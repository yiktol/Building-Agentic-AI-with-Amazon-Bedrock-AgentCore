# Docker Deploy — AgentCore Starter Toolkit (CLI)

Alternative deployment path for Demo 1's agent using the **AgentCore Starter Toolkit CLI**.
Same agent code, deployed as a Docker container via `agentcore deploy`.

## Comparison: ZIP vs Docker (Starter Toolkit)

| | ZIP Deploy (`../deploy.py`) | Docker Deploy (this folder) |
|---|---|---|
| **Tool** | Python + uv + boto3 | AgentCore CLI (`@aws/agentcore`) |
| **Deploy command** | `python deploy.py` | `agentcore deploy -y` |
| **Build** | Local arm64 zip via uv | CLI handles Docker + ECR + CodeBuild |
| **API** | `codeConfiguration` (S3 zip) | `containerConfiguration` (ECR image) |
| **Cleanup** | `python cleanup.py` | `aws cloudformation delete-stack` |
| **Local deps** | Python + uv | Node.js + npm + AgentCore CLI |
| **Build time** | ~30s | ~3-5 min (includes CDK + Docker build) |
| **Best for** | Quick prototyping, classroom | Production, CI/CD pipelines |

## Prerequisites

```bash
# 1. Node.js 20+ (required for the CLI)
node --version   # must be 20+

# 2. Install the AgentCore CLI
npm install -g @aws/agentcore

# 3. Verify
agentcore --version

# 4. AWS CDK (used by the CLI for deployment)
npm install -g aws-cdk

# 5. Python 3.10+ (for agent code)
python3 --version

# 6. AWS credentials configured
aws sts get-caller-identity
```

**Required AWS permissions:** See [Use the AgentCore CLI](https://docs.aws.amazon.com/bedrock-agentcore/latest/devguide/runtime-permissions.html#runtime-permissions-cli).

**Model access:** Enable Anthropic Claude Haiku 4.5 (or Claude Sonnet 4.0) in the [Amazon Bedrock console](https://console.aws.amazon.com/bedrock/home#/modelaccess).

## Usage

### Deploy (builds container → ECR → creates runtime via CDK)

```bash
cd docker-deploy
agentcore deploy -y
```

This single command:
1. Builds a CDK CloudFormation stack
2. Creates an ECR repository
3. Builds an arm64 Docker image (via CodeBuild)
4. Pushes to ECR
5. Creates the AgentCore Runtime with `containerConfiguration`
6. Outputs the Runtime ARN

### Invoke (via CLI)

```bash
# Single prompt
agentcore invoke "What is the weather in Seattle?"

# Multi-turn session
SESSION_ID=$(uuidgen)
agentcore invoke --session-id "$SESSION_ID" "My name is Alice"
agentcore invoke --session-id "$SESSION_ID" "What is my name?"
```

### Invoke (via parent folder's scripts — same API)

```bash
# Create a runtime_config.json with the ARN from deploy output, then:
cd ..
python invoke.py
python invoke_agent.py
```

### Local Development

```bash
agentcore dev
# Starts agent locally — test before deploying
```

### Check Status

```bash
agentcore status
```

### Cleanup

```bash
# Option A: AgentCore CLI (recommended)
agentcore remove all      # Remove resources from config
agentcore deploy -y       # Deploy the removal (tears down AWS resources)

# Option B: Direct CloudFormation (if CLI has issues)
aws cloudformation delete-stack \
  --stack-name AgentCore-StrandsDemo-default \
  --region ap-southeast-1

aws cloudformation wait stack-delete-complete \
  --stack-name AgentCore-StrandsDemo-default \
  --region ap-southeast-1
```

## Project Structure

```
docker-deploy/
├── README.md                   ← This file
├── .gitignore                  ← Ignores CLI-generated files
├── agentcore/
│   ├── agentcore.json          ← Project + agent configuration
│   └── aws-targets.json        ← Deployment target (region + account)
├── app/
│   └── StrandsDemo/
│       ├── main.py             ← Agent code (same as ../agent.py)
│       ├── Dockerfile          ← Container definition
│       └── pyproject.toml      ← Python dependencies
└── (auto-generated on deploy)
    ├── agentcore/cdk/          ← CDK infrastructure code
    ├── agentcore/.cli/         ← CLI state + logs
    └── agentcore/state/        ← Deployment state
```

## Key Talking Points

1. **`agentcore deploy` = one command** — handles ECR, Docker build, push, CDK, runtime creation
2. **`agentcore dev` = local testing** — same HTTP contract as production
3. **`agentcore invoke` = test the deployed agent** — no separate client script needed
4. **Same agent code** — `main.py` is the same as `../agent.py`
5. **Same invoke API** — `invoke.py` from the parent folder works regardless of deploy method
6. **Production pattern** — CDK stack for infrastructure-as-code, container for reproducibility
