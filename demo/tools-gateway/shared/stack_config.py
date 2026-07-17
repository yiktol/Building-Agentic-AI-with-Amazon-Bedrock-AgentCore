"""Reads CloudFormation stack outputs for tools-gateway demos."""

import os
import sys

import boto3
from boto3.session import Session

STACK_NAME = os.environ.get("STACK_NAME", "mlagac-m04-tools-gateway-prereqs")


def get_stack_outputs(region: str = None) -> dict:
    session = Session()
    region = region or session.region_name or "ap-southeast-1"
    cfn = boto3.client("cloudformation", region_name=region)
    try:
        resp = cfn.describe_stacks(StackName=STACK_NAME)
    except Exception as e:
        print(f"\n  ERROR: Stack '{STACK_NAME}' not found in {region}")
        print(f"  Deploy first: cd cloudformation && ./deploy-stack.sh {region}")
        sys.exit(1)
    return {o["OutputKey"]: o["OutputValue"] for o in resp["Stacks"][0].get("Outputs", [])}


def get_config(region: str = None) -> dict:
    session = Session()
    region = region or session.region_name or "ap-southeast-1"
    account_id = session.client("sts").get_caller_identity()["Account"]
    outputs = get_stack_outputs(region)
    return {
        "region": region,
        "account_id": account_id,
        "s3_bucket": outputs["BucketName"],
        "runtime_role_arn": outputs["RuntimeRoleArn"],
        "lambda_role_arn": outputs["LambdaRoleArn"],
        "order_service_arn": outputs["OrderServiceArn"],
        "weather_service_arn": outputs["WeatherServiceArn"],
        "calculator_service_arn": outputs["CalculatorServiceArn"],
    }
