#!/usr/bin/env bash
set -euo pipefail

STACK_NAME="mlagac-m04-tools-gateway-prereqs"
REGION="${1:-$(aws configure get region 2>/dev/null || echo 'ap-southeast-1')}"

echo "═══════════════════════════════════════════════════════════"
echo "  Deleting: ${STACK_NAME}"
echo "  Region:   ${REGION}"
echo "═══════════════════════════════════════════════════════════"

BUCKET=$(aws cloudformation describe-stacks --stack-name "${STACK_NAME}" --region "${REGION}" \
  --query "Stacks[0].Outputs[?OutputKey=='BucketName'].OutputValue" --output text 2>/dev/null || echo "")

if [ -n "${BUCKET}" ] && [ "${BUCKET}" != "None" ]; then
  echo "  Emptying bucket: ${BUCKET}..."
  aws s3 rm "s3://${BUCKET}" --recursive --region "${REGION}" 2>/dev/null || true
fi

aws cloudformation delete-stack --stack-name "${STACK_NAME}" --region "${REGION}"
echo "  Waiting..."
aws cloudformation wait stack-delete-complete --stack-name "${STACK_NAME}" --region "${REGION}"
echo ""
echo "✓ Stack deleted!"
