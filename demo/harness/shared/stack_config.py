"""Reads CloudFormation stack outputs for harness demos."""

import os
import sys

import boto3
from boto3.session import Session

STACK_NAME = os.environ.get("STACK_NAME", "mlagac-m07-demo-prereqs")


def get_stack_outputs(region=None):
    """Read all outputs from the prerequisite CloudFormation stack."""
    session = Session()
    region = (
        region
        or os.environ.get("AWS_REGION")
        or os.environ.get("AWS_DEFAULT_REGION")
        or session.region_name
        or "ap-southeast-1"
    )
    cfn = boto3.client("cloudformation", region_name=region)
    try:
        resp = cfn.describe_stacks(StackName=STACK_NAME)
    except Exception as e:
        print(f"\n  ERROR: Could not read stack '{STACK_NAME}' in {region}")
        print(f"  Deploy first: cd cloudformation && ./deploy-stack.sh")
        sys.exit(1)
    outputs = {}
    for out in resp["Stacks"][0].get("Outputs", []):
        outputs[out["OutputKey"]] = out["OutputValue"]
    return outputs


def get_config(region=None):
    """Return config dict with region, account_id, and harness_role_arn."""
    session = Session()
    region = (
        region
        or os.environ.get("AWS_REGION")
        or os.environ.get("AWS_DEFAULT_REGION")
        or session.region_name
        or "ap-southeast-1"
    )
    account_id = session.client("sts").get_caller_identity()["Account"]
    outputs = get_stack_outputs(region)
    return {
        "region": region,
        "account_id": account_id,
        "harness_role_arn": outputs["HarnessExecutionRoleArn"],
    }
