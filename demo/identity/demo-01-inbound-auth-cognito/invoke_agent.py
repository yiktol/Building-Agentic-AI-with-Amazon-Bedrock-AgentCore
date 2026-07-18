"""
Demo 1: Interactive Authenticated Chat Client — Inbound Auth with Cognito.

Chat client that authenticates with Cognito JWT before each invocation.
Demonstrates the full inbound auth flow in a conversational loop.

Same session maintained → agent remembers context across turns.

Usage:
    python invoke_agent.py                          # Interactive chatbot
    python invoke_agent.py "What is 2 + 2?"         # Single prompt
"""

import json
import os
import re
import sys
import uuid

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))
from shared.colors import (
    banner, section, success, info, config_val, done,
    prompt_display, response_display, GREEN, YELLOW, RED, RESET, BOLD, WHITE, DIM
)

import boto3


def get_cognito_token(region, pool_id, client_id):
    """Authenticate test user and return access token."""
    cognito = boto3.client("cognito-idp", region_name=region)
    resp = cognito.initiate_auth(
        AuthFlow="USER_PASSWORD_AUTH",
        AuthParameters={"USERNAME": "demouser", "PASSWORD": "DemoPass123!"},
        ClientId=client_id,
    )
    return resp["AuthenticationResult"]["AccessToken"]


def parse_sse_response(raw: str) -> str:
    """Parse SSE streaming response into clean text."""
    parts = []
    for line in raw.splitlines():
        if line.startswith("data: "):
            chunk = line[len("data: "):]
            if chunk.startswith('"') and chunk.endswith('"'):
                chunk = chunk[1:-1]
            parts.append(chunk)
    text = "".join(parts) if parts else raw
    text = re.sub(r"<thinking>.*?</thinking>\s*", "", text, flags=re.DOTALL).strip()
    return text


def invoke_with_auth(runtime_arn, prompt, region, session_id, bearer_token):
    """Invoke the agent with JWT bearer token in Authorization header."""
    client = boto3.client("bedrock-agentcore", region_name=region)

    def _inject(request, **_):
        request.headers["Authorization"] = f"Bearer {bearer_token}"

    client.meta.events.register(
        "before-send.bedrock-agentcore.InvokeAgentRuntime", _inject
    )

    resp = client.invoke_agent_runtime(
        agentRuntimeArn=runtime_arn,
        qualifier="DEFAULT",
        payload=json.dumps({"prompt": prompt}).encode("utf-8"),
        runtimeSessionId=session_id,
    )
    return parse_sse_response(resp["response"].read().decode("utf-8"))


def run_chatbot(runtime_arn, region, session_id, bearer_token):
    """Interactive authenticated conversation loop."""
    print(f"\n{BOLD}{WHITE}  Authenticated Agent Chat{RESET}")
    print(f"  Every request includes: Authorization: Bearer <Cognito JWT>")
    print(f"  Agent code has ZERO auth logic — separation of concerns.")
    print(f"  Type 'quit' to stop.\n")

    while True:
        try:
            user_input = input(f"  {GREEN}You:{RESET} ")
        except (EOFError, KeyboardInterrupt):
            print()
            break

        if user_input.strip().lower() in ("quit", "exit", "q"):
            break
        if not user_input.strip():
            continue

        try:
            response = invoke_with_auth(
                runtime_arn, user_input, region, session_id, bearer_token
            )
            print(f"  {YELLOW}Agent:{RESET} {response}\n")
        except Exception as e:
            err = str(e)
            if "AccessDenied" in err:
                print(f"  {RED}Auth Error:{RESET} Token may have expired. Restart to re-authenticate.\n")
            else:
                print(f"  {RED}Error:{RESET} {err[:200]}\n")


def main():
    os.chdir(os.path.dirname(os.path.abspath(__file__)))

    if not os.path.exists("runtime_config.json"):
        from shared.colors import error
        error("runtime_config.json not found. Run deploy.py first.")
        sys.exit(1)

    with open("runtime_config.json") as f:
        config = json.load(f)

    runtime_arn = config["runtime_arn"]
    region = config["region"]
    pool_id = config["cognito_user_pool_id"]
    client_id = config["cognito_user_client_id"]
    session_id = str(uuid.uuid4())

    banner("Demo 1: Authenticated Agent Chat")
    config_val("Runtime ARN", runtime_arn)
    config_val("Session", session_id)

    # Authenticate with Cognito
    info("Authenticating: demouser / DemoPass123!")
    token = get_cognito_token(region, pool_id, client_id)
    success(f"JWT obtained: {token[:30]}...")
    info(f"{DIM}All requests will include: Authorization: Bearer <jwt>{RESET}")

    if len(sys.argv) > 1:
        prompt = " ".join(sys.argv[1:])
        section("Single prompt mode")
        prompt_display(prompt)
        response = invoke_with_auth(runtime_arn, prompt, region, session_id, token)
        response_display(response)
    else:
        run_chatbot(runtime_arn, region, session_id, token)

    done()
    info("Key: customJWTAuthorizer validates token at the Runtime level")
    info("Agent code has zero auth logic — separation of concerns")
    print()


if __name__ == "__main__":
    main()
