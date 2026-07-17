"""
Shared deployment helpers for Module 06 Observability demos.

Provides reusable functions for:
- arm64 deployment package building with pip
- S3 upload
- AgentCore Runtime creation with OTel instrumentation
- Endpoint creation and polling
- Cleanup
"""

import json
import os
import shutil
import subprocess
import sys
import time
import zipfile
from pathlib import Path

import boto3
from boto3.session import Session


def get_aws_context():
    """Get region and account ID from the current AWS session."""
    session = Session()
    region = os.environ.get("AWS_REGION") or session.region_name or "ap-southeast-1"
    account_id = session.client("sts").get_caller_identity()["Account"]
    return region, account_id


def build_and_upload_package(
    agent_name: str,
    region: str,
    s3_bucket: str,
    agent_files: list,
    requirements_file: str = "requirements.txt",
) -> str:
    """Build arm64 deployment package and upload to S3.

    Returns the S3 key.
    """
    s3 = boto3.client("s3", region_name=region)
    s3_key = f"{agent_name}/deployment_package.zip"
    build_dir = Path(f"/tmp/{agent_name}_build")  # nosec B108
    pkg_dir = build_dir / "pkg"

    # Clean previous build
    if build_dir.exists():
        shutil.rmtree(build_dir)
    pkg_dir.mkdir(parents=True)

    # Install arm64 dependencies
    print("  Installing arm64 dependencies...")
    subprocess.run(
        [
            sys.executable, "-m", "pip", "install",
            "-r", requirements_file,
            "-t", str(pkg_dir),
            "--platform", "manylinux2014_aarch64",
            "--only-binary=:all:",
            "--python-version", "3.13",
            "--quiet",
        ],
        check=True,
    )

    # Copy agent files
    for src_file in agent_files:
        shutil.copy(src_file, pkg_dir / Path(src_file).name)

    # Create zip
    zip_path = build_dir / "deployment_package.zip"
    with zipfile.ZipFile(zip_path, "w", zipfile.ZIP_DEFLATED) as zf:
        for root, _, files in os.walk(pkg_dir):
            for f in files:
                if f.endswith(".pyc") or "__pycache__" in root:
                    continue
                full = Path(root) / f
                zf.write(full, full.relative_to(pkg_dir))

    size_mb = zip_path.stat().st_size / (1024 * 1024)
    print(f"  ✓ Package: {zip_path.name} ({size_mb:.1f} MB)")

    # Upload
    print(f"  Uploading to s3://{s3_bucket}/{s3_key}...")
    s3.upload_file(str(zip_path), s3_bucket, s3_key)
    print("  ✓ Uploaded")

    # Clean up local
    shutil.rmtree(build_dir)
    return s3_key


def create_runtime_with_otel(
    agent_name: str,
    region: str,
    role_arn: str,
    s3_bucket: str,
    s3_key: str,
    entry_point: str = "agent.py",
    description: str = "",
) -> dict:
    """Create AgentCore Runtime with OpenTelemetry instrumentation and wait for READY.

    The key difference from other modules: entryPoint uses opentelemetry-instrument
    wrapper to enable automatic ADOT instrumentation.

    Returns dict with runtime_id, runtime_arn, log_group, service_name.
    """
    control = boto3.client("bedrock-agentcore-control", region_name=region)

    print(f"  Creating AgentCore Runtime '{agent_name}' with OTel instrumentation...")
    response = control.create_agent_runtime(
        agentRuntimeName=agent_name,
        agentRuntimeArtifact={
            "codeConfiguration": {
                "code": {"s3": {"bucket": s3_bucket, "prefix": s3_key}},
                "runtime": "PYTHON_3_13",
                # Key: opentelemetry-instrument wraps the agent for automatic tracing
                "entryPoint": ["opentelemetry-instrument", entry_point],
            }
        },
        roleArn=role_arn,
        networkConfiguration={"networkMode": "PUBLIC"},
        protocolConfiguration={"serverProtocol": "HTTP"},
        description=description or f"Module 06 demo: {agent_name}",
    )
    runtime_id = response["agentRuntimeId"]
    runtime_arn = response["agentRuntimeArn"]
    print(f"  ✓ Runtime created: {runtime_id}")

    # Poll for READY
    print("  Waiting for runtime to be ready...")
    for i in range(90):
        status_resp = control.get_agent_runtime(agentRuntimeId=runtime_id)
        status = status_resp["status"]
        if i % 4 == 0:
            print(f"    Status: {status}")
        if status in ("READY", "ACTIVE"):
            break
        if "FAILED" in status:
            reason = status_resp.get("failureReason", "Unknown")
            print(f"  ✗ Failed: {reason}")
            sys.exit(1)
        time.sleep(10)
    else:
        print("  ✗ Timed out waiting for runtime")
        sys.exit(1)

    log_group = f"/aws/bedrock-agentcore/runtimes/{runtime_id}-DEFAULT"
    service_name = f"{agent_name}.DEFAULT"

    return {
        "runtime_id": runtime_id,
        "runtime_arn": runtime_arn,
        "log_group": log_group,
        "service_name": service_name,
    }


def save_config(config: dict, config_file: str = "runtime_config.json"):
    """Save deployment config for invoke/cleanup scripts."""
    with open(config_file, "w") as f:
        json.dump(config, f, indent=2)
    print(f"  Config saved to: {config_file}")


def load_config(config_file: str = "runtime_config.json") -> dict:
    """Load deployment config from a previous deploy."""
    try:
        with open(config_file) as f:
            return json.load(f)
    except FileNotFoundError:
        print(f"Error: {config_file} not found. Run deploy.py first.")
        sys.exit(1)


def cleanup_runtime(config_file: str = "runtime_config.json"):
    """Delete AgentCore Runtime resources. S3/IAM stay in CloudFormation."""
    config = load_config(config_file)
    region = config["region"]
    runtime_id = config["runtime_id"]
    agent_name = config["agent_name"]
    s3_bucket = config.get("s3_bucket", "")
    s3_key = config.get("s3_key", "")

    control = boto3.client("bedrock-agentcore-control", region_name=region)
    s3 = boto3.client("s3", region_name=region)

    print(f"Cleaning up: {agent_name}")

    # Delete runtime
    try:
        control.delete_agent_runtime(agentRuntimeId=runtime_id)
        print(f"  ✓ Deleted runtime: {runtime_id}")
    except Exception as e:
        print(f"  Warning: {e}")

    # Delete S3 artifact
    if s3_bucket and s3_key:
        try:
            s3.delete_object(Bucket=s3_bucket, Key=s3_key)
            print(f"  ✓ Deleted s3://{s3_bucket}/{s3_key}")
        except Exception:
            pass

    # Remove config
    if os.path.exists(config_file):
        os.remove(config_file)

    print("  ✓ Cleanup complete (CFN resources remain)")
