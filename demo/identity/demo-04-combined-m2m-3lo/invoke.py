"""Demo 4: Invoke combined M2M + 3LO agent."""

import json
import sys
import os
import uuid

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))
from shared.stack_config import get_config
from shared.colors import banner, section, info, config_val, prompt_display, response_display, done, success

import boto3


def get_token(region, pool_id, client_id):
    cognito = boto3.client("cognito-idp", region_name=region)
    resp = cognito.initiate_auth(
        AuthFlow="USER_PASSWORD_AUTH",
        AuthParameters={"USERNAME": "demouser", "PASSWORD": "DemoPass123!"},
        ClientId=client_id,
    )
    return resp["AuthenticationResult"]["AccessToken"]


def main():
    os.chdir(os.path.dirname(os.path.abspath(__file__)))
    with open("runtime_config.json") as f:
        config = json.load(f)
    cfg = get_config()

    banner("Demo 4: Combined M2M + 3LO Invocation")
    config_val("Runtime", config["runtime_arn"])

    # Get Cognito token for inbound auth
    section("Authenticating with Cognito")
    token = get_token(cfg["region"], cfg["cognito_user_pool_id"], cfg["cognito_user_client_id"])
    success(f"Cognito token: {token[:30]}...")

    client = boto3.client("bedrock-agentcore", region_name=config["region"])

    def _inject(request, **_):
        request.headers["Authorization"] = f"Bearer {token}"
    client.meta.events.register("before-send.bedrock-agentcore.InvokeAgentRuntime", _inject)

    # M2M invocation
    section("M2M Flow (auth_flow='M2M')")
    info("Agent authenticates as itself — no user interaction")
    prompt = "Query the internal API for team status."
    prompt_display(prompt)
    response = client.invoke_agent_runtime(
        agentRuntimeArn=config["runtime_arn"],
        qualifier="DEFAULT",
        payload=json.dumps({"prompt": prompt}),
        runtimeSessionId=str(uuid.uuid4()),
    )
    response_display(response["response"].read().decode())

    # 3LO invocation
    section("3LO Flow (auth_flow='USER_FEDERATION')")
    info("Agent acts on behalf of user — may need consent first time")
    prompt = "Show my upcoming calendar events."
    prompt_display(prompt)
    response = client.invoke_agent_runtime(
        agentRuntimeArn=config["runtime_arn"],
        qualifier="DEFAULT",
        payload=json.dumps({"prompt": prompt}),
        runtimeSessionId=str(uuid.uuid4()),
    )
    response_display(response["response"].read().decode(), max_len=500)
    info("If consent URL returned: click to authorize, then re-invoke")

    done()
    print()


if __name__ == "__main__":
    main()
