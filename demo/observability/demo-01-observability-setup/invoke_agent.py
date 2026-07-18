"""
Demo 1: Interactive HR Agent Chat Client — with OTel Observability.

Chat client for the deployed HR Assistant agent. Each interaction generates
traces visible in CloudWatch GenAI Observability.

Same session maintained → agent remembers context across turns.

Usage:
    python invoke_agent.py                                    # Interactive
    python invoke_agent.py "What is the PTO balance for EMP-001?"  # Single
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
    """Send a prompt to the deployed HR agent."""
    client = boto3.client("bedrock-agentcore", region_name=region)
    resp = client.invoke_agent_runtime(
        agentRuntimeArn=runtime_arn,
        payload=json.dumps({"prompt": prompt}).encode("utf-8"),
        runtimeSessionId=session_id,
    )
    return parse_sse_response(resp["response"].read().decode("utf-8"))


def run_chatbot(runtime_arn, region, session_id):
    """Interactive HR agent conversation loop."""
    print(f"\n{BOLD}{WHITE}  HR Agent Chat (with Observability){RESET}")
    print(f"  Tools: get_pto_balance, submit_pto_request, lookup_hr_policy,")
    print(f"         get_benefits_summary, get_pay_stub")
    print(f"  Every message generates traces in CloudWatch.")
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
    session_id = str(uuid.uuid4())

    banner("Demo 1: HR Agent Chat (Interactive)")
    config_val("Runtime ARN", runtime_arn)
    config_val("Session", session_id)
    config_val("Log Group", config.get("log_group", "N/A"))
    info("Every invocation generates OTel traces → CloudWatch GenAI Observability")

    if len(sys.argv) > 1:
        prompt = " ".join(sys.argv[1:])
        section("Single prompt mode")
        prompt_display(prompt)
        response = invoke(runtime_arn, prompt, region, session_id)
        response_display(response)
    else:
        run_chatbot(runtime_arn, region, session_id)

    done()
    info(f"View traces: CloudWatch → GenAI Observability → Bedrock AgentCore")
    info(f"Session: {session_id}")
    print()


if __name__ == "__main__":
    main()
