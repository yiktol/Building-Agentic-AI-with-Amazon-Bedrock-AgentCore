"""
Demo 4: Invoke async agent — shows immediate response + background work.

Demonstrates:
  1. Synchronous response (quick_summary tool)
  2. Asynchronous response (generate_report tool — starts background task)
  3. Task monitoring (get_task_status — poll status at intervals)
  4. Agent stays responsive while background task runs

Usage:
    python invoke.py
"""

import json
import re
import sys
import os
import time
import uuid

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


def invoke(client, arn: str, prompt: str, session_id: str) -> str:
    response = client.invoke_agent_runtime(
        agentRuntimeArn=arn,
        payload=json.dumps({"prompt": prompt}).encode("utf-8"),
        contentType="application/json",
        accept="application/json",
        runtimeSessionId=session_id,
    )
    return response["response"].read().decode("utf-8")


def extract_task_id(response: str) -> str:
    """Extract task ID from agent response using common patterns."""
    # Try patterns like "Task ID: <id>" or "(Task ID: <id>)"
    match = re.search(r"Task ID[:\s]+([a-zA-Z0-9_-]+)", response)
    if match:
        return match.group(1)
    # Try UUID-style pattern
    match = re.search(r"([0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12})", response)
    if match:
        return match.group(1)
    return None


def main():
    config = load_config()
    arn = config["runtime_arn"]
    region = config["region"]
    client = boto3.client("bedrock-agentcore", region_name=region)
    session_id = f"demo-async-session-{uuid.uuid4().hex}"

    banner("Demo 4: Async Agent — Immediate Response + Background Work")
    config_val("Runtime", arn)

    # Part 1: Synchronous
    section("Part 1: Synchronous (immediate response)")
    prompt1 = "Give me a quick summary about cloud computing."
    prompt_display(prompt1)
    start = time.time()
    resp = invoke(client, arn, prompt1, session_id)
    elapsed = time.time() - start
    response_display(resp)
    info(f"Response time: {elapsed:.1f}s")

    # Part 2: Asynchronous
    section("Part 2: Asynchronous (background task)")
    prompt2 = "Generate a detailed report about AI trends in 2025. This should take about 10 seconds."
    prompt_display(prompt2)
    start = time.time()
    resp = invoke(client, arn, prompt2, session_id)
    elapsed = time.time() - start
    response_display(resp, max_len=400)
    info(f"Response time: {elapsed:.1f}s")

    # Extract and display the Task ID
    task_id = extract_task_id(resp)
    if task_id:
        config_val("Task ID", task_id)
        success("Agent responded immediately with task ID!")
    else:
        success("Agent responded immediately!")
        info("(Task ID not found in response)")

    info("Background task continues in the microVM (up to 8 hours)")

    # Part 3: Monitor Task Status
    section("Part 3: Monitor Task Status (3 checks, 5s interval)")
    info("Polling agent for task status every 5 seconds...")
    print()

    for attempt in range(1, 4):
        info(f"Status check {attempt}/3 — waiting 5 seconds...")
        time.sleep(5)

        status_prompt = "What is the current status of my running tasks?"
        prompt_display(status_prompt)
        start = time.time()
        resp = invoke(client, arn, status_prompt, session_id)
        elapsed = time.time() - start
        response_display(resp, max_len=400)
        info(f"Response time: {elapsed:.1f}s")
        print()

    success("Task monitoring complete!")

    # Part 4: Agent stays responsive
    section("Part 4: Agent stays responsive during background work")
    prompt4 = "While that report generates, give me a quick summary about machine learning."
    prompt_display(prompt4)
    resp = invoke(client, arn, prompt4, session_id)
    response_display(resp)
    success("Agent handles new requests while background task runs!")

    done()
    info("Key APIs: add_async_task() / complete_async_task() / get_async_task_info()")
    print()


if __name__ == "__main__":
    main()
