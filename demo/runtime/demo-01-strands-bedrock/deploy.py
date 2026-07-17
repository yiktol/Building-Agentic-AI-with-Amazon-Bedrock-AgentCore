"""
Demo 1: Deploy Strands + Bedrock agent to AgentCore Runtime.

This script demonstrates the full deployment lifecycle:
1. Create IAM execution role
2. Build arm64 deployment package with uv
3. Upload to S3
4. Create AgentCore Runtime
5. Create endpoint

Usage:
    python deploy.py
"""

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

AGENT_NAME = f"demo01_strands_bedrock_{int(time.time()) % 100000}"


def main():
    os.chdir(os.path.dirname(os.path.abspath(__file__)))
    region, account_id = get_aws_context()

    banner("Demo 1: Strands + Bedrock → AgentCore Runtime")
    config_val("Agent", AGENT_NAME)
    config_val("Region", region)
    config_val("Account", account_id)

    # Step 1: IAM Role
    step_header(1, 4, "Creating IAM execution role")
    info("Trust policy: bedrock-agentcore.amazonaws.com")
    info("Permissions: Bedrock, CloudWatch, X-Ray")
    role_arn = create_execution_role(AGENT_NAME, region, account_id)
    success(f"Role ready: agentcore-{AGENT_NAME}-role")

    # Step 2: Build + Upload
    step_header(2, 4, "Building arm64 package → S3")
    info("Using uv to compile arm64 wheels (Graviton)")
    info("Platform: aarch64-manylinux2014 | Python: 3.13")
    s3_bucket = build_and_upload_package(
        AGENT_NAME, region, account_id, agent_files=["agent.py"]
    )
    success(f"Uploaded to s3://{s3_bucket}/{AGENT_NAME}/code.zip")

    # Step 3: Create Runtime
    step_header(3, 4, "Creating AgentCore Runtime")
    info("API: create_agent_runtime()")
    info("Protocol: HTTP | Network: PUBLIC")
    runtime = create_runtime(
        agent_name=AGENT_NAME,
        region=region,
        role_arn=role_arn,
        s3_bucket=s3_bucket,
        entry_point="agent.py",
        description="Demo 1: Strands Agents with Bedrock on AgentCore Runtime",
    )
    success(f"Runtime READY: {runtime['runtime_id']}")

    # Step 4: Create Endpoint
    step_header(4, 4, "Creating endpoint")
    info("API: create_agent_runtime_endpoint()")
    info("Endpoint name: default")
    create_endpoint(runtime["runtime_id"], region)
    success("Endpoint READY — agent is now invocable")

    # Save config
    save_config(AGENT_NAME, runtime["runtime_id"], runtime["runtime_arn"], region)

    done("python invoke.py")
    config_val("Runtime ARN", runtime["runtime_arn"])
    print()


if __name__ == "__main__":
    main()
