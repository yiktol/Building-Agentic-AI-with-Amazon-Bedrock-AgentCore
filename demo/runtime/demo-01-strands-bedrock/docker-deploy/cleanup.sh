#!/bin/bash
# Clean up the deployed agent and restore config for next deploy.
set -e

SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
cd "$SCRIPT_DIR"

STACK_NAME="AgentCore-StrandsDemo-default"
REGION="${1:-ap-southeast-1}"

echo "=== Cleaning up StrandsDemo ==="
echo "  Stack: $STACK_NAME"
echo "  Region: $REGION"
echo ""

# Delete the CloudFormation stack directly (more reliable than agentcore remove)
echo "Deleting CloudFormation stack..."
aws cloudformation delete-stack \
    --stack-name "$STACK_NAME" \
    --region "$REGION" 2>/dev/null || true

echo "Waiting for deletion..."
aws cloudformation wait stack-delete-complete \
    --stack-name "$STACK_NAME" \
    --region "$REGION" 2>/dev/null || true

# Restore agentcore.json so runtimes[] is intact for next deploy
git checkout -- agentcore/agentcore.json 2>/dev/null || true

# Clean CLI state (but keep cdk/)
rm -rf agentcore/.cli/logs agentcore/state 2>/dev/null || true

echo ""
echo "✅ Cleanup complete. Ready to deploy again with: bash deploy.sh"
