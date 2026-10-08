#!/usr/bin/env bash
#
# Deploy / update the agc-slides CloudFormation stack (root + nested stacks),
# then publish the generated Web_Viewer content to the S3 origin.
#
# Architecture: CloudFront (OAC) -> private S3 content bucket. There is no
# EC2/ALB and no activity/judge backend. The Web_Viewer is the pre-built static
# site under `slides/` (the reveal.js app: index.html, deck.html, decks/),
# published to the bucket root with `aws s3 sync` and served from "/" (a
# CloudFront Function redirects "/" to index.html and rewrites directory-style
# URIs to index.html). Publishes existing static content directly, no pipeline
# build step.
#
# The root stack references two nested templates by S3 URL, staged under
#   s3://<BucketName>/templates/agc-slides-demo/s3.yaml
#   s3://<BucketName>/templates/agc-slides-demo/cloudfront.yaml
# This script uploads the local templates to those keys, creates/updates the
# root stack, then syncs `slides/` to the content bucket and issues a
# CloudFront invalidation so viewers pick up the new content immediately.
#
# The <BucketName> (staging bucket for templates) is read from SSM
# (${PARAMETER_PREFIX}/BucketName), matching how the root template resolves it.
#
# All resource names derive from PROJECT_PREFIX (default agc) so this stack
# coexists with the aibs-slides (aibs) and aws-sec-slides (sbp) deployments in
# the same account/region without collisions.
#
# Usage:
#   ./agc-slides-deploy.sh kb              # deploy the KB sibling stack + ingest the corpus
#   ./agc-slides-deploy.sh                 # deploy/update, publish Lambdas + content
#   REGION=ap-southeast-1 ./agc-slides-deploy.sh
#   ./agc-slides-deploy.sh --dry-run       # upload templates + show change set, no execute
#   ./agc-slides-deploy.sh --content-only  # skip stack deploy; only sync + invalidate
#
# First-time bring-up order: `./agc-slides-deploy.sh kb` (creates the KB,
# ingests the corpus, sets the sentinel) then `./agc-slides-deploy.sh` (deploys
# the root with the KB wired, publishes both Lambdas + content). A second
# default run tightens the distribution ARN on both Lambda policies.
#
set -euo pipefail

# ------------------------------------------------------------------ config ---
REGION="${REGION:-ap-southeast-1}"
STACK_NAME="${STACK_NAME:-agc-slides}"
PROJECT_PREFIX="${PROJECT_PREFIX:-agc}"
PREFIX="${PREFIX:-templates/agc-slides-demo}"          # S3 key prefix for nested templates
PARAMETER_PREFIX="${PARAMETER_PREFIX:-/genai/cognito}" # SSM prefix for shared config

# Local template files -> remote S3 key names expected by the root template
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
REPO_ROOT="$(cd "$SCRIPT_DIR/.." && pwd)"
ROOT_TEMPLATE="$SCRIPT_DIR/agc-slides-root.yaml"
S3_TEMPLATE="$SCRIPT_DIR/agc-slides-s3.yaml"
CLOUDFRONT_TEMPLATE="$SCRIPT_DIR/agc-slides-cloudfront.yaml"
JUDGE_TEMPLATE="$SCRIPT_DIR/agc-slides-judge.yaml"
JUDGE_SRC_DIR="$SCRIPT_DIR/judge"                      # Lambda source (handler.py)
# Origin secret shared between CloudFront and BOTH the judge and assistant
# Lambdas. Persisted in SSM so repeat deploys reuse the same value (changing it
# would break both backends until the Lambda env and the CloudFront origin
# header are updated together).
ORIGIN_SECRET_SSM="${ORIGIN_SECRET_SSM:-${PARAMETER_PREFIX}/agc/JudgeOriginSecret}"

