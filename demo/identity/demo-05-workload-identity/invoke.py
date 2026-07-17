"""Demo 5: Invoke the deployed agent (standard invocation)."""

import json
import sys
import os

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))
from shared.colors import banner, section, config_val, prompt_display, response_display, done

import boto3


def main():
    os.chdir(os.path.dirname(os.path.abspath(__file__)))
    with open("runtime_config.json") as f:
        config = json.load(f)

    banner("Demo 5: Workload Identity — Invoke")
    config_val("Runtime", config["runtime_arn"])

    client = boto3.client("bedrock-agentcore", region_name=config["region"])
    section("Invocation")
    prompt = "What's the weather in Seattle?"
    prompt_display(prompt)
    response = client.invoke_agent_runtime(
        agentRuntimeArn=config["runtime_arn"],
        payload=json.dumps({"prompt": prompt}).encode(),
        contentType="application/json", accept="application/json",
    )
    response_display(response["response"].read().decode())

    done()
    print()


if __name__ == "__main__":
    main()
