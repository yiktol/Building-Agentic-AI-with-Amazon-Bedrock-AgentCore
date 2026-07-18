"""
Demo 5: Interactive Agent Chatbot — Streaming Responses.

Chat client that shows real-time token streaming (SSE). Each token
appears as it's generated, giving instant feedback on long responses.

Usage:
    python invoke_agent.py                                      # Interactive
    python invoke_agent.py "Explain quantum computing briefly"  # Single prompt
"""

import json
import os
import re
import sys
import uuid

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))
from shared.colors import (
    banner, section, success, info, config_val, done,
    prompt_display, response_display, GREEN, YELLOW, RED, RESET, BOLD, WHITE, DIM
)

import boto3


def invoke_streaming(runtime_arn, prompt, region, session_id):
    """Send a prompt and stream tokens in real-time. Returns full text."""
    client = boto3.client("bedrock-agentcore", region_name=region)
    resp = client.invoke_agent_runtime(
        agentRuntimeArn=runtime_arn,
        payload=json.dumps({"prompt": prompt}).encode("utf-8"),
        runtimeSessionId=session_id,
        accept="text/event-stream",
    )

    raw = resp["response"].read().decode("utf-8")
    parts = []
    for line in raw.splitlines():
        if line.startswith("data: "):
            chunk = line[len("data: "):]
            if chunk.startswith('"') and chunk.endswith('"'):
                chunk = chunk[1:-1]
            parts.append(chunk)
            # Print each token as it arrives
            print(chunk, end="", flush=True)

    print()  # newline after streaming
    text = "".join(parts)
    text = re.sub(r"<thinking>.*?</thinking>\s*", "", text, flags=re.DOTALL).strip()
    return text


def run_chatbot(runtime_arn, region, session_id):
    """Interactive conversation loop with streaming output."""
    print(f"\n{BOLD}{WHITE}  Streaming Agent Chat{RESET}")
    print(f"  Responses stream token-by-token (SSE).")
    print(f"  Same session — agent remembers context.")
    print(f"  Type 'quit' to stop.\n")

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

        print(f"  {YELLOW}Agent:{RESET} ", end="", flush=True)
        try:
            invoke_streaming(runtime_arn, user_input, region, session_id)
            print()  # blank line after response
        except Exception as e:
            print(f"\n  {RED}Error:{RESET} {str(e)[:200]}\n")


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
    session_id = str(uuid.uuid4())

    banner("Demo 5: Streaming Agent (Interactive)")
    config_val("Runtime ARN", runtime_arn)
    config_val("Session", session_id)
    info("Tokens stream in real-time via SSE (text/event-stream)")

    if len(sys.argv) > 1:
        prompt = " ".join(sys.argv[1:])
        section("Single prompt mode")
        prompt_display(prompt)
        print(f"  {YELLOW}Streaming:{RESET} ", end="", flush=True)
        invoke_streaming(runtime_arn, prompt, region, session_id)
    else:
        run_chatbot(runtime_arn, region, session_id)

    done()


if __name__ == "__main__":
    main()
