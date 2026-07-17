"""
Reads CloudFormation stack outputs for identity demos.

All AWS resources are provisioned via the CloudFormation template.
This module retrieves the outputs (bucket name, role ARN, Cognito IDs).
"""

import json
import os
import subprocess
import sys

import boto3
from boto3.session import Session

STACK_NAME = os.environ.get("STACK_NAME", "mlagac-m03-identity-prereqs")


def get_stack_outputs(region: str = None) -> dict:
    """Retrieve all outputs from the identity prerequisites stack.

    Returns a dict mapping OutputKey -> OutputValue.
    """
    session = Session()
    region = region or session.region_name or "us-east-1"
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
    region = region or session.region_name or "us-east-1"
    account_id = session.client("sts").get_caller_identity()["Account"]
    outputs = get_stack_outputs(region)

    return {
        "region": region,
        "account_id": account_id,
        "s3_bucket": outputs["BucketName"],
        "role_arn": outputs["ExecutionRoleArn"],
        "cognito_user_pool_id": outputs["CognitoUserPoolId"],
        "cognito_user_client_id": outputs["CognitoUserClientId"],
        "cognito_machine_client_id": outputs["CognitoMachineClientId"],
        "cognito_discovery_url": outputs["CognitoDiscoveryUrl"],
        "cognito_token_endpoint": outputs["CognitoTokenEndpoint"],
    }
