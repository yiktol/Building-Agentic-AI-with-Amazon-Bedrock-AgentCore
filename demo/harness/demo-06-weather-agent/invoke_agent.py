"""
Demo 6: Weather Agent — Interactive Chatbot.

Full-featured chatbot combining Harness + Gateway + Guardrails.
Ask weather questions and see real-time tool calls via the Exa MCP target.

Commands:
  quit/exit — stop the chatbot
  exec <cmd> — run a shell command on the agent's microVM

Usage:
    python invoke_agent.py
"""

import json
import os
import sys
import uuid

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))
from shared.harness_helpers import execute_command, load_config
from shared.colors import (
    banner, section, success, info, config_val, done,
    GREEN, YELLOW, RED, RESET, BOLD, WHITE, DIM
)

import boto3


def main():
    os.chdir(os.path.dirname(os.path.abspath(__file__)))
    config = load_config()
    harness_arn = config["harness_arn"]
    gateway_arn = config["gateway_arn"]
    region = config["region"]

    client = boto3.client("bedrock-agentcore", region_name=region)
    session_id = str(uuid.uuid4()).upper()
    model_id = "global.anthropic.claude-haiku-4-5-20251001-v1:0"
    tools = [{"type": "agentcore_gateway", "name": "gateway", "config": {"agentCoreGateway": {"gatewayArn": gateway_arn}}}]

    banner("Demo 6: Weather Agent (Interactive)")
    config_val("Harness", config["harness_id"])
    config_val("Session", session_id)
    info("Features: Harness + Gateway + Guardrails + Observability")

    print(f"\n{BOLD}{WHITE}  Weather Agent Chat{RESET}")
    print(f"  Ask about weather anywhere. Agent uses real-time web search.")
    print(f"  Commands: 'exec <cmd>' for shell, 'quit' to exit.\n")

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

        # Handle exec command
        if user_input.strip().startswith("exec "):
            cmd = user_input.strip()[5:]
            print(f"  {DIM}$ {cmd}{RESET}")
            stdout, stderr, exit_code = execute_command(harness_arn, session_id, cmd, region)
            if stdout:
                print(f"  {stdout.rstrip()}")
            if stderr:
                print(f"  {RED}{stderr.rstrip()}{RESET}")
            print(f"  {DIM}[exit: {exit_code}]{RESET}\n")
            continue

        # Invoke harness
        print(f"  {YELLOW}Agent:{RESET} ", end="")
        try:
            response = client.invoke_harness(
                harnessArn=harness_arn,
                runtimeSessionId=session_id,
                messages=[{"role": "user", "content": [{"text": user_input}]}],
                model={"bedrockModelConfig": {"modelId": model_id}},
                tools=tools,
            )

            for event in response["stream"]:
                if "contentBlockStart" in event:
                    start = event["contentBlockStart"].get("start", {})
                    if "toolUse" in start:
                        print(f"\n    {DIM}🔧 {start['toolUse'].get('name', '?')}{RESET}", end="")
                elif "contentBlockDelta" in event:
                    delta = event["contentBlockDelta"].get("delta", {})
                    if "text" in delta:
                        print(delta["text"], end="", flush=True)
                elif "messageStop" in event:
                    print("\n")
        except Exception as e:
            print(f"\n  {RED}Error:{RESET} {str(e)[:200]}\n")

    done()


if __name__ == "__main__":
    main()