# Course assistant backend (Lambda + IAM-auth Function URL), nested parallel to
# the judge, and the Bedrock Knowledge Base it grounds on (a SIBLING stack, not
# nested in the root).
ASSISTANT_SRC_DIR="$SCRIPT_DIR/assistant"              # assistant Lambda source
ASSISTANT_MODEL_ID="${ASSISTANT_MODEL_ID:-global.anthropic.claude-haiku-4-5-20251001-v1:0}"
ASSISTANT_TEMPLATE="$SCRIPT_DIR/agc-slides-assistant.yaml"
KB_STACK_NAME="${KB_STACK_NAME:-agc-slides-kb}"
KB_TEMPLATE="$SCRIPT_DIR/kb/kb.yaml"
KB_CORPUS_BUILDER="$SCRIPT_DIR/kb/build_corpus.sh"
KB_STAGING_DIR="$SCRIPT_DIR/kb/.staging"
KB_INGEST_SSM="${KB_INGEST_SSM:-/agc/kb-ingestion-status}"
EMBEDDING_MODEL_ID="${EMBEDDING_MODEL_ID:-cohere.embed-english-v3}"

# The pre-built static Web_Viewer content (the slides/ reveal.js app).
WEB_DIR="$REPO_ROOT/slides"

DRY_RUN=false
CONTENT_ONLY=false
KB_ONLY=false
# Optional first-arg sub-command: `kb` deploys the Knowledge Base sibling stack
# (creates the KB, builds+syncs the corpus, runs ingestion to COMPLETE, and
# writes the ingestion sentinel), then exits. The default (no-arg) flow deploys
# the root + nested stacks and re-derives the KB wiring from the sibling stack.
case "${1:-}" in
  kb) KB_ONLY=true ;;
  --dry-run) DRY_RUN=true ;;
  --content-only) CONTENT_ONLY=true ;;
  "") ;;
  *) echo "Unknown option: ${1}" >&2; exit 1 ;;
esac

log() { printf '\033[1;34m==>\033[0m %s\n' "$*"; }
err() { printf '\033[1;31mERROR:\033[0m %s\n' "$*" >&2; }

