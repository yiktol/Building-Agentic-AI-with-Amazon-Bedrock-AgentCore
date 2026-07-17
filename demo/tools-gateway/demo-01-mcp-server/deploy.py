"""
Demo 1: Deploy MCP Server to AgentCore Runtime.

Key difference from agent deployment: serverProtocol = "MCP" (not HTTP).

Usage:
    python deploy.py
"""

import json
import os
import shutil
import subprocess
import sys
import time

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))
from shared.stack_config import get_config
from shared.colors import banner, step_header, success, info, config_val, done

import boto3
from botocore.exceptions import ClientError

AGENT_NAME = f"demo01_mcp_server_{int(time.time()) % 100000}"


def main():
    os.chdir(os.path.dirname(os.path.abspath(__file__)))
    cfg = get_config()

    banner("Demo 1: MCP Server on AgentCore Runtime")
    config_val("Server", AGENT_NAME)
    config_val("Protocol", "MCP (port 8000, /mcp)")
    config_val("Region", cfg["region"])

    # Build package
    step_header(1, 2, "Building arm64 package → S3")
    info("MCP server uses mcp>=1.10.0 (FastMCP with streamable-HTTP)")
    s3_key = f"{AGENT_NAME}/code.zip"
    pkg_dir = "deployment_package"
    zip_file = "deployment_package.zip"

    if os.path.isdir(pkg_dir):
        shutil.rmtree(pkg_dir)
    subprocess.run([
        "uv", "pip", "install", "--python-platform", "aarch64-manylinux2014",
        "--python-version", "3.13", "--target", pkg_dir,
        "--only-binary", ":all:", "-r", "requirements.txt",
    ], check=True, capture_output=True)
    subprocess.run(["zip", "-r", f"../{zip_file}", "."], cwd=pkg_dir, check=True, capture_output=True)
    subprocess.run(["zip", zip_file, "mcp_server.py"], check=True, capture_output=True)

    s3 = boto3.client("s3", region_name=cfg["region"])
    s3.upload_file(zip_file, cfg["s3_bucket"], s3_key)
    shutil.rmtree(pkg_dir)
    os.remove(zip_file)
    success(f"Uploaded to s3://{cfg['s3_bucket']}/{s3_key}")

    # Create runtime with MCP protocol
    step_header(2, 2, "Creating runtime (serverProtocol=MCP)")
    info("Key difference: protocolConfiguration.serverProtocol = 'MCP'")
    info("Server listens on port 8000 at /mcp (JSON-RPC 2.0)")
    control = boto3.client("bedrock-agentcore-control", region_name=cfg["region"])

    for attempt in range(5):
        try:
            resp = control.create_agent_runtime(
                agentRuntimeName=AGENT_NAME,
                agentRuntimeArtifact={
                    "codeConfiguration": {
                        "code": {"s3": {"bucket": cfg["s3_bucket"], "prefix": s3_key}},
                        "runtime": "PYTHON_3_13",
                        "entryPoint": ["mcp_server.py"],
                    }
                },
                roleArn=cfg["runtime_role_arn"],
                networkConfiguration={"networkMode": "PUBLIC"},
                protocolConfiguration={"serverProtocol": "MCP"},
                description="Demo 1: MCP Server with tools",
            )
            break
        except ClientError as e:
            if "role" in str(e).lower() and attempt < 4:
                time.sleep(2**attempt * 4)
            else:
                raise

    runtime_id = resp["agentRuntimeId"]
    runtime_arn = resp["agentRuntimeArn"]

    info("Waiting for READY...")
    while True:
        status = control.get_agent_runtime(agentRuntimeId=runtime_id)["status"]
        if status == "READY":
            break
        if "FAILED" in status:
            from shared.colors import error
            error(f"Failed: {status}")
            sys.exit(1)
        time.sleep(15)

    control.create_agent_runtime_endpoint(agentRuntimeId=runtime_id, name="default")
    while True:
        eps = control.list_agent_runtime_endpoints(agentRuntimeId=runtime_id)
        for ep in eps.get("runtimeEndpoints", []):
            if ep["name"] == "default" and ep["status"] == "READY":
                success(f"MCP Server READY: {runtime_id}")
                state = {
                    "agent_name": AGENT_NAME, "runtime_id": runtime_id,
                    "runtime_arn": runtime_arn, "region": cfg["region"],
                    "s3_bucket": cfg["s3_bucket"], "s3_key": s3_key,
                }
                with open("runtime_config.json", "w") as f:
                    json.dump(state, f, indent=2)
                done("python invoke.py")
                config_val("Runtime ARN", runtime_arn)
                print()
                return
        time.sleep(15)


if __name__ == "__main__":
    main()
