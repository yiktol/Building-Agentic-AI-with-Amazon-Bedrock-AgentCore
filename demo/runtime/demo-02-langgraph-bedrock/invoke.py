"""
Demo 2: Invoke the LangGraph + Bedrock agent.

Same invocation pattern as Demo 1 — proving framework agnosticism.

Usage:
    python invoke.py
    python invoke.py "What is sqrt(144) + 8?"
"""

import json
import sys
import os

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))
from shared.colors import banner, section, success, info, config_val, prompt_display, response_display, done

import boto3


def load_config() -> dict:
    os.chdir(os.path.dirname(os.path.abspath(__file__)))
    try:
        with open("runtime_config.json") as f:
            return json.load(f)
    except FileNotFoundError:
        from shared.colors import error
        error("runtime_config.json not found. Run deploy.py first.")
        sys.exit(1)


def invoke(runtime_arn: str, prompt: str, region: str) -> str:
    client = boto3.client("bedrock-agentcore", region_name=region)
    response = client.invoke_agent_runtime(
        agentRuntimeArn=runtime_arn,
        payload=json.dumps({"prompt": prompt}).encode("utf-8"),
        contentType="application/json",
        accept="application/json",
    )
    return response["response"].read().decode("utf-8")


def main():
    config = load_config()

    if len(sys.argv) > 1:
        prompts = [" ".join(sys.argv[1:])]
    else:
        prompts = [
            "What is 25 * 17 + 42?",
            "Calculate sqrt(144) + log10(1000)",
            "What's the weather in Seattle?",
        ]

    banner("Demo 2: Invoking LangGraph + Bedrock Agent")
    config_val("Runtime", config["runtime_arn"])
    info("Same invoke_agent_runtime() API as Demo 1")

    for i, prompt in enumerate(prompts, 1):
        section(f"Prompt {i}/{len(prompts)}")
        prompt_display(prompt)
        response = invoke(config["runtime_arn"], prompt, config["region"])
        response_display(response)

    done()


if __name__ == "__main__":
    main()