# ------------------------------------------------------- KB sibling stack ---
# Deploy the Knowledge Base sibling stack (agc-slides-kb), build + sync the
# corpus, run ingestion to COMPLETE, and record the ingestion sentinel in SSM.
# This script runs under `set -euo pipefail` with no ERR trap, so where the
# reference relied on a trap we use `|| rc=$?` captures to keep set -e from
# aborting on an expected non-zero (e.g. an empty changeset).
deploy_kb() {
  log "=========================================="
  log "Deploy Knowledge Base Stack (sibling): $KB_STACK_NAME (region $REGION)"
  log "=========================================="

  [[ -f "$KB_TEMPLATE" ]] || { err "KB template not found: $KB_TEMPLATE"; exit 1; }
  [[ -f "$KB_CORPUS_BUILDER" ]] || { err "corpus builder not found: $KB_CORPUS_BUILDER"; exit 1; }

  # 1. Deploy the childless KB stack. `aws cloudformation deploy` returns
  #    non-zero on an empty changeset even when the stack is COMPLETE; the
  #    `|| deploy_rc=$?` capture + --no-fail-on-empty-changeset make the no-op
  #    rc=0 and keep set -e from aborting.
  local deploy_rc=0
  aws cloudformation deploy \
    --template-file "$KB_TEMPLATE" \
    --stack-name "$KB_STACK_NAME" \
    --parameter-overrides ProjectPrefix="$PROJECT_PREFIX" \
                          EmbeddingModelId="$EMBEDDING_MODEL_ID" \
    --capabilities CAPABILITY_NAMED_IAM \
    --region "$REGION" \
    --no-fail-on-empty-changeset || deploy_rc=$?
  if [[ "$deploy_rc" -ne 0 ]]; then
    err "KB stack deploy failed (rc=$deploy_rc)"; exit 1
  fi
  log "KB stack deployed"

  # 2. Read KB stack outputs.
  local kb_outputs DS_BUCKET KB_ID DS_ID
  kb_outputs="$(aws cloudformation describe-stacks \
    --stack-name "$KB_STACK_NAME" --region "$REGION" \
    --query 'Stacks[0].Outputs' --output json 2>/dev/null || echo "[]")"
  DS_BUCKET="$(echo "$kb_outputs" | jq -r '[.[]?|select(.OutputKey=="DataSourceBucketName").OutputValue][0] // ""')"
  KB_ID="$(echo "$kb_outputs"     | jq -r '[.[]?|select(.OutputKey=="KnowledgeBaseId").OutputValue][0] // ""')"
  DS_ID="$(echo "$kb_outputs"     | jq -r '[.[]?|select(.OutputKey=="DataSourceId").OutputValue][0] // ""')"
  if [[ -z "$DS_BUCKET" || -z "$KB_ID" || -z "$DS_ID" ]]; then
    err "KB stack outputs incomplete (bucket='$DS_BUCKET' kb='$KB_ID' ds='$DS_ID')"; exit 1
  fi
  log "KB: id=$KB_ID ds=$DS_ID bucket=$DS_BUCKET"

  # 3. Build + sync the corpus.
  log "Building corpus staging dir"
  bash "$KB_CORPUS_BUILDER" "$KB_STAGING_DIR"
  log "Syncing corpus -> s3://$DS_BUCKET/"
  aws s3 sync "$KB_STAGING_DIR" "s3://$DS_BUCKET/" --region "$REGION" --delete

  # 4. Start ingestion. Immediately after CREATE_COMPLETE the KB may not yet be
  #    queryable, so start-ingestion-job can return a transient non-zero; retry
  #    up to 5 attempts, 15s apart, before treating it as a real failure.
  local JOB_ID="" start_attempt
  for start_attempt in 1 2 3 4 5; do
    JOB_ID="$(aws bedrock-agent start-ingestion-job \
      --knowledge-base-id "$KB_ID" --data-source-id "$DS_ID" \
      --region "$REGION" --query 'ingestionJob.ingestionJobId' \
      --output text 2>/dev/null || echo "")"
    if [[ -n "$JOB_ID" && "$JOB_ID" != "None" ]]; then
      break
    fi
    if [[ "$start_attempt" -lt 5 ]]; then
      log "start-ingestion-job not ready (attempt $start_attempt/5); retrying in 15s"
      sleep 15
    fi
  done
  if [[ -z "$JOB_ID" || "$JOB_ID" == "None" ]]; then
    err "Failed to start ingestion job"; exit 1
  fi
  log "Ingestion job started: $JOB_ID"

  # 5. Poll to COMPLETE — set-e-safe. Only a terminal FAILED/STOPPED, 5
  #    consecutive unreadable polls, or a ~1200s timeout is fatal; a lone
  #    transient CLI non-zero is absorbed and retried.
  local job_status unknown_count=0 start_time
  start_time="$(date +%s)"
  while true; do
    job_status="$(aws bedrock-agent get-ingestion-job \
      --knowledge-base-id "$KB_ID" --data-source-id "$DS_ID" \
      --ingestion-job-id "$JOB_ID" --region "$REGION" \
      --query 'ingestionJob.status' --output text 2>/dev/null || echo "UNKNOWN")"
    case "$job_status" in
      COMPLETE)
        log "Ingestion COMPLETE"
        # Sentinel: record that THIS KB has a COMPLETE ingestion, so the main
        # deploy wires the assistant only after ingestion.
        aws ssm put-parameter --name "$KB_INGEST_SSM" \
          --type String --overwrite --region "$REGION" \
          --value "COMPLETE:${KB_ID}" >/dev/null
        break ;;
      FAILED|STOPPED)
        err "Ingestion $job_status"
        # Invalidate the sentinel so a later main deploy will NOT wire a KB
        # whose latest ingestion failed.
        aws ssm put-parameter --name "$KB_INGEST_SSM" \
          --type String --overwrite --region "$REGION" \
          --value "${job_status}:${KB_ID}" >/dev/null 2>&1 || true
        # Surface failureReasons[] for diagnosability (dimension mismatch, etc.)
        aws bedrock-agent get-ingestion-job \
          --knowledge-base-id "$KB_ID" --data-source-id "$DS_ID" \
          --ingestion-job-id "$JOB_ID" --region "$REGION" \
          --query 'ingestionJob.failureReasons' --output json 2>/dev/null || true
        exit 1 ;;
      STARTING|IN_PROGRESS)
        unknown_count=0 ;;
      UNKNOWN|*)
        unknown_count=$((unknown_count + 1))
        if [[ "$unknown_count" -ge 5 ]]; then
          err "Ingestion status unreadable after 5 attempts"; exit 1
        fi ;;
    esac
    if [[ $(($(date +%s) - start_time)) -gt 1200 ]]; then
      err "Ingestion timed out after 1200s"; exit 1
    fi
    sleep 15
  done

  log "Knowledge Base stack deployed and ingested"
}

