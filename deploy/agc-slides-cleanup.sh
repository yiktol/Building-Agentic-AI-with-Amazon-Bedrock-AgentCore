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
  log "Removing all objects, versions, and delete markers: s3://${bucket}"
  # Use boto3's list_object_versions paginator to clear a versioned bucket
  # completely in batches of 1000. This is more robust than driving the AWS CLI
  # paginator from shell with JMESPath, which previously bailed out partway and
  # left versions/delete-markers behind — causing CloudFormation to fail the
  # bucket (and thus the whole stack) deletion.
  python3 - "$bucket" "$REGION" <<'PY' || warn "bucket empty step reported an error"
import sys
import boto3
from botocore.exceptions import ClientError

bucket, region = sys.argv[1], sys.argv[2]
s3 = boto3.client("s3", region_name=region)
paginator = s3.get_paginator("list_object_versions")
total = 0
try:
    for page in paginator.paginate(Bucket=bucket):
        objs = [{"Key": v["Key"], "VersionId": v["VersionId"]} for v in page.get("Versions", [])]
        objs += [{"Key": m["Key"], "VersionId": m["VersionId"]} for m in page.get("DeleteMarkers", [])]
        for i in range(0, len(objs), 1000):
            chunk = objs[i:i + 1000]
            s3.delete_objects(Bucket=bucket, Delete={"Objects": chunk, "Quiet": True})
            total += len(chunk)
except ClientError as e:
    if e.response.get("Error", {}).get("Code") == "NoSuchBucket":
        print(f"  bucket {bucket} already gone")
        sys.exit(0)
    raise
print(f"  removed {total} objects/versions/markers")
PY
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
  aws s3 rm "s3://${BUCKET_NAME}/${PREFIX}/assistant.yaml"  --region "$REGION" 2>/dev/null || true
else
  warn "Could not resolve staging bucket from SSM; skipping template cleanup."
fi

log "Cleanup complete."
