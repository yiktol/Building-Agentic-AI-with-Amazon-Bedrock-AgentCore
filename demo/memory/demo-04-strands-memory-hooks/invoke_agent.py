"""
Demo 4: Interactive Agent with Memory Hooks — Chatbot.

Talks to the deployed hooks-based memory agent, demonstrating that memory
persists automatically without explicit tool calls. The agent hooks fire:
  - MessageAdded → retrieves relevant memories
  - AfterInvocation → saves new information to memory

Memory is transparent — the agent doesn't need to "remember" explicitly.
Just have a conversation and it automatically builds context over time.

Usage:
    python invoke_agent.py                      # Interactive chatbot
    python invoke_agent.py "My name is Alice"   # Single prompt
"""

import json
import os
import re
import sys
import uuid

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))
from shared.colors import (
    banner, section, success, info, config_val, done,
    prompt_display, response_display, GREEN, YELLOW, RED, RESET, BOLD, WHITE
)

import boto3


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
    # Strip thinking tags
    text = re.sub(r"<thinking>.*?</thinking>\s*", "", text, flags=re.DOTALL).strip()
    return text


def invoke(runtime_arn, prompt, region, session_id=None):
    """Send a prompt to the deployed hooks-based memory agent."""
    client = boto3.client("bedrock-agentcore", region_name=region)
    params = dict(
        agentRuntimeArn=runtime_arn,
        payload=json.dumps({"prompt": prompt}).encode("utf-8"),
    )
    if session_id:
        params["runtimeSessionId"] = session_id
    resp = client.invoke_agent_runtime(**params)
    return parse_sse_response(resp["response"].read().decode("utf-8"))


def run_chatbot(runtime_arn, region, session_id):
    """Interactive conversation loop demonstrating automatic memory hooks."""
    print(f"\n{BOLD}{WHITE}  Memory Hooks Agent Chat{RESET}")
    print(f"  Memory is automatic — no explicit 'remember' commands needed.")
    print(f"  Just chat naturally. The agent builds context over time.")
    print(f"  Try: 'I work at Acme Corp' then later 'Where do I work?'")
    print(f"  Type 'quit' or 'exit' to stop.\n")

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
            response = invoke(runtime_arn, user_input, region, session_id)
            print(f"  {YELLOW}Agent:{RESET} {response}\n")
        except Exception as e:
            print(f"  {RED}Error:{RESET} {str(e)[:200]}\n")


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
    memory_id = config.get("memory_id", "N/A")
    session_id = str(uuid.uuid4())

    banner("Demo 4: Memory Hooks Agent (Interactive)")
    config_val("Runtime ARN", runtime_arn)
    config_val("Memory ID", memory_id)
    config_val("Session", session_id)
    info("Hooks: MessageAdded \u2192 retrieve | AfterInvocation \u2192 save")

    if len(sys.argv) > 1:
        prompt = " ".join(sys.argv[1:])
        section("Single prompt mode")
        prompt_display(prompt)
        response = invoke(runtime_arn, prompt, region, session_id)
        response_display(response)
    else:
        run_chatbot(runtime_arn, region, session_id)

    done()


if __name__ == "__main__":
    main()
