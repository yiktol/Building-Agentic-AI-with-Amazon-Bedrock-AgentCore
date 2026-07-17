#!/usr/bin/env bash
#
# Delete the Module 02 prerequisites CloudFormation stack.
#
# Removes:
#   - S3 bucket (must be empty — lifecycle rule auto-expires objects after 7 days)
#   - IAM execution role
#
# Usage:
#   chmod +x cleanup-stack.sh
#   ./cleanup-stack.sh
#   ./cleanup-stack.sh us-west-2    # specify region

set -euo pipefail

STACK_NAME="mlagac-m02-demo-prereqs"
REGION="${1:-$(aws configure get region 2>/dev/null || echo 'ap-southeast-1')}"

echo "═══════════════════════════════════════════════════════════"
echo "  Deleting: ${STACK_NAME}"
echo "  Region:   ${REGION}"
echo "═══════════════════════════════════════════════════════════"
echo ""

# Empty the S3 bucket first (CloudFormation can't delete non-empty buckets)
BUCKET_NAME=$(aws cloudformation describe-stacks \
  --stack-name "${STACK_NAME}" \
  --region "${REGION}" \
  --query "Stacks[0].Outputs[?OutputKey=='BucketName'].OutputValue" \
  --output text 2>/dev/null || echo "")

if [ -n "${BUCKET_NAME}" ] && [ "${BUCKET_NAME}" != "None" ]; then
  echo "  Emptying S3 bucket: ${BUCKET_NAME}..."
  aws s3 rm "s3://${BUCKET_NAME}" --recursive --region "${REGION}" 2>/dev/null || true
  echo "  ✓ Bucket emptied"
fi

echo "  Deleting CloudFormation stack..."
aws cloudformation delete-stack \
  --stack-name "${STACK_NAME}" \
  --region "${REGION}"

echo "  Waiting for stack deletion..."
aws cloudformation wait stack-delete-complete \
  --stack-name "${STACK_NAME}" \
  --region "${REGION}"

echo ""
echo "✓ Stack deleted successfully!"
