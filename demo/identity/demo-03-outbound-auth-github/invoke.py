"""Demo 3: Invoke GitHub agent (shows consent flow on first call)."""

import json
import sys
import os

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))
from shared.colors import banner, section, info, config_val, prompt_display, response_display, done

import boto3


def main():
    os.chdir(os.path.dirname(os.path.abspath(__file__)))
    with open("runtime_config.json") as f:
        config = json.load(f)

    banner("Demo 3: GitHub 3LO — User Delegation")
    config_val("Runtime", config["runtime_arn"])
    info("First call may return a consent URL — user must click to grant access")

    client = boto3.client("bedrock-agentcore", region_name=config["region"])

    section("Invocation")
    prompt = "List my private GitHub repositories."
    prompt_display(prompt)
    response = client.invoke_agent_runtime(
        agentRuntimeArn=config["runtime_arn"],
        payload=json.dumps({"prompt": prompt}).encode(),
        contentType="application/json", accept="application/json",
    )
    body = response["response"].read().decode()
    response_display(body, max_len=500)
    info("If consent URL returned: click it → authorize → re-invoke")

    done()
    print()


if __name__ == "__main__":
    main()
