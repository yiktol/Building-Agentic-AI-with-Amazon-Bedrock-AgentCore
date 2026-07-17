"""
Demo 1: Invoke the Strands + Bedrock agent on AgentCore Runtime.

Sends sample prompts that exercise:
- Weather tool
- Calculator tool
- General conversation

Usage:
    python invoke.py
    python invoke.py "What is 25 * 17?"
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
    """Send a prompt to the deployed agent."""
    client = boto3.client("bedrock-agentcore", region_name=region)

    response = client.invoke_agent_runtime(
        agentRuntimeArn=runtime_arn,
        payload=json.dumps({"prompt": prompt}).encode("utf-8"),
        contentType="application/json",
        accept="application/json",
    )

    body = response["response"].read().decode("utf-8")
    session_id = response.get("runtimeSessionId", "N/A")
    info(f"Session: {session_id}")
    return body


def main():
    config = load_config()
    runtime_arn = config["runtime_arn"]
    region = config["region"]

    if len(sys.argv) > 1:
        prompts = [" ".join(sys.argv[1:])]
    else:
        prompts = [
            "What is the weather in Seattle?",
            "Calculate 25 * 17 + 42",
            "Compare the weather in Miami and New York",
        ]

    banner("Demo 1: Invoking Strands + Bedrock Agent")
    config_val("Runtime", runtime_arn)

    for i, prompt in enumerate(prompts, 1):
        section(f"Prompt {i}/{len(prompts)}")
        prompt_display(prompt)
        response = invoke(runtime_arn, prompt, region)
        response_display(response)

    done()


if __name__ == "__main__":
    main()