# ----------------------------------------------- publish assistant Lambda ---
# Zip deploy/assistant/handler.py at the archive root and update the assistant
# Lambda's code. Parallel to the judge publish: the template ships only an
# inline 503 stub, so this publishes the real handler. Guarded on a resolvable
# function name so a not-yet-created assistant output skips non-fatally (so
# set -e does not abort). A resolvable-name-but-failed update-function-code is
# the only fatal publish path.
publish_assistant_code() {
  local ASSISTANT_FN
  ASSISTANT_FN="$(aws cloudformation describe-stacks --stack-name "$STACK_NAME" --region "$REGION" \
    --query "Stacks[0].Outputs[?OutputKey=='AssistantFunctionName'].OutputValue" \
    --output text 2>/dev/null || true)"
  if [[ -n "$ASSISTANT_FN" && "$ASSISTANT_FN" != "None" ]]; then
    if [[ ! -f "$ASSISTANT_SRC_DIR/handler.py" ]]; then
      err "assistant source not found: $ASSISTANT_SRC_DIR/handler.py; skipping assistant code publish"
      return 0
    fi
    log "Publishing assistant Lambda code to ${ASSISTANT_FN}"
    local TMP_ZIP
    TMP_ZIP="$(mktemp -t agc-assistant-XXXX).zip"
    ( cd "$ASSISTANT_SRC_DIR" && zip -q -r "$TMP_ZIP" handler.py )
    # A genuinely-failed update-function-code is NOT suffixed with `|| true`, so
    # it remains the only fatal path.
    aws lambda update-function-code \
      --function-name "$ASSISTANT_FN" \
      --zip-file "fileb://${TMP_ZIP}" \
      --region "$REGION" --publish >/dev/null
    aws lambda wait function-updated --function-name "$ASSISTANT_FN" --region "$REGION" || true
    rm -f "$TMP_ZIP"
    log "Assistant Lambda code published."
  else
    err "AssistantFunctionName output not found yet; skipping assistant code publish (non-fatal)"
    return 0
  fi
}

# --------------------------------------------------------------- preflight ---
command -v aws >/dev/null || { err "aws CLI not found"; exit 1; }

# KB sub-command: deploy the Knowledge Base sibling stack, then exit. This is
# the first-time bring-up step (`./agc-slides-deploy.sh kb`); the default flow
# below then deploys the root with the KB wired in.
if $KB_ONLY; then
  command -v jq >/dev/null || { err "jq not found (required for the kb sub-command)"; exit 1; }
  deploy_kb
  exit 0
fi

if ! $CONTENT_ONLY; then
  for f in "$ROOT_TEMPLATE" "$S3_TEMPLATE" "$CLOUDFRONT_TEMPLATE" "$JUDGE_TEMPLATE" "$ASSISTANT_TEMPLATE"; do
    [[ -f "$f" ]] || { err "template not found: $f"; exit 1; }
  done
  [[ -f "$JUDGE_SRC_DIR/handler.py" ]] || { err "judge handler not found: $JUDGE_SRC_DIR/handler.py"; exit 1; }
  [[ -f "$ASSISTANT_SRC_DIR/handler.py" ]] || { err "assistant handler not found: $ASSISTANT_SRC_DIR/handler.py"; exit 1; }
fi
[[ -d "$WEB_DIR" ]] || { err "web content folder not found: $WEB_DIR"; exit 1; }
[[ -f "$WEB_DIR/index.html" ]] || { err "no index.html in $WEB_DIR (expected the slides/ reveal.js app)"; exit 1; }

# --------------------------------------------------- resolve staging bucket ---
log "Resolving staging bucket from SSM ${PARAMETER_PREFIX}/BucketName"
BUCKET_NAME="$(aws ssm get-parameter \
  --name "${PARAMETER_PREFIX}/BucketName" \
  --region "$REGION" \
  --query 'Parameter.Value' --output text)"
[[ -n "$BUCKET_NAME" && "$BUCKET_NAME" != "None" ]] || { err "could not resolve bucket name from SSM"; exit 1; }
log "Staging bucket: s3://${BUCKET_NAME}/${PREFIX}/"

