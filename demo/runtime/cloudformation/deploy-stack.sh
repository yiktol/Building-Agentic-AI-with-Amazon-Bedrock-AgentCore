#!/usr/bin/env bash
#
# Deploy the Module 02 prerequisites CloudFormation stack.
#
# Creates:
#   - S3 bucket for agent code artifacts
#   - IAM execution role for AgentCore Runtime
#
# Usage:
#   chmod +x deploy-stack.sh
#   ./deploy-stack.sh
#   ./deploy-stack.sh us-west-2    # specify region

set -euo pipefail

STACK_NAME="mlagac-m02-demo-prereqs"
TEMPLATE_FILE="$(dirname "$0")/prerequisites.yaml"
REGION="${1:-$(aws configure get region 2>/dev/null || echo 'ap-southeast-1')}"

echo "═══════════════════════════════════════════════════════════"
echo "  Deploying: ${STACK_NAME}"
echo "  Region:    ${REGION}"
echo "  Template:  ${TEMPLATE_FILE}"
echo "═══════════════════════════════════════════════════════════"
echo ""

aws cloudformation deploy \
  --template-file "${TEMPLATE_FILE}" \
  --stack-name "${STACK_NAME}" \
  --region "${REGION}" \
  --capabilities CAPABILITY_NAMED_IAM \
  --tags Project=MLAGAC-Module02-Demo

echo ""
echo "✓ Stack deployed successfully!"
echo ""
echo "  Outputs:"
aws cloudformation describe-stacks \
  --stack-name "${STACK_NAME}" \
  --region "${REGION}" \
  --query "Stacks[0].Outputs[*].[OutputKey,OutputValue]" \
  --output table

echo ""
echo "  Next: cd demo-01-strands-bedrock && python deploy.py"
