"""
Demo 3: Session Management — demonstrates continuity, isolation, and cleanup.

This script shows three core concepts:
  Part 1: Session Continuity — same session ID retains context
  Part 2: Session Isolation — different session ID = fresh microVM
  Part 3: Session Cleanup — stop sessions to release resources

Usage:
    python invoke.py
"""

import json
import sys
import os
import uuid
import time

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
    """Invoke agent with a specific session ID."""
    response = client.invoke_agent_runtime(
        agentRuntimeArn=arn,
        payload=json.dumps({"prompt": prompt}).encode("utf-8"),
        contentType="application/json",
        accept="application/json",
        runtimeSessionId=session_id,
    )
    return response["response"].read().decode("utf-8")


def main():
    config = load_config()
    arn = config["runtime_arn"]
    region = config["region"]
    client = boto3.client("bedrock-agentcore", region_name=region)

    session_a = f"demo-session-a-{uuid.uuid4().hex}"
    session_b = f"demo-session-b-{uuid.uuid4().hex}"

    banner("Demo 3: Session Management")
    config_val("Runtime", arn)

    # ── Part 1: Session Continuity ────────────────────────────────────────
    section("Part 1: Session CONTINUITY (same microVM)")
    config_val("Session ID", session_a)

    prompt_display("My name is Alice and I live in Seattle.")
    resp = invoke(client, arn, "My name is Alice and I live in Seattle.", session_a)
    response_display(resp)

    time.sleep(2)

    prompt_display("What is my name and where do I live?")
    resp = invoke(client, arn, "What is my name and where do I live?", session_a)
    response_display(resp)
    success("Agent remembers! Same session = same microVM with preserved state")

    # ── Part 2: Session Isolation ─────────────────────────────────────────
    section("Part 2: Session ISOLATION (new microVM)")
    config_val("NEW Session ID", session_b)

    prompt_display("What is my name? (sent to a fresh session)")
    resp = invoke(client, arn, "What is my name?", session_b)
    response_display(resp)
    success("Agent has no context! Different session = isolated microVM")

    # ── Part 3: Stop Sessions ─────────────────────────────────────────────
    section("Part 3: Session CLEANUP (release resources)")
    info("Stopping sessions releases microVM resources")

    for label, sid in [("A", session_a), ("B", session_b)]:
        try:
            client.stop_runtime_session(agentRuntimeArn=arn, runtimeSessionId=sid)
            success(f"Stopped session {label}: {sid}")
        except Exception as e:
            info(f"Session {label}: {e}")

    done()
    info("Key takeaway: Each runtimeSessionId → dedicated microVM")
    print()


if __name__ == "__main__":
    main()
