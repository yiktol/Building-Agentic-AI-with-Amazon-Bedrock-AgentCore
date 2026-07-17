"""
Demo 1: Deploy HR Assistant with OpenTelemetry instrumentation.

Deploys the HR Assistant agent to AgentCore Runtime with:
- opentelemetry-instrument as the entry point wrapper
- aws-opentelemetry-distro for automatic ADOT instrumentation
- X-Ray tracing enabled via IAM role

This is the foundation for all subsequent observability demos.

Usage:
    python deploy.py
"""

import json
import os
import shutil
import sys
import time

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))
from shared.stack_config import get_config
from shared.deploy_helpers import (
    build_and_upload_package,
    create_runtime_with_otel,
    save_config,
)
from shared.colors import banner, step_header, success, info, config_val, done

AGENT_NAME = f"demo01_observe_{int(time.time()) % 100000}"
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

    # Check if already deployed
    existing = check_existing(cfg["region"])
    if existing:
        banner("Demo 1: Observability Setup — Deploy with OTel")
        success(f"Already deployed: {existing['runtime_id']}")
        config_val("Runtime ARN", existing["runtime_arn"])
        config_val("Log Group", existing["log_group"])
        done("python invoke.py")
        return

    banner("Demo 1: Observability Setup — Deploy with OTel")
    config_val("Agent", AGENT_NAME)
    config_val("Region", cfg["region"])

    # Step 1: Build + Upload
    step_header(1, 2, "Building arm64 package with OTel + ADOT")
    info("Includes: aws-opentelemetry-distro, strands-agents[otel]")
    info("Entry point: opentelemetry-instrument agent.py")

    # Copy the shared agent
    shutil.copy(
        os.path.join(os.path.dirname(__file__), "..", "shared", "hr_assistant_agent.py"),
        "agent.py",
    )

    s3_key = build_and_upload_package(
        AGENT_NAME, cfg["region"], cfg["s3_bucket"], ["agent.py"]
    )
    success(f"Uploaded to s3://{cfg['s3_bucket']}/{s3_key}")

    # Step 2: Create Runtime with OTel
    step_header(2, 2, "Creating runtime with opentelemetry-instrument wrapper")
    info("entryPoint: ['opentelemetry-instrument', 'agent.py']")
    info("ADOT auto-instruments: Bedrock calls, Strands tools, agent lifecycle")

    runtime = create_runtime_with_otel(
        agent_name=AGENT_NAME,
        region=cfg["region"],
        role_arn=cfg["runtime_role_arn"],
        s3_bucket=cfg["s3_bucket"],
        s3_key=s3_key,
        entry_point="agent.py",
        description="Demo 1: HR Assistant with OTel instrumentation",
    )
    success(f"Runtime READY: {runtime['runtime_id']}")

    # Save config
    save_config({
        "agent_name": AGENT_NAME,
        "runtime_id": runtime["runtime_id"],
        "runtime_arn": runtime["runtime_arn"],
        "log_group": runtime["log_group"],
        "service_name": runtime["service_name"],
        "s3_bucket": cfg["s3_bucket"],
        "s3_key": s3_key,
        "region": cfg["region"],
        "eval_role_arn": cfg["eval_role_arn"],
    })

    # Clean up local copy
    if os.path.exists("agent.py"):
        os.remove("agent.py")

    done("python invoke.py")
    config_val("Runtime ARN", runtime["runtime_arn"])
    config_val("Log Group", runtime["log_group"])
    config_val("OTel Service", runtime["service_name"])
    info("")
    info("View traces in CloudWatch:")
    info(f"  Console → CloudWatch → GenAI Observability → Bedrock AgentCore")
    print()


if __name__ == "__main__":
    main()
