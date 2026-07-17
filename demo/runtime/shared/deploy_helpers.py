"""
Shared deployment helpers for all Module 02 demos.

Provides reusable functions for:
- IAM role creation with AgentCore trust policy
- arm64 deployment package building with uv
- S3 upload
- AgentCore Runtime creation and polling
- Endpoint creation and polling
- Cleanup (tear down all resources)

Usage:
    from shared.deploy_helpers import (
        create_execution_role,
        build_and_upload_package,
        create_runtime,
        create_endpoint,
        cleanup_all,
    )
"""

import json
import os
import shutil
import subprocess
import sys
import time

import boto3
from boto3.session import Session


def get_aws_context():
    """Get region and account ID from the current AWS session."""
    session = Session()
    region = session.region_name or "ap-southeast-1"
    account_id = session.client("sts").get_caller_identity()["Account"]
    return region, account_id


def create_execution_role(agent_name: str, region: str, account_id: str) -> str:
    """Create IAM execution role with AgentCore permissions.

    Returns the role ARN.
    """
    iam = boto3.client("iam", region_name=region)
    role_name = f"agentcore-{agent_name}-role"

    trust_policy = {
        "Version": "2012-10-17",
        "Statement": [
            {
                "Effect": "Allow",
                "Principal": {"Service": "bedrock-agentcore.amazonaws.com"},
                "Action": "sts:AssumeRole",
                "Condition": {"StringEquals": {"aws:SourceAccount": account_id}},
            }
        ],
    }

    inline_policy = {
        "Version": "2012-10-17",
        "Statement": [
            {
                "Effect": "Allow",
                "Action": ["logs:DescribeLogStreams", "logs:CreateLogGroup"],
                "Resource": [f"arn:aws:logs:{region}:{account_id}:log-group:/aws/bedrock-agentcore/runtimes/*"],
            },
            {
                "Effect": "Allow",
                "Action": ["logs:DescribeLogGroups"],
                "Resource": [f"arn:aws:logs:{region}:{account_id}:log-group:*"],
            },
            {
                "Effect": "Allow",
                "Action": ["logs:CreateLogStream", "logs:PutLogEvents"],
                "Resource": [
                    f"arn:aws:logs:{region}:{account_id}:log-group:/aws/bedrock-agentcore/runtimes/*:log-stream:*"
                ],
            },
            {
                "Effect": "Allow",
                "Action": [
                    "xray:PutTraceSegments",
                    "xray:PutTelemetryRecords",
                    "xray:GetSamplingRules",
                    "xray:GetSamplingTargets",
                ],
                "Resource": ["*"],
            },
            {
                "Effect": "Allow",
                "Action": "cloudwatch:PutMetricData",
                "Resource": "*",
                "Condition": {"StringEquals": {"cloudwatch:namespace": "bedrock-agentcore"}},
            },
            {
                "Sid": "BedrockModelInvocation",
                "Effect": "Allow",
                "Action": [
                    "bedrock:InvokeModel",
                    "bedrock:InvokeModelWithResponseStream",
                ],
                "Resource": [
                    "arn:aws:bedrock:*::foundation-model/*",
                    f"arn:aws:bedrock:{region}:{account_id}:*",
                ],
            },
        ],
    }

    try:
        resp = iam.create_role(
            RoleName=role_name,
            AssumeRolePolicyDocument=json.dumps(trust_policy),
            Description=f"Execution role for AgentCore demo: {agent_name}",
        )
        role_arn = resp["Role"]["Arn"]
        print(f"  ✓ Created IAM role: {role_name}")
    except iam.exceptions.EntityAlreadyExistsException:
        role_arn = f"arn:aws:iam::{account_id}:role/{role_name}"
        print(f"  ✓ IAM role exists: {role_name}")

    iam.put_role_policy(
        RoleName=role_name,
        PolicyName=f"{agent_name}-policy",
        PolicyDocument=json.dumps(inline_policy),
    )

    print("  Waiting 10s for IAM propagation...")
    time.sleep(10)
    return role_arn


