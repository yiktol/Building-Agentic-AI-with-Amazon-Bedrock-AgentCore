#!/usr/bin/env bash
#
# Tear down the agc-slides deployment: delete the root CloudFormation stack
# (which removes the nested S3 and CloudFront stacks), then clean up the staged
# nested templates in S3.
#
# CloudFormation cannot delete a non-empty S3 bucket, so both buckets are
# emptied FIRST:
#   - Content bucket: versioning is enabled, so ALL object versions and delete
#     markers must be removed, not just current objects.
#   - CloudFront log bucket: emptied of access logs.
#
# Ordering:
#   1. Read stack outputs (ContentBucketName, CloudFrontLogBucketName) BEFORE
#      deleting.
#   2. Empty BOTH versioned buckets including all versions and delete markers.
#   3. delete-stack, then wait stack-delete-complete.
#   4. Remove the staged nested templates from the staging bucket.
#
# All resource names derive from PROJECT_PREFIX (default agc) so this script
# targets only the agc-slides deployment and never the aibs-slides (aibs) or
# aws-sec-slides (sbp) ones.
#
# Usage:
#   ./agc-slides-cleanup.sh                   # prompts for confirmation, then deletes
#   ./agc-slides-cleanup.sh --yes             # skip the confirmation prompt
#   ./agc-slides-cleanup.sh --keep-templates  # delete stack but leave S3 templates in place
#
set -euo pipefail

# ------------------------------------------------------------------ config ---
REGION="${REGION:-ap-southeast-1}"
STACK_NAME="${STACK_NAME:-agc-slides}"
PREFIX="${PREFIX:-templates/agc-slides-demo}"           # S3 key prefix for nested templates
PARAMETER_PREFIX="${PARAMETER_PREFIX:-/genai/cognito}"  # SSM prefix for shared config
PROJECT_PREFIX="${PROJECT_PREFIX:-agc}"

ASSUME_YES=false
KEEP_TEMPLATES=false
for arg in "$@"; do
  case "$arg" in
    --yes) ASSUME_YES=true ;;
    --keep-templates) KEEP_TEMPLATES=true ;;
    *) echo "Unknown option: $arg" >&2; exit 1 ;;
  esac
done

log()  { printf '\033[1;34m==>\033[0m %s\n' "$*"; }
warn() { printf '\033[1;33mWARN:\033[0m %s\n' "$*"; }
err()  { printf '\033[1;31mERROR:\033[0m %s\n' "$*" >&2; }

command -v aws >/dev/null || { err "aws CLI not found"; exit 1; }

# Read a single stack output value (empty string if the stack/output is absent).
get_output() {
  aws cloudformation describe-stacks \
    --stack-name "$STACK_NAME" --region "$REGION" \
    --query "Stacks[0].Outputs[?OutputKey=='$1'].OutputValue" \
    --output text 2>/dev/null || echo ""
}

# Empty an S3 bucket including ALL versions and delete markers (needed for a
# versioned bucket, which a simple `s3 rm --recursive` will not fully clear).
empty_versioned_bucket() {
  local bucket="$1"
  if [[ -z "$bucket" || "$bucket" == "None" ]]; then
    log "No bucket name resolved; skipping empty step."
    return 0
  fi
  if ! aws s3api head-bucket --bucket "$bucket" --region "$REGION" >/dev/null 2>&1; then
    log "Bucket ${bucket} not present or not accessible; skipping empty step."
    return 0
  fi
  log "Emptying bucket (current objects): s3://${bucket}"
  aws s3 rm "s3://${bucket}" --recursive --region "$REGION" >/dev/null 2>&1 || warn "current-object delete had issues"

  log "Removing all object versions and delete markers: s3://${bucket}"
  # Page through list-object-versions (at most 1000 keys per page). Each page is
  # written to a temp file in the {"Objects":[...]} shape delete-objects expects,
  # then passed via file:// (avoids arg-quoting issues). Pagination is driven by
  # --starting-token / NextToken so both Versions[] and DeleteMarkers[] on every
  # page are cleared.
  local batch token
  batch="$(mktemp)"
  token=""
  while true; do
    if [[ -n "$token" ]]; then
      aws s3api list-object-versions \
        --bucket "$bucket" --region "$REGION" --max-items 1000 --starting-token "$token" \
        --query '{Objects: ((Versions || `[]`)[].{Key:Key,VersionId:VersionId}) + ((DeleteMarkers || `[]`)[].{Key:Key,VersionId:VersionId}), Quiet: `true`, NextToken: NextToken}' \
        --output json > "$batch" 2>/dev/null || { warn "list-object-versions failed"; break; }
    else
      aws s3api list-object-versions \
        --bucket "$bucket" --region "$REGION" --max-items 1000 \
        --query '{Objects: ((Versions || `[]`)[].{Key:Key,VersionId:VersionId}) + ((DeleteMarkers || `[]`)[].{Key:Key,VersionId:VersionId}), Quiet: `true`, NextToken: NextToken}' \
        --output json > "$batch" 2>/dev/null || { warn "list-object-versions failed"; break; }
    fi

    local count
    count="$(python3 -c 'import sys,json; print(len((json.load(open(sys.argv[1])).get("Objects") or [])))' "$batch" 2>/dev/null || echo 0)"

    if [[ "$count" -gt 0 ]]; then
      aws s3api delete-objects --bucket "$bucket" --region "$REGION" \
        --delete "file://${batch}" >/dev/null 2>&1 || { warn "delete-objects batch failed"; break; }
      log "  removed ${count} versions/markers"
    fi

    # Advance to the next page; stop when the CLI reports no NextToken.
    token="$(python3 -c 'import sys,json; v=json.load(open(sys.argv[1])).get("NextToken"); print(v or "")' "$batch" 2>/dev/null || echo "")"
    [[ -n "$token" ]] || break
  done
  rm -f "$batch"
}

