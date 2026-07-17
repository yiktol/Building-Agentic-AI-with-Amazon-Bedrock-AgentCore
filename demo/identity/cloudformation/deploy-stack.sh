#!/usr/bin/env bash
set -euo pipefail

STACK_NAME="mlagac-m03-identity-prereqs"
TEMPLATE_FILE="$(dirname "$0")/prerequisites.yaml"
REGION="${1:-$(aws configure get region 2>/dev/null || echo 'ap-southeast-1')}"

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
  --tags Project=MLAGAC-Module03-Demo

echo ""
echo "✓ Stack deployed!"
echo ""

# Create test user (CFN cannot create Cognito users directly)
POOL_ID=$(aws cloudformation describe-stacks --stack-name "${STACK_NAME}" --region "${REGION}" \
  --query "Stacks[0].Outputs[?OutputKey=='CognitoUserPoolId'].OutputValue" --output text)

echo "  Creating test user in Cognito..."
aws cognito-idp admin-create-user \
  --user-pool-id "${POOL_ID}" \
  --username "demouser" \
  --temporary-password "DemoPass123!" \
  --user-attributes Name=email,Value=demo@example.com \
  --message-action SUPPRESS \
  --region "${REGION}" 2>/dev/null || echo "  (user may already exist)"

aws cognito-idp admin-set-user-password \
  --user-pool-id "${POOL_ID}" \
  --username "demouser" \
  --password "DemoPass123!" \
  --permanent \
  --region "${REGION}" 2>/dev/null || true

echo "  ✓ Test user: demouser / DemoPass123!"
echo ""

echo "  Outputs:"
aws cloudformation describe-stacks \
  --stack-name "${STACK_NAME}" \
  --region "${REGION}" \
  --query "Stacks[0].Outputs[*].[OutputKey,OutputValue]" \
  --output table

echo ""
echo "  Save outputs for demo scripts:"
echo "    export STACK_NAME=${STACK_NAME}"
echo "    export AWS_REGION=${REGION}"
echo ""
echo "  Next: cd demo-01-inbound-auth-cognito && python deploy.py"