def build_and_upload_package(
    agent_name: str,
    region: str,
    account_id: str,
    agent_files: list,
    requirements_file: str = "requirements.txt",
) -> str:
    """Build arm64 deployment package with uv and upload to S3.

    Returns the S3 bucket name.
    """
    s3 = boto3.client("s3", region_name=region)
    bucket = f"agentcore-code-{account_id}-{region}"
    s3_key = f"{agent_name}/code.zip"
    pkg_dir = "deployment_package"
    zip_file = "deployment_package.zip"

    # Create S3 bucket if needed
    try:
        if region == "us-east-1":
            s3.create_bucket(Bucket=bucket)
        else:
            s3.create_bucket(
                Bucket=bucket,
                CreateBucketConfiguration={"LocationConstraint": region},
            )
        print(f"  ✓ Created S3 bucket: {bucket}")
    except (s3.exceptions.BucketAlreadyOwnedByYou, s3.exceptions.BucketAlreadyExists):
        print(f"  ✓ S3 bucket exists: {bucket}")

    # Clean previous build
    if os.path.isdir(pkg_dir):
        shutil.rmtree(pkg_dir)
    if os.path.exists(zip_file):
        os.remove(zip_file)

    # Download arm64 wheels
    print("  Installing arm64 dependencies with uv...")
    subprocess.run(
        [
            "uv", "pip", "install",
            "--python-platform", "aarch64-manylinux2014",
            "--python-version", "3.13",
            "--target", pkg_dir,
            "--only-binary", ":all:",
            "-r", requirements_file,
        ],
        check=True,
        capture_output=True,
    )

    # Create zip
    print("  Creating deployment zip...")
    subprocess.run(
        ["zip", "-r", f"../{zip_file}", "."],
        cwd=pkg_dir,
        check=True,
        capture_output=True,
    )
    for src_file in agent_files:
        subprocess.run(["zip", zip_file, src_file], check=True, capture_output=True)

    zip_size = os.path.getsize(zip_file) / (1024 * 1024)
    print(f"  ✓ Package: {zip_file} ({zip_size:.1f} MB)")

    # Upload
    print(f"  Uploading to s3://{bucket}/{s3_key}...")
    s3.upload_file(zip_file, bucket, s3_key)
    print("  ✓ Uploaded")

    # Clean up local
    shutil.rmtree(pkg_dir)
    os.remove(zip_file)

    return bucket


def create_runtime(
    agent_name: str,
    region: str,
    role_arn: str,
    s3_bucket: str,
    entry_point: str = "agent.py",
    protocol: str = "HTTP",
    python_runtime: str = "PYTHON_3_13",
    lifecycle_config: dict = None,
    description: str = "",
) -> dict:
    """Create an AgentCore Runtime and wait for READY.

    Returns dict with runtime_id and runtime_arn.
    """
    control = boto3.client("bedrock-agentcore-control", region_name=region)
    s3_key = f"{agent_name}/code.zip"

    create_params = dict(
        agentRuntimeName=agent_name,
        agentRuntimeArtifact={
            "codeConfiguration": {
                "code": {"s3": {"bucket": s3_bucket, "prefix": s3_key}},
                "runtime": python_runtime,
                "entryPoint": [entry_point],
            }
        },
        roleArn=role_arn,
        networkConfiguration={"networkMode": "PUBLIC"},
        protocolConfiguration={"serverProtocol": protocol},
        description=description or f"Module 02 demo: {agent_name}",
    )

    if lifecycle_config:
        create_params["lifecycleConfiguration"] = lifecycle_config

    print(f"  Creating AgentCore Runtime '{agent_name}'...")
    response = control.create_agent_runtime(**create_params)
    runtime_id = response["agentRuntimeId"]
    runtime_arn = response["agentRuntimeArn"]
    print(f"  ✓ Runtime created: {runtime_id}")

    # Poll for READY
    print("  Waiting for runtime to be ready...")
    while True:
        status_resp = control.get_agent_runtime(agentRuntimeId=runtime_id)
        status = status_resp["status"]
        print(f"    Status: {status}")
        if status == "READY":
            break
        if status in ("CREATE_FAILED", "UPDATE_FAILED"):
            reason = status_resp.get("failureReason", "Unknown")
            print(f"  ✗ Failed: {reason}")
            sys.exit(1)
        time.sleep(15)

    return {"runtime_id": runtime_id, "runtime_arn": runtime_arn}


