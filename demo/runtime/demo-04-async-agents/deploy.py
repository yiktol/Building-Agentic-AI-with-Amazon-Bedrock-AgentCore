"""
Demo 4: Deploy async agent with extended session lifetime.

Sets maxLifetime to 28800s (8 hours) for long-running workloads.

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

AGENT_NAME = f"demo04_async_agent_{int(time.time()) % 100000}"


def main():
    os.chdir(os.path.dirname(os.path.abspath(__file__)))
    region, account_id = get_aws_context()

    banner("Demo 4: Async Agents → Long-Running Background Tasks")
    config_val("Agent", AGENT_NAME)
    config_val("Region", region)
    config_val("Max Lifetime", "28800s (8 hours)")

    step_header(1, 4, "Creating IAM execution role")
    role_arn = create_execution_role(AGENT_NAME, region, account_id)
    success("Role ready")

    step_header(2, 4, "Building arm64 package → S3")
    info("Includes: add_async_task / complete_async_task pattern")
    s3_bucket = build_and_upload_package(
        AGENT_NAME, region, account_id, agent_files=["agent.py"]
    )
    success("Uploaded to S3")

    step_header(3, 4, "Creating AgentCore Runtime (8hr max)")
    info("lifecycleConfiguration: maxLifetime=28800")
    runtime = create_runtime(
        agent_name=AGENT_NAME,
        region=region,
        role_arn=role_arn,
        s3_bucket=s3_bucket,
        entry_point="agent.py",
        lifecycle_config={
            "idleRuntimeSessionTimeout": 1800,
            "maxLifetime": 28800,
        },
        description="Demo 4: Async agents with background task processing",
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
