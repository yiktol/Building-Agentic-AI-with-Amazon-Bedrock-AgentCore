#!/bin/bash
REGION=${1:-$(aws configure get region 2>/dev/null || echo "ap-southeast-1")}
STACK_NAME="mlagac-m07-demo-prereqs"
echo "Deploying stack: $STACK_NAME in $REGION"
aws cloudformation deploy \
  --template-file "$(dirname "$0")/prerequisites.yaml" \
  --stack-name "$STACK_NAME" \
  --capabilities CAPABILITY_NAMED_IAM \
  --region "$REGION" \
  --no-fail-on-empty-changeset
echo ""
echo "Stack outputs:"
aws cloudformation describe-stacks \
  --stack-name "$STACK_NAME" --region "$REGION" \
  --query 'Stacks[0].Outputs[*].[OutputKey,OutputValue]' --output table
