"""
Demo 1: Deploy agent with inbound JWT auth (Cognito).

All AWS resources (Cognito, IAM, S3) come from the CloudFormation stack.
This script only deploys the AgentCore Runtime with customJWTAuthorizer.

Idempotent: if runtime_config.json exists and the runtime is still READY,
the script skips creation and reports the existing state.

Usage:
    python deploy.py
"""

import json
import os
import sys
import time

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))
from shared.stack_config import get_config
from shared.deploy_helpers import build_and_upload, create_runtime
from shared.colors import banner, step_header, success, info, config_val, done

import boto3

AGENT_NAME = f"demo01_inbound_auth_{int(time.time()) % 100000}"
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

    banner("Demo 1: Inbound Auth — Cognito JWT")

    # Check if already deployed
    existing = check_existing(cfg["region"])
    if existing:
        success(f"Already deployed: {existing['runtime_id']}")
        config_val("Runtime ARN", existing["runtime_arn"])
        done("python invoke.py")
        return

    config_val("Agent", AGENT_NAME)
    config_val("Region", cfg["region"])
    config_val("Discovery URL", cfg["cognito_discovery_url"])
    config_val("Allowed Client", cfg["cognito_user_client_id"])

    step_header(1, 2, "Building arm64 package → S3")
    info("Using IAM role and S3 bucket from CloudFormation stack")
    s3_key = build_and_upload(AGENT_NAME, cfg["region"], cfg["s3_bucket"], ["agent.py"])
    success(f"Uploaded to s3://{cfg['s3_bucket']}/{s3_key}")

    step_header(2, 2, "Creating runtime with customJWTAuthorizer")
    info("authorizerConfiguration.customJWTAuthorizer enabled")
    runtime = create_runtime(
        agent_name=AGENT_NAME,
        region=cfg["region"],
        role_arn=cfg["role_arn"],
        s3_bucket=cfg["s3_bucket"],
        s3_key=s3_key,
        authorizer_config={
            "customJWTAuthorizer": {
                "discoveryUrl": cfg["cognito_discovery_url"],
                "allowedClients": [cfg["cognito_user_client_id"]],
            }
        },
        description="Demo 1: Inbound Auth with Cognito JWT",
    )
    success(f"Runtime READY: {runtime['runtime_id']}")

    state = {
        "agent_name": AGENT_NAME,
        "runtime_id": runtime["runtime_id"],
        "runtime_arn": runtime["runtime_arn"],
        "region": cfg["region"],
        "s3_bucket": cfg["s3_bucket"],
        "s3_key": s3_key,
        "cognito_user_pool_id": cfg["cognito_user_pool_id"],
        "cognito_user_client_id": cfg["cognito_user_client_id"],
    }
    with open("runtime_config.json", "w") as f:
        json.dump(state, f, indent=2)

    done("python invoke.py")
    config_val("Runtime ARN", runtime["runtime_arn"])
    print()


if __name__ == "__main__":
    main()
