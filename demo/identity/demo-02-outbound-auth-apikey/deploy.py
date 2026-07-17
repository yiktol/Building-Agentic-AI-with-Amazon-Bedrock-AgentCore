"""
Demo 2: Deploy agent + create API key credential provider.

Requires DEMO_API_KEY env var (any string for testing).

Usage:
    export DEMO_API_KEY="sk-your-key-here"
    python deploy.py
"""

import json
import os
import sys
import time

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))
from shared.stack_config import get_config
from shared.deploy_helpers import build_and_upload, create_runtime
from shared.colors import banner, step_header, success, info, error, config_val, done

import boto3

AGENT_NAME = f"demo02_outbound_apikey_{int(time.time()) % 100000}"
PROVIDER_NAME = "demo-apikey-provider"
CONFIG_FILE = "runtime_config.json"


def check_existing(region):
    """Check if a previously deployed runtime still exists and is READY."""
    if not os.path.exists(CONFIG_FILE):
        return None
    with open(CONFIG_FILE) as f:
        config = json.load(f)
    runtime_id = config.get("runtime_id")
    if not runtime_id:
        return None
    try:
        control = boto3.client("bedrock-agentcore-control", region_name=region)
        resp = control.get_agent_runtime(agentRuntimeId=runtime_id)
        if resp.get("status") in ("READY", "ACTIVE"):
            return config
    except Exception:
        pass
    return None


def main():
    os.chdir(os.path.dirname(os.path.abspath(__file__)))
    cfg = get_config()

    # Check if already deployed
    existing = check_existing(cfg["region"])
    if existing:
        banner("Demo 2: Outbound Auth \u2014 API Key (Token Vault)")
        success(f"Already deployed: {existing['runtime_id']}")
        config_val("Runtime ARN", existing["runtime_arn"])
        done("python invoke.py")
        return

    api_key = os.environ.get("DEMO_API_KEY", "")
    if not api_key:
        error("Set DEMO_API_KEY: export DEMO_API_KEY=\"sk-your-key\"")
        sys.exit(1)

    banner("Demo 2: Outbound Auth — API Key (Token Vault)")
    config_val("Agent", AGENT_NAME)
    config_val("Provider", PROVIDER_NAME)

    step_header(1, 3, "Creating API key credential provider")
    info("Stores key in Secrets Manager via AgentCore Identity")
    try:
        from bedrock_agentcore.services.identity import IdentityClient
        identity = IdentityClient(cfg["region"])
        identity.create_api_key_credential_provider({"name": PROVIDER_NAME, "apiKey": api_key})
        success(f"Created: {PROVIDER_NAME}")
    except Exception as e:
        if "already exists" in str(e).lower() or "Conflict" in str(e):
            success(f"Provider already exists: {PROVIDER_NAME}")
        else:
            error(f"Failed: {e}")
            sys.exit(1)

    step_header(2, 3, "Building arm64 package → S3")
    s3_key = build_and_upload(AGENT_NAME, cfg["region"], cfg["s3_bucket"], ["agent.py"])
    success(f"Uploaded to S3")

    step_header(3, 3, "Creating AgentCore Runtime")
    info("Role has GetResourceApiKey + secretsmanager:GetSecretValue")
    runtime = create_runtime(
        agent_name=AGENT_NAME, region=cfg["region"],
        role_arn=cfg["role_arn"], s3_bucket=cfg["s3_bucket"], s3_key=s3_key,
        description="Demo 2: Outbound auth with API key credential provider",
    )
    success(f"Runtime READY: {runtime['runtime_id']}")

    state = {
        "agent_name": AGENT_NAME, "runtime_id": runtime["runtime_id"],
        "runtime_arn": runtime["runtime_arn"], "region": cfg["region"],
        "s3_bucket": cfg["s3_bucket"], "s3_key": s3_key,
        "provider_name": PROVIDER_NAME,
    }
    with open("runtime_config.json", "w") as f:
        json.dump(state, f, indent=2)

    done("python invoke.py")
    config_val("Runtime ARN", runtime["runtime_arn"])
    print()


if __name__ == "__main__":
    main()