def create_endpoint(runtime_id: str, region: str) -> dict:
    """Create a runtime endpoint and wait for READY."""
    control = boto3.client("bedrock-agentcore-control", region_name=region)

    print("  Creating endpoint 'default'...")
    response = control.create_agent_runtime_endpoint(
        agentRuntimeId=runtime_id,
        name="default",
    )
    print(f"  ✓ Endpoint created: {response['agentRuntimeEndpointArn']}")

    # Poll for READY
    print("  Waiting for endpoint to be ready...")
    while True:
        eps = control.list_agent_runtime_endpoints(agentRuntimeId=runtime_id)
        for ep in eps.get("runtimeEndpoints", []):
            if ep["name"] == "default":
                status = ep["status"]
                print(f"    Status: {status}")
                if status == "READY":
                    return ep
                if status in ("CREATE_FAILED", "UPDATE_FAILED"):
                    print("  ✗ Endpoint creation failed")
                    sys.exit(1)
        time.sleep(15)


def save_config(agent_name: str, runtime_id: str, runtime_arn: str, region: str, config_file: str = "runtime_config.json"):
    """Save deployment config for invoke/cleanup scripts."""
    config = {
        "agent_name": agent_name,
        "runtime_id": runtime_id,
        "runtime_arn": runtime_arn,
        "region": region,
    }
    with open(config_file, "w") as f:
        json.dump(config, f, indent=2)
    print(f"  Config saved to: {config_file}")


def cleanup_all(config_file: str = "runtime_config.json"):
    """Delete all resources: endpoints, runtime, S3 artifact, IAM role."""
    try:
        with open(config_file) as f:
            config = json.load(f)
    except FileNotFoundError:
        print(f"Error: {config_file} not found.")
        sys.exit(1)

    agent_name = config["agent_name"]
    runtime_id = config["runtime_id"]
    region = config["region"]

    session = Session(region_name=region)
    account_id = session.client("sts").get_caller_identity()["Account"]
    control = boto3.client("bedrock-agentcore-control", region_name=region)
    iam = boto3.client("iam", region_name=region)
    s3 = boto3.client("s3", region_name=region)

    print(f"Cleaning up: {agent_name}\n")

    # 1. Delete endpoints
    try:
        endpoints = control.list_agent_runtime_endpoints(agentRuntimeId=runtime_id)
        for ep in endpoints.get("runtimeEndpoints", []):
            name = ep["name"]
            if name == "DEFAULT":
                continue
            print(f"  Deleting endpoint: {name}")
            control.delete_agent_runtime_endpoint(agentRuntimeId=runtime_id, endpointName=name)
        if endpoints.get("runtimeEndpoints"):
            print("  Waiting for endpoint deletion...")
            time.sleep(30)
    except Exception as e:
        print(f"  Warning: {e}")

    # 2. Delete runtime
    try:
        print(f"  Deleting runtime: {runtime_id}")
        control.delete_agent_runtime(agentRuntimeId=runtime_id)
        print("  Waiting for runtime deletion...")
        time.sleep(30)
    except Exception as e:
        print(f"  Warning: {e}")

    # 3. Delete S3 artifact
    bucket_name = f"agentcore-code-{account_id}-{region}"
    s3_key = f"{agent_name}/code.zip"
    try:
        s3.delete_object(Bucket=bucket_name, Key=s3_key)
        print(f"  Deleted s3://{bucket_name}/{s3_key}")
    except Exception as e:
        print(f"  Warning: {e}")

    # 4. Delete IAM role
    role_name = f"agentcore-{agent_name}-role"
    try:
        policies = iam.list_role_policies(RoleName=role_name)
        for policy_name in policies.get("PolicyNames", []):
            iam.delete_role_policy(RoleName=role_name, PolicyName=policy_name)
        iam.delete_role(RoleName=role_name)
        print(f"  Deleted IAM role: {role_name}")
    except iam.exceptions.NoSuchEntityException:
        print(f"  IAM role not found: {role_name}")
    except Exception as e:
        print(f"  Warning: {e}")

    # 5. Remove config file
    if os.path.exists(config_file):
        os.remove(config_file)

    print(f"\n✓ Cleanup complete for {agent_name}")
