#!/bin/bash
# Deploy the Module 06 Observability prerequisites CloudFormation stack.
# Usage: ./deploy-stack.sh [region]

REGION=${1:-$(aws configure get region 2>/dev/null || echo "ap-southeast-1")}
STACK_NAME="mlagac-m06-demo-prereqs"

echo "Deploying stack: $STACK_NAME in $REGION"
echo ""
echo "NOTE: CloudWatch Transaction Search must be enabled separately."
echo "      Console: CloudWatch > X-Ray settings > Transaction Search > Enable"
echo ""

aws cloudformation deploy \
  --template-file "$(dirname "$0")/prerequisites.yaml" \
  --stack-name "$STACK_NAME" \
  --capabilities CAPABILITY_NAMED_IAM \
  --region "$REGION" \
  --no-fail-on-empty-changeset

echo ""
echo "Stack outputs:"
aws cloudformation describe-stacks \
  --stack-name "$STACK_NAME" \
  --region "$REGION" \
  --query 'Stacks[0].Outputs[*].[OutputKey,OutputValue]' \
  --output table

echo ""
echo "IMPORTANT: Enable CloudWatch Transaction Search if not already done:"
echo "  Console: https://console.aws.amazon.com/cloudwatch/home?region=$REGION#xray:settings/transaction-search"
