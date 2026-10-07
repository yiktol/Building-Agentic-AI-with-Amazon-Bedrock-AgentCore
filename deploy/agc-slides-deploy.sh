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
#   ./agc-slides-deploy.sh                 # deploy/update, then publish content
#   REGION=ap-southeast-1 ./agc-slides-deploy.sh
#   ./agc-slides-deploy.sh --dry-run       # upload templates + show change set, no execute
#   ./agc-slides-deploy.sh --content-only  # skip stack deploy; only sync + invalidate
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
# Origin secret shared between CloudFront and the judge Lambda. Persisted in SSM
# so repeat deploys reuse the same value (changing it would break grading until
# both the Lambda env and the CloudFront origin header are updated together).
ORIGIN_SECRET_SSM="${ORIGIN_SECRET_SSM:-${PARAMETER_PREFIX}/agc/JudgeOriginSecret}"

# The pre-built static Web_Viewer content (the slides/ reveal.js app).
WEB_DIR="$REPO_ROOT/slides"

DRY_RUN=false
CONTENT_ONLY=false
case "${1:-}" in
  --dry-run) DRY_RUN=true ;;
  --content-only) CONTENT_ONLY=true ;;
  "") ;;
  *) echo "Unknown option: ${1}" >&2; exit 1 ;;
esac

log() { printf '\033[1;34m==>\033[0m %s\n' "$*"; }
err() { printf '\033[1;31mERROR:\033[0m %s\n' "$*" >&2; }

# --------------------------------------------------------------- preflight ---
command -v aws >/dev/null || { err "aws CLI not found"; exit 1; }

if ! $CONTENT_ONLY; then
  for f in "$ROOT_TEMPLATE" "$S3_TEMPLATE" "$CLOUDFRONT_TEMPLATE" "$JUDGE_TEMPLATE"; do
    [[ -f "$f" ]] || { err "template not found: $f"; exit 1; }
  done
  [[ -f "$JUDGE_SRC_DIR/handler.py" ]] || { err "judge handler not found: $JUDGE_SRC_DIR/handler.py"; exit 1; }
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
    cfn-lint "$ROOT_TEMPLATE" "$S3_TEMPLATE" "$CLOUDFRONT_TEMPLATE" || {
      # cfn-lint exit 4 = warnings only; treat as non-fatal
      [[ $? -eq 4 ]] || { err "cfn-lint reported errors"; exit 1; }
    }
  else
    log "cfn-lint not installed, skipping lint"
  fi

  # The root template references these by their remote names: s3.yaml, cloudfront.yaml, judge.yaml
  log "Uploading nested templates to S3"
  aws s3 cp "$S3_TEMPLATE"         "s3://${BUCKET_NAME}/${PREFIX}/s3.yaml"         --region "$REGION"
  aws s3 cp "$CLOUDFRONT_TEMPLATE" "s3://${BUCKET_NAME}/${PREFIX}/cloudfront.yaml" --region "$REGION"
  aws s3 cp "$JUDGE_TEMPLATE"      "s3://${BUCKET_NAME}/${PREFIX}/judge.yaml"      --region "$REGION"

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
    log "Scoping judge Lambda permission to distribution ${EXISTING_DIST_ID}"
  fi

  PARAM_OVERRIDES=(
    "Prefix=${PREFIX}"
    "BucketRegion=${REGION}"
    "ParameterPrefix=${PARAMETER_PREFIX}"
    "ProjectPrefix=${PROJECT_PREFIX}"
    "OriginSecret=${ORIGIN_SECRET}"
    "JudgeDistributionArn=${JUDGE_DIST_ARN}"
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
NOTE
