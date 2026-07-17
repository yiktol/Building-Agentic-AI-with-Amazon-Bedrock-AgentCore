"""Demo 2: Invoke the agent that uses @requires_api_key."""

import json
import sys
import os

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))
from shared.colors import banner, section, success, info, config_val, prompt_display, response_display, done

import boto3


def main():
    os.chdir(os.path.dirname(os.path.abspath(__file__)))
    with open("runtime_config.json") as f:
        config = json.load(f)

    banner("Demo 2: Invoking Agent with API Key Outbound Auth")
    config_val("Runtime", config["runtime_arn"])
    config_val("Provider", config["provider_name"])

    client = boto3.client("bedrock-agentcore", region_name=config["region"])

    prompts = ["Look up the latest AI news for me."]

    for prompt in prompts:
        section("Invocation")
        info("Agent will call @requires_api_key → retrieve key from vault")
        prompt_display(prompt)
        response = client.invoke_agent_runtime(
            agentRuntimeArn=config["runtime_arn"],
            payload=json.dumps({"prompt": prompt}).encode(),
            contentType="application/json", accept="application/json",
        )
        body = response["response"].read().decode()
        response_display(body)
        success("Key retrieved from vault → API called (key never in LLM context)")

    done()
    print()


if __name__ == "__main__":
    main()
