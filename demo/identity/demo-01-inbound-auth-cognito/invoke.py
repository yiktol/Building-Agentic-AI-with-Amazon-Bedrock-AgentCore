"""
Demo 1: Test inbound auth — invoke WITHOUT and WITH Cognito JWT.

Shows:
  1. Unauthenticated request → AccessDeniedException
  2. Obtain Cognito access token
  3. Authenticated request → agent responds

Usage:
    python invoke.py
"""

import json
import sys
import os
import uuid

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))
from shared.colors import banner, section, success, info, error, config_val, prompt_display, response_display, done

import boto3


def load_config() -> dict:
    os.chdir(os.path.dirname(os.path.abspath(__file__)))
    with open("runtime_config.json") as f:
        return json.load(f)


def get_cognito_token(region: str, pool_id: str, client_id: str) -> str:
    """Authenticate test user and return access token."""
    cognito = boto3.client("cognito-idp", region_name=region)
    resp = cognito.initiate_auth(
        AuthFlow="USER_PASSWORD_AUTH",
        AuthParameters={"USERNAME": "demouser", "PASSWORD": "DemoPass123!"},
        ClientId=client_id,
    )
    return resp["AuthenticationResult"]["AccessToken"]


def invoke_runtime(runtime_arn: str, prompt: str, region: str, bearer_token: str = None) -> str:
    """Invoke runtime with optional bearer token."""
    client = boto3.client("bedrock-agentcore", region_name=region)

    if bearer_token:
        def _inject(request, **_):
            request.headers["Authorization"] = f"Bearer {bearer_token}"
        client.meta.events.register("before-send.bedrock-agentcore.InvokeAgentRuntime", _inject)

    response = client.invoke_agent_runtime(
        agentRuntimeArn=runtime_arn,
        qualifier="DEFAULT",
        payload=json.dumps({"prompt": prompt}),
        runtimeSessionId=str(uuid.uuid4()),
    )
    return response["response"].read().decode("utf-8")


def main():
    config = load_config()
    arn = config["runtime_arn"]
    region = config["region"]

    banner("Demo 1: Testing Inbound Auth")
    config_val("Runtime", arn)

    # Test A: No auth
    section("Test A: Invoke WITHOUT authorization")
    info("Expected: AccessDeniedException (runtime rejects unauthenticated requests)")
    try:
        result = invoke_runtime(arn, "What is 2+2?", region)
        error(f"Unexpected success: {result[:100]}")
    except Exception as e:
        success(f"Got expected error: {type(e).__name__}")
        info(str(e)[:200])

    # Test B: Get token
    section("Test B: Obtain Cognito access token")
    info("Authenticating: demouser / DemoPass123!")
    token = get_cognito_token(region, config["cognito_user_pool_id"], config["cognito_user_client_id"])
    success(f"Token obtained: {token[:40]}...")

    # Test C: With auth
    section("Test C: Invoke WITH authorization")
    info("Sending: Authorization: Bearer <jwt>")
    prompt = "What is the weather in Seattle?"
    prompt_display(prompt)
    result = invoke_runtime(arn, prompt, region, bearer_token=token)
    response_display(result)
    success("Authenticated invocation succeeded!")

    done()
    info("Key: customJWTAuthorizer protects the endpoint")
    info("Agent code has zero auth logic — separation of concerns")
    print()


if __name__ == "__main__":
    main()
