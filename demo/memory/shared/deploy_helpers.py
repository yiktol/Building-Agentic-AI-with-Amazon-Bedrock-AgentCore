"""
Shared deployment helpers for Module 05 Memory demos.

Provides reusable functions for:
- IAM role creation with AgentCore + Memory trust policies
- Memory resource creation and polling
- arm64 deployment package building with uv
- S3 upload
- AgentCore Runtime creation and polling
- Endpoint creation and polling
- Cleanup (tear down all resources)

Usage:
    from shared.deploy_helpers import (
        get_aws_context,
        create_execution_role,
        create_memory_resource,
        build_and_upload_package,
        create_runtime,
        create_endpoint,
        save_config,
        cleanup_all,
    )
"""

import json
import os
import shutil
import subprocess
import sys
import time
import uuid

import boto3
from boto3.session import Session


def get_aws_context():
    """Get region and account ID from the current AWS session."""
    session = Session()
    region = os.environ.get("AWS_REGION") or session.region_name or "ap-southeast-1"
    account_id = session.client("sts").get_caller_identity()["Account"]
    return region, account_id


def create_execution_role(agent_name: str, region: str, account_id: str) -> str:
    """Create IAM execution role with AgentCore + Memory permissions.

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
            {
                "Sid": "AgentCoreMemoryDataPlane",
                "Effect": "Allow",
                "Action": [
                    "bedrock-agentcore:CreateEvent",
                    "bedrock-agentcore:GetEvent",
                    "bedrock-agentcore:ListEvents",
                    "bedrock-agentcore:ListSessions",
                    "bedrock-agentcore:RetrieveMemoryRecords",
                    "bedrock-agentcore:ListMemoryRecords",
                    "bedrock-agentcore:GetMemoryRecord",
                ],
                "Resource": [f"arn:aws:bedrock-agentcore:{region}:{account_id}:memory/*"],
            },
            {
                "Sid": "AgentCoreMemoryControlPlane",
                "Effect": "Allow",
                "Action": [
                    "bedrock-agentcore:CreateMemory",
                    "bedrock-agentcore:GetMemory",
                    "bedrock-agentcore:UpdateMemory",
                    "bedrock-agentcore:DeleteMemory",
                    "bedrock-agentcore:ListMemories",
                ],
                "Resource": ["*"],
            },
        ],
    }

    try:
        resp = iam.create_role(
            RoleName=role_name,
            AssumeRolePolicyDocument=json.dumps(trust_policy),
            Description=f"Execution role for AgentCore Memory demo: {agent_name}",
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


def create_memory_execution_role(agent_name: str, region: str, account_id: str) -> str:
    """Create IAM role for AgentCore Memory service to assume (extraction).

    This role lets the Memory service invoke Bedrock models for built-in
    strategy extraction. Returns the role ARN.
    """
    iam = boto3.client("iam", region_name=region)
    role_name = f"agentcore-memory-exec-{agent_name}-role"

    trust_policy = {
        "Version": "2012-10-17",
        "Statement": [
            {
                "Effect": "Allow",
                "Principal": {"Service": "bedrock-agentcore.amazonaws.com"},
                "Action": "sts:AssumeRole",
            }
        ],
    }

    inline_policy = {
        "Version": "2012-10-17",
        "Statement": [
            {
                "Effect": "Allow",
                "Action": [
                    "bedrock:InvokeModel",
                    "bedrock:InvokeModelWithResponseStream",
                ],
                "Resource": "*",
            }
        ],
    }

    try:
        resp = iam.create_role(
            RoleName=role_name,
            AssumeRolePolicyDocument=json.dumps(trust_policy),
            Description=f"Memory execution role for extraction: {agent_name}",
        )
        role_arn = resp["Role"]["Arn"]
        print(f"  ✓ Created memory execution role: {role_name}")
    except iam.exceptions.EntityAlreadyExistsException:
        role_arn = f"arn:aws:iam::{account_id}:role/{role_name}"
        print(f"  ✓ Memory execution role exists: {role_name}")

    iam.put_role_policy(
        RoleName=role_name,
        PolicyName=f"{agent_name}-bedrock-access",
        PolicyDocument=json.dumps(inline_policy),
    )

    time.sleep(5)
    return role_arn


def create_memory_resource(
    name: str,
    region: str,
    memory_execution_role_arn: str,
    strategies: list = None,
    event_expiry_days: int = 7,
    description: str = "",
) -> dict:
    """Create an AgentCore Memory resource and wait for ACTIVE.

    Returns dict with memory_id and memory status.
    """
    control = boto3.client("bedrock-agentcore-control", region_name=region)

    create_params = dict(
        name=name,
        description=description or f"Module 05 demo memory: {name}",
        eventExpiryDuration=event_expiry_days,
        memoryExecutionRoleArn=memory_execution_role_arn,
        clientToken=str(uuid.uuid4()),
    )
    if strategies:
        create_params["memoryStrategies"] = strategies

    print(f"  Creating memory resource '{name}'...")
    resp = control.create_memory(**create_params)
    memory_id = resp["memory"]["id"]
    print(f"  ✓ Memory created: {memory_id}")

    # Poll for ACTIVE
    print("  Waiting for memory to be ACTIVE...")
    deadline = time.time() + 300
    while time.time() < deadline:
        status = control.get_memory(memoryId=memory_id)["memory"]["status"]
        if status == "ACTIVE":
            print(f"  ✓ Memory ACTIVE: {memory_id}")
            return {"memory_id": memory_id, "status": status}
        if status == "FAILED":
            print(f"  ✗ Memory creation FAILED")
            sys.exit(1)
        time.sleep(5)

    print("  ✗ Timed out waiting for memory to become ACTIVE")
    sys.exit(1)


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
                "runtime": "PYTHON_3_13",
                "entryPoint": [entry_point],
            }
        },
        roleArn=role_arn,
        networkConfiguration={"networkMode": "PUBLIC"},
        protocolConfiguration={"serverProtocol": "HTTP"},
        description=description or f"Module 05 Memory demo: {agent_name}",
    )

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


def cleanup_all(config_file: str = "runtime_config.json"):
    """Delete all resources: memory, endpoints, runtime, S3 artifact, IAM roles."""
    config = load_config(config_file)

    agent_name = config["agent_name"]
    region = config["region"]

    session = Session(region_name=region)
    account_id = session.client("sts").get_caller_identity()["Account"]
    control = boto3.client("bedrock-agentcore-control", region_name=region)
    iam = boto3.client("iam", region_name=region)
    s3 = boto3.client("s3", region_name=region)

    print(f"Cleaning up: {agent_name}\n")

    # 1. Delete memory resource
    memory_id = config.get("memory_id")
    if memory_id:
        try:
            print(f"  Deleting memory: {memory_id}")
            control.delete_memory(memoryId=memory_id, clientToken=str(uuid.uuid4()))
            print("  Waiting for memory deletion...")
            time.sleep(15)
        except Exception as e:
            print(f"  Warning: {e}")

    # 2. Delete endpoints
    runtime_id = config.get("runtime_id")
    if runtime_id:
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

        # 3. Delete runtime
        try:
            print(f"  Deleting runtime: {runtime_id}")
            control.delete_agent_runtime(agentRuntimeId=runtime_id)
            print("  Waiting for runtime deletion...")
            time.sleep(30)
        except Exception as e:
            print(f"  Warning: {e}")

    # 4. Delete S3 artifact
    bucket_name = f"agentcore-code-{account_id}-{region}"
    s3_key = f"{agent_name}/code.zip"
    try:
        s3.delete_object(Bucket=bucket_name, Key=s3_key)
        print(f"  Deleted s3://{bucket_name}/{s3_key}")
    except Exception as e:
        print(f"  Warning: {e}")

    # 5. Delete IAM roles
    for role_name in [f"agentcore-{agent_name}-role", f"agentcore-memory-exec-{agent_name}-role"]:
        try:
            policies = iam.list_role_policies(RoleName=role_name)
            for policy_name in policies.get("PolicyNames", []):
                iam.delete_role_policy(RoleName=role_name, PolicyName=policy_name)
            iam.delete_role(RoleName=role_name)
            print(f"  Deleted IAM role: {role_name}")
        except iam.exceptions.NoSuchEntityException:
            pass
        except Exception as e:
            print(f"  Warning: {e}")

    # 6. Remove config file
    if os.path.exists(config_file):
        os.remove(config_file)

    print(f"\n✓ Cleanup complete for {agent_name}")