# --------------------------------------------- resolve/create origin secret ---
# Shared x-origin-secret value between CloudFront and the judge Lambda. Create a
# random one on first deploy and store it as a SecureString in SSM; reuse it on
# subsequent deploys so the two sides stay in sync.
if ! $CONTENT_ONLY; then
  ORIGIN_SECRET="$(aws ssm get-parameter --name "$ORIGIN_SECRET_SSM" --with-decryption \
    --region "$REGION" --query 'Parameter.Value' --output text 2>/dev/null || true)"
  if [[ -z "$ORIGIN_SECRET" || "$ORIGIN_SECRET" == "None" ]]; then
    ORIGIN_SECRET="$(python3 -c 'import secrets; print(secrets.token_urlsafe(32))')"
    aws ssm put-parameter --name "$ORIGIN_SECRET_SSM" --type SecureString \
      --value "$ORIGIN_SECRET" --region "$REGION" --overwrite >/dev/null
    log "Generated and stored a new judge origin secret in SSM ${ORIGIN_SECRET_SSM}"
  else
    log "Reusing judge origin secret from SSM ${ORIGIN_SECRET_SSM}"
  fi
fi

# ------------------------------------------------------------ deploy stack ---
if ! $CONTENT_ONLY; then
  log "Validating templates with cfn-lint (if available)"
  if command -v cfn-lint >/dev/null; then
    cfn-lint "$ROOT_TEMPLATE" "$S3_TEMPLATE" "$CLOUDFRONT_TEMPLATE" "$JUDGE_TEMPLATE" "$ASSISTANT_TEMPLATE" || {
      # cfn-lint exit 4 = warnings only; treat as non-fatal
      [[ $? -eq 4 ]] || { err "cfn-lint reported errors"; exit 1; }
    }
  else
    log "cfn-lint not installed, skipping lint"
  fi

  # The root template references these by their remote names: s3.yaml,
  # cloudfront.yaml, judge.yaml, assistant.yaml
  log "Uploading nested templates to S3"
  aws s3 cp "$S3_TEMPLATE"         "s3://${BUCKET_NAME}/${PREFIX}/s3.yaml"         --region "$REGION"
  aws s3 cp "$CLOUDFRONT_TEMPLATE" "s3://${BUCKET_NAME}/${PREFIX}/cloudfront.yaml" --region "$REGION"
  aws s3 cp "$JUDGE_TEMPLATE"      "s3://${BUCKET_NAME}/${PREFIX}/judge.yaml"      --region "$REGION"
  aws s3 cp "$ASSISTANT_TEMPLATE"  "s3://${BUCKET_NAME}/${PREFIX}/assistant.yaml"  --region "$REGION"

  # If the stack already exists, read its distribution id so we can scope the
  # judge Lambda's resource policy to that exact distribution ARN. On the very
  # first create this is empty and the judge falls back to a SourceAccount
  # condition; the next deploy tightens it to the distribution ARN.
  EXISTING_DIST_ID="$(aws cloudformation describe-stacks \
    --stack-name "$STACK_NAME" --region "$REGION" \
    --query "Stacks[0].Outputs[?OutputKey=='CloudFrontDistributionId'].OutputValue" \
    --output text 2>/dev/null || true)"
  JUDGE_DIST_ARN=""
  if [[ -n "$EXISTING_DIST_ID" && "$EXISTING_DIST_ID" != "None" ]]; then
    JUDGE_DIST_ARN="arn:aws:cloudfront::$(aws sts get-caller-identity --query Account --output text):distribution/${EXISTING_DIST_ID}"
    log "Scoping judge + assistant Lambda permissions to distribution ${EXISTING_DIST_ID}"
  fi

  # --- Re-derive the KB wiring from the sibling KB stack + ingestion sentinel.
  # These are ALWAYS resolved on a default deploy (even when the KB stack is
  # absent — then both stay empty and the assistant renders 503, the correct
  # "not configured" state). CloudFormation resets any param not passed back to
  # its default, so a routine deploy MUST re-derive + re-pass the KB params or
  # it would silently un-wire a live KB. The assistant is wired ONLY when BOTH
  # outputs are present AND the sentinel reads COMPLETE:<this KB id>.
  KB_ID_PARAM=""
  KB_ARN_PARAM=""
  if command -v jq >/dev/null; then
    KB_OUTPUTS="$(aws cloudformation describe-stacks --stack-name "$KB_STACK_NAME" \
      --region "$REGION" --query 'Stacks[0].Outputs' --output json 2>/dev/null || echo "[]")"
    KB_ID_MAIN="$(echo "$KB_OUTPUTS"  | jq -r '[.[]?|select(.OutputKey=="KnowledgeBaseId").OutputValue][0] // ""')"
    KB_ARN_MAIN="$(echo "$KB_OUTPUTS" | jq -r '[.[]?|select(.OutputKey=="KnowledgeBaseArn").OutputValue][0] // ""')"
    KB_INGEST="$(aws ssm get-parameter --name "$KB_INGEST_SSM" --region "$REGION" \
      --query 'Parameter.Value' --output text 2>/dev/null || echo "")"
    if [[ -n "$KB_ID_MAIN" && -n "$KB_ARN_MAIN" ]]; then
      if [[ "$KB_INGEST" == "COMPLETE:${KB_ID_MAIN}" ]]; then
        KB_ID_PARAM="$KB_ID_MAIN"
        KB_ARN_PARAM="$KB_ARN_MAIN"
        log "Wiring assistant to KB ${KB_ID_MAIN} (ingestion COMPLETE)"
      else
        log "KB present but ingestion not COMPLETE (status='$KB_INGEST'); assistant will render 503 until ingestion completes. Run './agc-slides-deploy.sh kb' then redeploy."
      fi
    elif [[ ( -n "$KB_ID_MAIN" && -z "$KB_ARN_MAIN" ) || ( -z "$KB_ID_MAIN" && -n "$KB_ARN_MAIN" ) ]]; then
      err "KB stack is partial (id='$KB_ID_MAIN' arn='$KB_ARN_MAIN'); refusing to half-wire."; exit 1
    fi
  else
    log "jq not found; skipping KB re-derivation (assistant will render 503 until a KB id is wired)"
  fi

  PARAM_OVERRIDES=(
    "Prefix=${PREFIX}"
    "BucketRegion=${REGION}"
    "ParameterPrefix=${PARAMETER_PREFIX}"
    "ProjectPrefix=${PROJECT_PREFIX}"
    "OriginSecret=${ORIGIN_SECRET}"
    "JudgeDistributionArn=${JUDGE_DIST_ARN}"
    "AssistantModelId=${ASSISTANT_MODEL_ID}"
    "ReservedConcurrency=3"
    "KnowledgeBaseId=${KB_ID_PARAM}"
    "KnowledgeBaseArn=${KB_ARN_PARAM}"
    "EmbeddingModelId=${EMBEDDING_MODEL_ID}"
  )

  if $DRY_RUN; then
    log "Dry run: creating change set only (no execution)"
    aws cloudformation deploy \
      --stack-name "$STACK_NAME" \
      --template-file "$ROOT_TEMPLATE" \
      --region "$REGION" \
      --capabilities CAPABILITY_IAM CAPABILITY_NAMED_IAM CAPABILITY_AUTO_EXPAND \
      --parameter-overrides "${PARAM_OVERRIDES[@]}" \
      --no-execute-changeset
    log "Change set created. Review it in the CloudFormation console, then run without --dry-run to apply."
    exit 0
  fi

  log "Deploying root stack: $STACK_NAME (region $REGION)"
  aws cloudformation deploy \
    --stack-name "$STACK_NAME" \
    --template-file "$ROOT_TEMPLATE" \
    --region "$REGION" \
    --capabilities CAPABILITY_IAM CAPABILITY_NAMED_IAM CAPABILITY_AUTO_EXPAND \
    --parameter-overrides "${PARAM_OVERRIDES[@]}"
