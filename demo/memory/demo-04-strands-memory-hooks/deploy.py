"""
Demo 4: Deploy Strands agent with memory hooks.

Memory resource comes from CloudFormation. This script only deploys
the AgentCore Runtime (build → upload → create runtime → endpoint).

Usage:
    python deploy.py
"""

import json
import os
import sys
import time

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))
from shared.stack_config import get_config
from shared.deploy_helpers import (
    build_and_upload_package,
    create_runtime,
    create_endpoint,
    save_config,
)
from shared.colors import banner, step_header, success, info, config_val, done

AGENT_NAME = f"demo04_hooks_{int(time.time()) % 100000}"
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
        import boto3
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

    banner("Demo 4: Strands Agent \u2014 Memory Hooks")

    # Check if already deployed
    existing = check_existing(cfg["region"])
    if existing:
        success(f"Already deployed: {existing['runtime_id']}")
        config_val("Runtime ARN", existing["runtime_arn"])
        config_val("Memory ID", existing.get("memory_id", "N/A"))
        done("python invoke.py")
        return

    config_val("Agent", AGENT_NAME)
    config_val("Region", cfg["region"])
    config_val("Memory ID (Semantic)", cfg["memory_semantic_id"])

    # Step 1: Build + Upload
    step_header(1, 3, "Building arm64 package → S3")
    info("Using S3 bucket and IAM role from CloudFormation stack")
    s3_bucket = cfg["s3_bucket"]
    build_and_upload_package(
        AGENT_NAME, cfg["region"], cfg["account_id"], agent_files=["agent.py"]
    )
    success(f"Uploaded to s3://{s3_bucket}/{AGENT_NAME}/code.zip")

    # Step 2: Create Runtime
    step_header(2, 3, "Creating AgentCore Runtime")
    info("Hooks fire automatically: MessageAdded → retrieve, AfterInvocation → save")
    runtime = create_runtime(
        agent_name=AGENT_NAME,
        region=cfg["region"],
        role_arn=cfg["runtime_role_arn"],
        s3_bucket=s3_bucket,
        entry_point="agent.py",
        description="Demo 4: Strands agent with memory hooks",
    )
    success(f"Runtime READY: {runtime['runtime_id']}")

    # Step 3: Create Endpoint
    step_header(3, 3, "Creating endpoint")
    create_endpoint(runtime["runtime_id"], cfg["region"])
    success("Endpoint READY")

    # Save config for invoke/cleanup
    save_config({
        "agent_name": AGENT_NAME,
        "runtime_id": runtime["runtime_id"],
        "runtime_arn": runtime["runtime_arn"],
        "memory_id": cfg["memory_semantic_id"],
        "region": cfg["region"],
        "s3_bucket": s3_bucket,
    })

    done("python invoke.py")
    config_val("Runtime ARN", runtime["runtime_arn"])
    config_val("Memory ID", cfg["memory_semantic_id"])
    print()


if __name__ == "__main__":
    main()
