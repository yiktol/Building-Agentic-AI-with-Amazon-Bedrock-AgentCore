"""
Shared update helper for pushing new code to an existing AgentCore Runtime.

Uses update_agent_runtime() to deploy a new version without recreating
the runtime or endpoint. This is the production pattern for iterating
on agent code.
"""

import json
import os
import shutil
import subprocess
import sys
import time

import boto3


def update_runtime(
    config_file: str = "runtime_config.json",
    agent_files: list = None,
    requirements_file: str = "requirements.txt",
):
    """Rebuild code, upload to S3, and call update_agent_runtime().

    Reads runtime_config.json for runtime_id, region, s3_bucket, s3_key.
    """
    if agent_files is None:
        agent_files = ["agent.py"]

    if not os.path.exists(config_file):
        print("  ERROR: runtime_config.json not found. Run deploy.py first.")
        sys.exit(1)

    with open(config_file) as f:
        config = json.load(f)

    region = config["region"]
    runtime_id = config["runtime_id"]
    s3_bucket = config["s3_bucket"]
    s3_key = config["s3_key"]

    # Rebuild arm64 package
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
    for src in agent_files:
        subprocess.run(["zip", zip_file, src], check=True, capture_output=True)

    # Upload new code
    s3 = boto3.client("s3", region_name=region)
    s3.upload_file(zip_file, s3_bucket, s3_key)

    shutil.rmtree(pkg_dir)
    os.remove(zip_file)

    # Update runtime (new version of the code)
    control = boto3.client("bedrock-agentcore-control", region_name=region)

    # Get current runtime config for required fields
    current = control.get_agent_runtime(agentRuntimeId=runtime_id)

    control.update_agent_runtime(
        agentRuntimeId=runtime_id,
        agentRuntimeArtifact={
            "codeConfiguration": {
                "code": {"s3": {"bucket": s3_bucket, "prefix": s3_key}},
                "runtime": "PYTHON_3_13",
                "entryPoint": [agent_files[0]],
            }
        },
        roleArn=current["roleArn"],
        networkConfiguration=current["networkConfiguration"],
    )

    # Wait for READY
    while True:
        resp = control.get_agent_runtime(agentRuntimeId=runtime_id)
        status = resp["status"]
        if status == "READY":
            return runtime_id
        if "FAILED" in status:
            print(f"  ERROR: Update failed: {resp.get('failureReason', status)}")
            sys.exit(1)
        time.sleep(10)