fi

# --------------------------------------------- read stack outputs for publish ---
get_output() {
  aws cloudformation describe-stacks \
    --stack-name "$STACK_NAME" --region "$REGION" \
    --query "Stacks[0].Outputs[?OutputKey=='$1'].OutputValue" --output text
}

CONTENT_BUCKET="$(get_output ContentBucketName)"
DIST_ID="$(get_output CloudFrontDistributionId)"
[[ -n "$CONTENT_BUCKET" && "$CONTENT_BUCKET" != "None" ]] || { err "could not read ContentBucketName output"; exit 1; }
[[ -n "$DIST_ID" && "$DIST_ID" != "None" ]] || { err "could not read CloudFrontDistributionId output"; exit 1; }

# ------------------------------------------------- publish judge Lambda code ---
# The template ships only a stub so it is valid on first create; publish the
# real handler here. Skipped in --content-only mode (static site only).
if ! $CONTENT_ONLY; then
  JUDGE_FN="$(get_output JudgeFunctionName)"
  if [[ -n "$JUDGE_FN" && "$JUDGE_FN" != "None" ]]; then
    log "Publishing judge Lambda code to ${JUDGE_FN}"
    TMP_ZIP="$(mktemp -t agc-judge-XXXX).zip"
    ( cd "$JUDGE_SRC_DIR" && zip -q -r "$TMP_ZIP" handler.py )
    aws lambda update-function-code \
      --function-name "$JUDGE_FN" \
      --zip-file "fileb://${TMP_ZIP}" \
      --region "$REGION" --publish >/dev/null
    aws lambda wait function-updated --function-name "$JUDGE_FN" --region "$REGION" || true
    rm -f "$TMP_ZIP"
    log "Judge Lambda code published."
  else
    err "could not read JudgeFunctionName output; judge code not published"
  fi

  # Publish the assistant Lambda code (parallel to the judge publish above).
  publish_assistant_code
