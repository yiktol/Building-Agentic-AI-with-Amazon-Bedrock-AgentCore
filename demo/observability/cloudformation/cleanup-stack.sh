#!/bin/bash
# Delete the Module 06 Observability prerequisites CloudFormation stack.
# Usage: ./cleanup-stack.sh [region]

REGION=${1:-$(aws configure get region 2>/dev/null || echo "ap-southeast-1")}
STACK_NAME="mlagac-m06-demo-prereqs"

echo "Deleting stack: $STACK_NAME in $REGION"

# Empty the S3 bucket first
BUCKET=$(aws cloudformation describe-stacks \
  --stack-name "$STACK_NAME" \
  --region "$REGION" \
  --query 'Stacks[0].Outputs[?OutputKey==`CodeBucketName`].OutputValue' \
  --output text 2>/dev/null)

if [ -n "$BUCKET" ]; then
  echo "Emptying bucket: $BUCKET"
  aws s3 rm "s3://$BUCKET" --recursive --region "$REGION" 2>/dev/null
fi

aws cloudformation delete-stack \
  --stack-name "$STACK_NAME" \
  --region "$REGION"

echo "Waiting for deletion..."
aws cloudformation wait stack-delete-complete \
  --stack-name "$STACK_NAME" \
  --region "$REGION"

echo "✓ Stack deleted."
