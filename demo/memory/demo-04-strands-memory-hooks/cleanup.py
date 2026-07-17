"""Demo 4: Clean up AgentCore Runtime only (memory stays in CloudFormation)."""

import json
import os
import sys
import time

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))
from shared.deploy_helpers import load_config
from shared.colors import banner, success, info, done

import boto3


def main():
    os.chdir(os.path.dirname(os.path.abspath(__file__)))
    banner("Demo 4: Cleanup")

    config = load_config()
    region = config["region"]
    runtime_id = config["runtime_id"]
    agent_name = config["agent_name"]

    control = boto3.client("bedrock-agentcore-control", region_name=region)
    s3 = boto3.client("s3", region_name=region)

    # Delete endpoints
    try:
        endpoints = control.list_agent_runtime_endpoints(agentRuntimeId=runtime_id)
        for ep in endpoints.get("runtimeEndpoints", []):
            if ep["name"] != "DEFAULT":
                control.delete_agent_runtime_endpoint(agentRuntimeId=runtime_id, endpointName=ep["name"])
        time.sleep(30)
    except Exception as e:
        info(f"Warning: {e}")

    # Delete runtime
    try:
        control.delete_agent_runtime(agentRuntimeId=runtime_id)
        success(f"Deleted runtime: {runtime_id}")
        time.sleep(15)
    except Exception as e:
        info(f"Warning: {e}")

    # Delete S3 artifact
    try:
        s3.delete_object(Bucket=config["s3_bucket"], Key=f"{agent_name}/code.zip")
        success(f"Deleted S3 artifact")
    except Exception as e:
        info(f"Warning: {e}")

    # Remove config
    if os.path.exists("runtime_config.json"):
        os.remove("runtime_config.json")

    info("Memory resource managed by CloudFormation (not deleted)")
    done()


if __name__ == "__main__":
    main()