# ------------------------------------------------------------- confirmation ---
ACCOUNT_ID="$(aws sts get-caller-identity --query Account --output text 2>/dev/null || echo unknown)"

cat <<EOF
About to DELETE the agc-slides deployment (account ${ACCOUNT_ID}, region ${REGION}):
  - CloudFormation stack: ${STACK_NAME} (and its nested S3 + CloudFront stacks)
  - Content bucket (emptied, incl. versions + delete markers)
  - CloudFront log bucket (emptied, incl. versions + delete markers)
  - Staged templates under: s3://<staging-bucket>/${PREFIX}/  (unless --keep-templates)

This is destructive and not reversible.
EOF

if ! $ASSUME_YES; then
  read -r -p "Type 'delete' to proceed: " CONFIRM
  [[ "$CONFIRM" == "delete" ]] || { log "Aborted."; exit 0; }
fi

# ---------------------------------------------------------- resolve context ---
if ! aws cloudformation describe-stacks --stack-name "$STACK_NAME" --region "$REGION" >/dev/null 2>&1; then
  warn "Stack ${STACK_NAME} not found in ${REGION}; will still attempt bucket/template cleanup."
  STACK_EXISTS=false
else
  STACK_EXISTS=true
fi

# ---- Read bucket names from stack outputs BEFORE deleting the stack ----
# Content bucket comes from the root stack's ContentBucketName output. The log
# bucket uses the CloudFrontLogBucketName output when present, otherwise it is
# derived from the Project_Prefix naming convention.
CONTENT_BUCKET="$(get_output ContentBucketName)"
if [[ -z "$CONTENT_BUCKET" || "$CONTENT_BUCKET" == "None" ]]; then
  CONTENT_BUCKET="${PROJECT_PREFIX}-content-${REGION}-${ACCOUNT_ID}"
  warn "ContentBucketName output unavailable; derived ${CONTENT_BUCKET}"
fi

LOG_BUCKET="$(get_output CloudFrontLogBucketName)"
if [[ -z "$LOG_BUCKET" || "$LOG_BUCKET" == "None" ]]; then
  LOG_BUCKET="${PROJECT_PREFIX}-logging-${REGION}-${ACCOUNT_ID}"
fi

log "Content bucket: ${CONTENT_BUCKET}"
log "Log bucket:     ${LOG_BUCKET}"

# Resolve the staging bucket (best-effort; used for template cleanup), matching
# how the deploy script resolves it from SSM.
BUCKET_NAME="$(aws ssm get-parameter \
  --name "${PARAMETER_PREFIX}/BucketName" \
  --region "$REGION" \
  --query 'Parameter.Value' --output text 2>/dev/null || echo "")"

# ------------------------------------------- pre-empty the content + log buckets ---
# CloudFormation cannot delete a non-empty S3 bucket, so this must run first.
empty_versioned_bucket "$CONTENT_BUCKET"
empty_versioned_bucket "$LOG_BUCKET"

# ------------------------------------------------------------- delete stack ---
if $STACK_EXISTS; then
  log "Deleting stack ${STACK_NAME} (this also deletes nested stacks)"
  aws cloudformation delete-stack --stack-name "$STACK_NAME" --region "$REGION"
  log "Waiting for stack deletion to complete..."
  if aws cloudformation wait stack-delete-complete --stack-name "$STACK_NAME" --region "$REGION"; then
    log "Stack deleted."
  else
    err "Stack deletion did not complete cleanly. Check the CloudFormation console for the failure reason."
    err "Common cause: a bucket still has objects/versions. Re-run this script to retry the empty step."
    exit 1
  fi
fi

# --------------------------------------------------------- remove S3 templates ---
if $KEEP_TEMPLATES; then
  log "--keep-templates set; leaving staged templates in S3."
elif [[ -n "$BUCKET_NAME" && "$BUCKET_NAME" != "None" ]]; then
  log "Removing staged templates: s3://${BUCKET_NAME}/${PREFIX}/"
  aws s3 rm "s3://${BUCKET_NAME}/${PREFIX}/s3.yaml"         --region "$REGION" 2>/dev/null || true
  aws s3 rm "s3://${BUCKET_NAME}/${PREFIX}/cloudfront.yaml" --region "$REGION" 2>/dev/null || true
  aws s3 rm "s3://${BUCKET_NAME}/${PREFIX}/judge.yaml"      --region "$REGION" 2>/dev/null || true
else
  warn "Could not resolve staging bucket from SSM; skipping template cleanup."
fi

log "Cleanup complete."
