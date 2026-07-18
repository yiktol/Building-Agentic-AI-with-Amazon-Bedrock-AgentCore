"""
Demo 3: Interactive Agent Chatbot — Session Management.

Chat client that demonstrates session persistence. The agent remembers
everything you tell it within the same session. Use 'new session' to
start fresh (proves isolation between sessions).

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
    prompt_display, response_display, GREEN, YELLOW, RED, RESET, BOLD, WHITE, DIM
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
    text = re.sub(r"<thinking>.*?</thinking>\s*", "", text, flags=re.DOTALL).strip()
    return text


def invoke(runtime_arn, prompt, region, session_id):
    """Send a prompt to the deployed session-aware agent."""
    client = boto3.client("bedrock-agentcore", region_name=region)
    resp = client.invoke_agent_runtime(
        agentRuntimeArn=runtime_arn,
        payload=json.dumps({"prompt": prompt}).encode("utf-8"),
        runtimeSessionId=session_id,
    )
    return parse_sse_response(resp["response"].read().decode("utf-8"))


def run_chatbot(runtime_arn, region):
    """Interactive conversation loop with session control."""
    session_id = str(uuid.uuid4())

    print(f"\n{BOLD}{WHITE}  Session Management Chat{RESET}")
    print(f"  Agent remembers context within the same session.")
    print(f"  Commands:")
    print(f"    'new session' — start a fresh session (agent forgets everything)")
    print(f"    'session'     — show current session ID")
    print(f"    'quit'        — exit")
    print(f"\n  {DIM}Session: {session_id}{RESET}\n")

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

        # Session control commands
        if user_input.strip().lower() == "new session":
            session_id = str(uuid.uuid4())
            print(f"  {DIM}→ New session: {session_id}{RESET}")
            print(f"  {DIM}→ Agent now has NO memory of previous conversation{RESET}\n")
            continue

        if user_input.strip().lower() == "session":
            print(f"  {DIM}→ Current session: {session_id}{RESET}\n")
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

    banner("Demo 3: Session Management Agent (Interactive)")
    config_val("Runtime ARN", runtime_arn)
    info("Each session maps to an isolated microVM — 'new session' starts fresh")

    if len(sys.argv) > 1:
        prompt = " ".join(sys.argv[1:])
        session_id = str(uuid.uuid4())
        config_val("Session", session_id)
        section("Single prompt mode")
        prompt_display(prompt)
        response = invoke(runtime_arn, prompt, region, session_id)
        response_display(response)
    else:
        run_chatbot(runtime_arn, region)

    done()


if __name__ == "__main__":
    main()
