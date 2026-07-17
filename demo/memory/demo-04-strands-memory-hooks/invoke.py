"""
Demo 4: Invoke Strands agent with memory hooks.

Shows:
  1. Conversation is automatically saved (no explicit tool calls)
  2. Context is auto-retrieved on new messages
  3. Compare with Demo 3: hooks are transparent to the LLM

Usage:
    python invoke.py
    python invoke.py "What do you remember about me?"
"""

import json
import os
import sys

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))
from shared.deploy_helpers import load_config
from shared.colors import banner, section, success, info, config_val, prompt_display, response_display, done

import boto3


def invoke(runtime_arn: str, prompt: str, region: str, session_id: str = None) -> str:
    """Send a prompt to the deployed agent."""
    client = boto3.client("bedrock-agentcore", region_name=region)
    params = dict(
        agentRuntimeArn=runtime_arn,
        payload=json.dumps({"prompt": prompt}).encode("utf-8"),
        contentType="application/json",
        accept="application/json",
    )
    if session_id:
        params["runtimeSessionId"] = session_id

    response = client.invoke_agent_runtime(**params)
    return response["response"].read().decode("utf-8")


def main():
    os.chdir(os.path.dirname(os.path.abspath(__file__)))
    config = load_config()
    runtime_arn = config["runtime_arn"]
    region = config["region"]

    if len(sys.argv) > 1:
        prompts = [" ".join(sys.argv[1:])]
    else:
        prompts = [
            "Hi, I'm Alex. I'm a vegetarian who lives in Portland.",
            "I work as a data scientist and prefer Python.",
            "What do you remember about me?",
        ]

    banner("Demo 4: Strands Agent — Memory Hooks (Automatic)")
    config_val("Runtime", runtime_arn)
    config_val("Memory", config["memory_id"])
    info("Hooks auto-save each turn and auto-retrieve on new messages")

    for i, prompt in enumerate(prompts, 1):
        section(f"Prompt {i}/{len(prompts)}")
        prompt_display(prompt)
        response = invoke(runtime_arn, prompt, region)
        response_display(response)

    done()
    info("Key: Hooks fire transparently — agent doesn't 'see' memory operations")
    info("Compare with Demo 3: tool pattern = agent decides; hook pattern = automatic")
    print()


if __name__ == "__main__":
    main()
