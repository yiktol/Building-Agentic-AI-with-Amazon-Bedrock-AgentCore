"""Demo 1: Cleanup MCP Server runtime."""

import json
import os
import sys
import time

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))
from shared.colors import banner, success, info, done

import boto3


def main():
    os.chdir(os.path.dirname(os.path.abspath(__file__)))
    banner("Demo 1: Cleanup")
    if not os.path.exists("runtime_config.json"):
        info("No runtime_config.json found")
        return
    with open("runtime_config.json") as f:
        config = json.load(f)

    control = boto3.client("bedrock-agentcore-control", region_name=config["region"])
    try:
        eps = control.list_agent_runtime_endpoints(agentRuntimeId=config["runtime_id"])
        for ep in eps.get("runtimeEndpoints", []):
            if ep["name"] != "DEFAULT":
                control.delete_agent_runtime_endpoint(agentRuntimeId=config["runtime_id"], endpointName=ep["name"])
        time.sleep(15)
        control.delete_agent_runtime(agentRuntimeId=config["runtime_id"])
        success(f"Deleted runtime: {config['runtime_id']}")
    except Exception as e:
        info(f"Runtime: {e}")

    s3 = boto3.client("s3", region_name=config["region"])
    try:
        s3.delete_object(Bucket=config["s3_bucket"], Key=config["s3_key"])
        success("Deleted S3 artifact")
    except Exception:
        pass

    os.remove("runtime_config.json")
    done()


if __name__ == "__main__":
    main()
