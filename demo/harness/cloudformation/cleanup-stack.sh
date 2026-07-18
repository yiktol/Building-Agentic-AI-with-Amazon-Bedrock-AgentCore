#!/bin/bash
REGION=${1:-$(aws configure get region 2>/dev/null || echo "ap-southeast-1")}
STACK_NAME="mlagac-m07-demo-prereqs"
echo "Deleting stack: $STACK_NAME in $REGION"
aws cloudformation delete-stack --stack-name "$STACK_NAME" --region "$REGION"
echo "Waiting for deletion..."
aws cloudformation wait stack-delete-complete --stack-name "$STACK_NAME" --region "$REGION"
echo "✓ Stack deleted."
