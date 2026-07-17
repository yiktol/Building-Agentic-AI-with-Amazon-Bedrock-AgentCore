"""
Demo 2: Deploy LangGraph + Bedrock agent to AgentCore Runtime.

Shows that the deployment is IDENTICAL to Demo 1 — only agent.py changes.

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

AGENT_NAME = f"demo02_langgraph_bedrock_{int(time.time()) % 100000}"


def main():
    os.chdir(os.path.dirname(os.path.abspath(__file__)))
    region, account_id = get_aws_context()

    banner("Demo 2: LangGraph + Bedrock → AgentCore Runtime")
    config_val("Agent", AGENT_NAME)
    config_val("Region", region)
    config_val("Account", account_id)
    info("Same deployment API as Demo 1 — only agent.py differs")

    step_header(1, 4, "Creating IAM execution role")
    info("Trust policy: bedrock-agentcore.amazonaws.com")
    role_arn = create_execution_role(AGENT_NAME, region, account_id)
    success(f"Role ready: agentcore-{AGENT_NAME}-role")

    step_header(2, 4, "Building arm64 package → S3")
    info("Dependencies: langgraph, langchain-aws, langchain-core")
    s3_bucket = build_and_upload_package(
        AGENT_NAME, region, account_id, agent_files=["agent.py"]
    )
    success(f"Uploaded to s3://{s3_bucket}/{AGENT_NAME}/code.zip")

    step_header(3, 4, "Creating AgentCore Runtime")
    info("API: create_agent_runtime() — identical to Demo 1")
    info("Protocol: HTTP | Network: PUBLIC")
    runtime = create_runtime(
        agent_name=AGENT_NAME,
        region=region,
        role_arn=role_arn,
        s3_bucket=s3_bucket,
        entry_point="agent.py",
        description="Demo 2: LangGraph with Bedrock — framework agnosticism",
    )
    success(f"Runtime READY: {runtime['runtime_id']}")

    step_header(4, 4, "Creating endpoint")
    info("API: create_agent_runtime_endpoint()")
    create_endpoint(runtime["runtime_id"], region)
    success("Endpoint READY — agent is now invocable")

    save_config(AGENT_NAME, runtime["runtime_id"], runtime["runtime_arn"], region)

    done("python invoke.py")
    config_val("Runtime ARN", runtime["runtime_arn"])
    print()


if __name__ == "__main__":
    main()