fi

# --------------------------------------------- validate quizzes before publish ---
# Gate: the knowledge-check quizzes are a mN.json/mN.js pair that must stay in
# sync, and each question has mechanical invariants (4 options, answer ==
# options[answerIndex], answerLetter consistent, sequential ids). A hand-edit
# can silently break these, and the sync below would ship the breakage. Fail
# the publish if slides/build_quiz.py reports any problem. Runs on every publish
# path (including --content-only), since that is exactly when quiz files ship.
QUIZ_VALIDATOR="$WEB_DIR/build_quiz.py"
if [[ -f "$QUIZ_VALIDATOR" ]]; then
  log "Validating knowledge-check quizzes (slides/build_quiz.py)"
  python3 "$QUIZ_VALIDATOR" || { err "quiz validation failed; not publishing"; exit 1; }
else
  log "Quiz validator not found ($QUIZ_VALIDATOR); skipping quiz validation"
fi

# ------------------------------------------------------ publish web content ---
# Sync the Web_Viewer to the content bucket root. --delete keeps the bucket in
# sync with the slides/ tree (removes files that were removed locally). The
# CloudFront invalidation below forces edges to refresh regardless.
#
# Excludes drop local tooling that should never be served: build scripts,
# Python helpers, and OS cruft.
log "Syncing slides/ -> s3://${CONTENT_BUCKET}/"
aws s3 sync "$WEB_DIR/" "s3://${CONTENT_BUCKET}/" \
  --region "$REGION" \
  --delete \
  --exclude ".DS_Store" \
  --exclude "*/.DS_Store" \
  --exclude "*.py" \
  --exclude "*/__pycache__/*" \
  --exclude "*.pyc" \
  --exclude "*.sh"

# ---------------------------------------------------- invalidate CloudFront ---
log "Creating CloudFront invalidation (/*) on distribution ${DIST_ID}"
INVALIDATION_ID="$(aws cloudfront create-invalidation \
  --distribution-id "$DIST_ID" \
  --paths '/*' \
  --query 'Invalidation.Id' --output text)"
log "Invalidation ${INVALIDATION_ID} submitted."

# ----------------------------------------------------------------- outputs ---
log "Stack outputs"
aws cloudformation describe-stacks \
  --stack-name "$STACK_NAME" \
  --region "$REGION" \
  --query 'Stacks[0].Outputs[].{Key:OutputKey,Value:OutputValue}' \
  --output table

log "Done. The Web_Viewer is served at:"
cat <<NOTE
  https://${PROJECT_PREFIX}.<domain>/            (slides landing page)
  https://${PROJECT_PREFIX}.<domain>/deck.html?m=1   (a module deck)

To republish content later without touching the stack:
  ./agc-slides-deploy.sh --content-only

To (re)build the Knowledge Base and ingest the corpus:
  ./agc-slides-deploy.sh kb
NOTE
