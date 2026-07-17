"""
Reads CloudFormation stack outputs for observability demos.

All base AWS resources (S3, IAM roles) are provisioned via the CloudFormation template.
This module retrieves the outputs.
"""

import os
import sys

import boto3
from boto3.session import Session

STACK_NAME = os.environ.get("STACK_NAME", "mlagac-m06-demo-prereqs")


def get_stack_outputs(region: str = None) -> dict:
    """Retrieve all outputs from the observability prerequisites stack."""
    session = Session()
    region = region or os.environ.get("AWS_REGION") or session.region_name or "ap-southeast-1"
    cfn = boto3.client("cloudformation", region_name=region)

    try:
        resp = cfn.describe_stacks(StackName=STACK_NAME)
    except Exception as e:
        print(f"\n  ERROR: Could not read stack '{STACK_NAME}' in {region}")
        print(f"  {e}")
        print(f"\n  Deploy prerequisites first:")
        print(f"    cd cloudformation && ./deploy-stack.sh {region}")
        sys.exit(1)

    outputs = {}
    for out in resp["Stacks"][0].get("Outputs", []):
        outputs[out["OutputKey"]] = out["OutputValue"]
    return outputs


def get_config(region: str = None) -> dict:
    """Get full config dict from stack outputs."""
    session = Session()
    region = region or os.environ.get("AWS_REGION") or session.region_name or "ap-southeast-1"
    account_id = session.client("sts").get_caller_identity()["Account"]
    outputs = get_stack_outputs(region)

    return {
        "region": region,
        "account_id": account_id,
        "s3_bucket": outputs["CodeBucketName"],
        "runtime_role_arn": outputs["RuntimeExecutionRoleArn"],
        "eval_role_arn": outputs["EvaluationExecutionRoleArn"],
    }
