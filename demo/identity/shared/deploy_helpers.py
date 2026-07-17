"""
Shared deployment helpers for identity demos.

Uses the IAM role and S3 bucket from the CloudFormation stack.
Handles: arm64 package build, S3 upload, runtime create, endpoint create, cleanup.
"""

import json
import os
import shutil
import subprocess
import sys
import time

import boto3
from botocore.exceptions import ClientError


def build_and_upload(agent_name: str, region: str, s3_bucket: str, agent_files: list, requirements_file: str = "requirements.txt") -> str:
    """Build arm64 zip and upload to S3. Returns the S3 key."""
    s3 = boto3.client("s3", region_name=region)
    s3_key = f"{agent_name}/code.zip"
    pkg_dir = "deployment_package"
    zip_file = "deployment_package.zip"

    if os.path.isdir(pkg_dir):
        shutil.rmtree(pkg_dir)
    if os.path.exists(zip_file):
        os.remove(zip_file)

    subprocess.run([
        "uv", "pip", "install",
        "--python-platform", "aarch64-manylinux2014",
        "--python-version", "3.13",
        "--target", pkg_dir,
        "--only-binary", ":all:",
        "-r", requirements_file,
    ], check=True, capture_output=True)

    subprocess.run(["zip", "-r", f"../{zip_file}", "."], cwd=pkg_dir, check=True, capture_output=True)
    for src_file in agent_files:
        subprocess.run(["zip", zip_file, src_file], check=True, capture_output=True)

    s3.upload_file(zip_file, s3_bucket, s3_key)

    shutil.rmtree(pkg_dir)
    os.remove(zip_file)
    return s3_key


def create_runtime(agent_name: str, region: str, role_arn: str, s3_bucket: str, s3_key: str,
                   entry_point: str = "agent.py", authorizer_config: dict = None,
                   description: str = "") -> dict:
    """Create AgentCore Runtime + endpoint. Returns dict with runtime_id and runtime_arn."""
    control = boto3.client("bedrock-agentcore-control", region_name=region)

    create_params = dict(
        agentRuntimeName=agent_name,
        agentRuntimeArtifact={
            "codeConfiguration": {
                "code": {"s3": {"bucket": s3_bucket, "prefix": s3_key}},
                "runtime": "PYTHON_3_13",
                "entryPoint": [entry_point],
            }
        },
        roleArn=role_arn,
        networkConfiguration={"networkMode": "PUBLIC"},
        protocolConfiguration={"serverProtocol": "HTTP"},
        description=description or f"Identity demo: {agent_name}",
    )
    if authorizer_config:
        create_params["authorizerConfiguration"] = authorizer_config

    # Retry for IAM propagation
    response = None
    for attempt in range(5):
        try:
            response = control.create_agent_runtime(**create_params)
            break
        except ClientError as e:
            if "role" in str(e).lower() and attempt < 4:
                time.sleep(2**attempt * 4)
            else:
                raise

    runtime_id = response["agentRuntimeId"]
    runtime_arn = response["agentRuntimeArn"]

    # Wait for READY
    while True:
        status = control.get_agent_runtime(agentRuntimeId=runtime_id)["status"]
        if status == "READY":
            break
        if "FAILED" in status:
            raise RuntimeError(f"Runtime failed: {status}")
        time.sleep(15)

    # Create endpoint
    control.create_agent_runtime_endpoint(agentRuntimeId=runtime_id, name="default")
    while True:
        eps = control.list_agent_runtime_endpoints(agentRuntimeId=runtime_id)
        for ep in eps.get("runtimeEndpoints", []):
            if ep["name"] == "default" and ep["status"] == "READY":
                return {"runtime_id": runtime_id, "runtime_arn": runtime_arn}
        time.sleep(15)


def cleanup_runtime(config_file: str = "runtime_config.json"):
    """Delete AgentCore Runtime resources. S3/IAM/Cognito are in CloudFormation."""
    if not os.path.exists(config_file):
        print("  No runtime_config.json found.")
        return

    with open(config_file) as f:
        config = json.load(f)

    region = config["region"]
    runtime_id = config["runtime_id"]
    s3_bucket = config.get("s3_bucket", "")
    s3_key = config.get("s3_key", "")

    control = boto3.client("bedrock-agentcore-control", region_name=region)

    # Delete endpoints
    try:
        eps = control.list_agent_runtime_endpoints(agentRuntimeId=runtime_id)
        for ep in eps.get("runtimeEndpoints", []):
            if ep["name"] != "DEFAULT":
                control.delete_agent_runtime_endpoint(agentRuntimeId=runtime_id, endpointName=ep["name"])
        time.sleep(15)
    except Exception:
        pass

    # Delete runtime
    try:
        control.delete_agent_runtime(agentRuntimeId=runtime_id)
        print(f"  ✓ Deleted runtime: {runtime_id}")
    except Exception as e:
        print(f"  Warning: {e}")

    # Delete S3 code artifact (bucket stays — managed by CFN)
    if s3_bucket and s3_key:
        try:
            s3 = boto3.client("s3", region_name=region)
            s3.delete_object(Bucket=s3_bucket, Key=s3_key)
            print(f"  ✓ Deleted s3://{s3_bucket}/{s3_key}")
        except Exception:
            pass

    os.remove(config_file)
    print("  ✓ Cleanup complete (CFN resources remain)")
