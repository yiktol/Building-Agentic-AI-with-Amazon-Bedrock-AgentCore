"""
Demo 3: Deploy session-aware agent with extended idle timeout.

Sets idleRuntimeSessionTimeout to 1800s (30 min) for demo purposes.

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
from shared.deploy_helpers import (
    get_aws_context,
    create_execution_role,
    build_and_upload_package,
    create_runtime,
    create_endpoint,
    save_config,
)
from shared.colors import banner, step_header, success, info, config_val, done

import boto3

AGENT_NAME = f"demo03_session_mgmt_{int(time.time()) % 100000}"
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
    region, account_id = get_aws_context()

    banner("Demo 3: Session Management → microVM Isolation")

    # Check if already deployed
    existing = check_existing(region)
    if existing:
        success(f"Already deployed: {existing['runtime_id']}")
        config_val("Runtime ARN", existing["runtime_arn"])
        done("python invoke.py")
        return

    config_val("Agent", AGENT_NAME)
    config_val("Region", region)
    config_val("Idle Timeout", "1800s (30 min)")
    config_val("Max Lifetime", "7200s (2 hr)")

    step_header(1, 4, "Creating IAM execution role")
    role_arn = create_execution_role(AGENT_NAME, region, account_id)
    success(f"Role ready")

    step_header(2, 4, "Building arm64 package → S3")
    s3_bucket = build_and_upload_package(
        AGENT_NAME, region, account_id, agent_files=["agent.py"]
    )
    success(f"Uploaded to S3")

    step_header(3, 4, "Creating AgentCore Runtime")
    info("lifecycleConfiguration: idleTimeout=1800, maxLifetime=7200")
    runtime = create_runtime(
        agent_name=AGENT_NAME,
        region=region,
        role_arn=role_arn,
        s3_bucket=s3_bucket,
        entry_point="agent.py",
        lifecycle_config={
            "idleRuntimeSessionTimeout": 1800,
            "maxLifetime": 7200,
        },
        description="Demo 3: Session management with microVM isolation",
    )
    success(f"Runtime READY: {runtime['runtime_id']}")

    step_header(4, 4, "Creating endpoint")
    create_endpoint(runtime["runtime_id"], region)
    success("Endpoint READY")

    save_config(AGENT_NAME, runtime["runtime_id"], runtime["runtime_arn"], region)

    done("python invoke.py")
    config_val("Runtime ARN", runtime["runtime_arn"])
    print()


if __name__ == "__main__":
    main()
