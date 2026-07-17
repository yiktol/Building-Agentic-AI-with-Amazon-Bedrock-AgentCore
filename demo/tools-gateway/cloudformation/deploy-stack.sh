#!/usr/bin/env bash
set -euo pipefail

STACK_NAME="mlagac-m04-tools-gateway-prereqs"
TEMPLATE_FILE="$(dirname "$0")/prerequisites.yaml"
REGION="${1:-$(aws configure get region 2>/dev/null || echo 'us-east-1')}"

echo "═══════════════════════════════════════════════════════════"
echo "  Deploying: ${STACK_NAME}"
echo "  Region:    ${REGION}"
echo "═══════════════════════════════════════════════════════════"
echo ""

aws cloudformation deploy \
  --template-file "${TEMPLATE_FILE}" \
  --stack-name "${STACK_NAME}" \
  --region "${REGION}" \
  --capabilities CAPABILITY_NAMED_IAM \
  --tags Project=MLAGAC-Module04-Demo

echo ""
echo "✓ Stack deployed!"
echo ""
echo "  Outputs:"
aws cloudformation describe-stacks \
  --stack-name "${STACK_NAME}" \
  --region "${REGION}" \
  --query "Stacks[0].Outputs[*].[OutputKey,OutputValue]" \
  --output table

echo ""
echo "  Next: cd demo-01-mcp-server && python deploy.py"
