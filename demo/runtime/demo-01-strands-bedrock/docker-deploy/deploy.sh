#!/bin/bash
# Deploy the Docker-based agent to AgentCore Runtime.
# Safe for repeated deploy/cleanup cycles — always restores config from git.
set -e

SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
cd "$SCRIPT_DIR"

# Always restore agentcore.json from git before deploying
# This prevents empty runtimes[] caused by previous `agentcore remove all`
git checkout -- agentcore/agentcore.json 2>/dev/null || true

# Ensure uv.lock exists
if [ ! -f app/StrandsDemo/uv.lock ]; then
    echo "Generating uv.lock..."
    (cd app/StrandsDemo && uv lock)
fi

# Ensure CDK project exists
if [ ! -d agentcore/cdk/node_modules ]; then
    echo "Setting up CDK project..."
    if [ ! -d agentcore/cdk ]; then
        cp -r "$(npm root -g)/@aws/agentcore/dist/assets/cdk" agentcore/cdk
    fi
    (cd agentcore/cdk && npm install)
fi

echo ""
echo "=== Deploying StrandsDemo ==="
agentcore deploy -y "$@"
