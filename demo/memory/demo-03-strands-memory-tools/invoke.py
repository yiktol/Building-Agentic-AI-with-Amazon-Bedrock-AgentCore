"""
Demo 3: Invoke Strands agent with memory-as-tool.

Shows:
  1. Tell the agent user preferences (agent decides to save)
  2. Ask about preferences (agent decides to recall)
  3. Demonstrate the LLM deciding when to use memory tools

Usage:
    python invoke.py
    python invoke.py "Do you remember my preferences?"
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
            "I'm vegetarian and I love Italian cuisine.",
            "I prefer morning meetings and I work remotely from Portland.",
            "Do you remember my food preferences?",
            "What do you know about my work setup?",
        ]

    banner("Demo 3: Strands Agent — Memory as Tool")
    config_val("Runtime", runtime_arn)
    config_val("Memory", config["memory_id"])
    info("The agent decides when to save/recall via tool calls")

    for i, prompt in enumerate(prompts, 1):
        section(f"Prompt {i}/{len(prompts)}")
        prompt_display(prompt)
        response = invoke(runtime_arn, prompt, region)
        response_display(response)

    done()
    info("Key: Agent explicitly calls memory tools — deliberate save/recall")
    info("Pattern: AgentCoreMemoryToolProvider gives agent read/write tools")
    print()


if __name__ == "__main__":
    main()
