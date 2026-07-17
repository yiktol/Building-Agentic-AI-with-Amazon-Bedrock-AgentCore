"""
Demo 1: Invoke the HR Assistant and show traces flow to CloudWatch.

Sends sample HR prompts that exercise multiple tools, then shows
where to find the resulting sessions/traces/spans in CloudWatch.

Usage:
    python invoke.py
    python invoke.py "What is the PTO balance for EMP-001?"
"""

import json
import os
import sys
import uuid

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
    )
    if session_id:
        params["runtimeSessionId"] = session_id

    response = client.invoke_agent_runtime(**params)
    raw = response["response"].read().decode("utf-8")

    # Parse SSE streaming response
    parts = []
    for line in raw.splitlines():
        if line.startswith("data: "):
            chunk = line[len("data: "):]
            # Remove surrounding quotes if present
            if chunk.startswith('"') and chunk.endswith('"'):
                chunk = chunk[1:-1]
            parts.append(chunk)

    return "".join(parts) if parts else raw


def main():
    os.chdir(os.path.dirname(os.path.abspath(__file__)))
    config = load_config()
    runtime_arn = config["runtime_arn"]
    region = config["region"]

    if len(sys.argv) > 1:
        prompts = [("custom", " ".join(sys.argv[1:]))]
    else:
        prompts = [
            ("EMP-001", "What is my current PTO balance?"),
            ("EMP-001", "Please submit a PTO request from 2026-08-01 to 2026-08-05 for vacation."),
            ("EMP-042", "Tell me about the 401k plan — how much does the company match?"),
        ]

    banner("Demo 1: Invoking HR Assistant (traces → CloudWatch)")
    config_val("Runtime", runtime_arn)
    config_val("Log Group", config["log_group"])

    session_id = str(uuid.uuid4())
    info(f"Session ID: {session_id}")

    for i, (emp_id, prompt) in enumerate(prompts, 1):
        section(f"Prompt {i}/{len(prompts)}")
        full_prompt = prompt if emp_id == "custom" else f"Employee ID: {emp_id}. {prompt}"
        prompt_display(full_prompt)
        response = invoke(runtime_arn, full_prompt, region, session_id)
        response_display(response)

    done()
    info("Traces are now flowing to CloudWatch (allow 2-3 min for ingestion)")
    info("")
    info("View in CloudWatch Console:")
    info("  1. Open CloudWatch → GenAI Observability → Bedrock AgentCore")
    info("  2. Click 'Agents' tab → find your agent")
    info("  3. Click into a session → see traces → see spans")
    info("")
    info("Hierarchy: Session → Trace → Span → Sub-Span")
    info(f"  Session: {session_id}")
    info(f"  Service: {config['service_name']}")
    print()


if __name__ == "__main__":
    main()
