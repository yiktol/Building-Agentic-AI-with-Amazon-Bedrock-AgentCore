"""Shared helpers for harness demos."""

import json
import os
import sys
import time
import uuid

import boto3
from boto3.session import Session


def get_aws_context():
    """Return (region, account_id) from environment or session defaults."""
    session = Session()
    region = (
        os.environ.get("AWS_REGION")
        or os.environ.get("AWS_DEFAULT_REGION")
        or session.region_name
        or "ap-southeast-1"
    )
    account_id = session.client("sts").get_caller_identity()["Account"]
    return region, account_id


def create_harness(name: str, role_arn: str, region: str) -> dict:
    """Create a harness and wait for READY. Returns dict with harness_id, harness_arn."""
    control = boto3.client("bedrock-agentcore-control", region_name=region)

    print(f"  Creating harness '{name}'...")
    resp = control.create_harness(harnessName=name, executionRoleArn=role_arn)
    harness = resp["harness"]
    harness_id = harness["harnessId"]
    harness_arn = harness["arn"]
    print(f"  ✓ Harness created: {harness_id}")

    print("  Waiting for READY...")
    for i in range(60):  # up to 5 minutes
        resp = control.get_harness(harnessId=harness_id)
        status = resp["harness"]["status"]
        if status == "READY":
            print(f"  ✓ Harness READY")
            return {"harness_id": harness_id, "harness_arn": harness_arn}
        if "FAILED" in status:
            print(f"  ✗ Harness failed: {status}")
            sys.exit(1)
        time.sleep(5)

    print("  ✗ Timed out waiting for harness")
    sys.exit(1)


def get_harness_status(harness_id: str, region: str) -> str:
    """Get the current status of a harness. Returns status string or None if not found."""
    control = boto3.client("bedrock-agentcore-control", region_name=region)
    try:
        resp = control.get_harness(harnessId=harness_id)
        return resp["harness"]["status"]
    except control.exceptions.ResourceNotFoundException:
        return None
    except Exception:
        return None


def invoke_harness_prompt(
    harness_arn: str,
    session_id: str,
    prompt: str,
    region: str,
    model_id: str = "global.anthropic.claude-haiku-4-5-20251001-v1:0",
) -> tuple:
    """Invoke harness with a prompt and return (text_response, tool_calls)."""
    client = boto3.client("bedrock-agentcore", region_name=region)

    response = client.invoke_harness(
        harnessArn=harness_arn,
        runtimeSessionId=session_id,
        messages=[{"role": "user", "content": [{"text": prompt}]}],
        model={"bedrockModelConfig": {"modelId": model_id}},
    )

    text_parts = []
    tool_calls = []
    for event in response["stream"]:
        if "contentBlockStart" in event:
            start = event["contentBlockStart"].get("start", {})
            if "toolUse" in start:
                tool_calls.append(start["toolUse"].get("name", "?"))
        elif "contentBlockDelta" in event:
            delta = event["contentBlockDelta"].get("delta", {})
            if "text" in delta:
                text_parts.append(delta["text"])
        elif "internalServerException" in event:
            text_parts.append(f"[Error: {event['internalServerException']}]")

    return "".join(text_parts), tool_calls


def invoke_harness_streaming(
    harness_arn: str,
    session_id: str,
    prompt: str,
    region: str,
    model_id: str = "global.anthropic.claude-haiku-4-5-20251001-v1:0",
    print_stream: bool = True,
) -> tuple:
    """Invoke harness with streaming output to console. Returns (full_text, tool_calls)."""
    client = boto3.client("bedrock-agentcore", region_name=region)

    response = client.invoke_harness(
        harnessArn=harness_arn,
        runtimeSessionId=session_id,
        messages=[{"role": "user", "content": [{"text": prompt}]}],
        model={"bedrockModelConfig": {"modelId": model_id}},
    )

    text_parts = []
    tool_calls = []
    for event in response["stream"]:
        if "contentBlockStart" in event:
            start = event["contentBlockStart"].get("start", {})
            if "toolUse" in start:
                tool_name = start["toolUse"].get("name", "?")
                tool_calls.append(tool_name)
                if print_stream:
                    print(f"\n  🔧 Tool call: {tool_name}")
        elif "contentBlockDelta" in event:
            delta = event["contentBlockDelta"].get("delta", {})
            if "text" in delta:
                text_parts.append(delta["text"])
                if print_stream:
                    print(delta["text"], end="", flush=True)
        elif "internalServerException" in event:
            err = f"[Error: {event['internalServerException']}]"
            text_parts.append(err)
            if print_stream:
                print(err)

    if print_stream:
        print()  # newline after streaming

    return "".join(text_parts), tool_calls


def execute_command(harness_arn: str, session_id: str, command: str, region: str) -> tuple:
    """Run a shell command on the harness microVM via ExecuteCommand. Returns (stdout, stderr, exit_code)."""
    client = boto3.client("bedrock-agentcore", region_name=region)

    resp = client.invoke_agent_runtime_command(
        agentRuntimeArn=harness_arn,
        runtimeSessionId=session_id,
        body={"command": command},
    )

    stdout_parts = []
    stderr_parts = []
    exit_code = None
    for event in resp["stream"]:
        if "chunk" in event:
            chunk = event["chunk"]
            if "contentDelta" in chunk:
                d = chunk["contentDelta"]
                if "stdout" in d:
                    stdout_parts.append(d["stdout"])
                if "stderr" in d:
                    stderr_parts.append(d["stderr"])
            elif "contentStop" in chunk:
                exit_code = chunk["contentStop"].get("exitCode", -1)

    return "".join(stdout_parts), "".join(stderr_parts), exit_code


def delete_harness(harness_id: str, region: str):
    """Delete a harness by ID."""
    control = boto3.client("bedrock-agentcore-control", region_name=region)
    try:
        control.delete_harness(harnessId=harness_id)
        print(f"  ✓ Harness deleted: {harness_id}")
    except control.exceptions.ResourceNotFoundException:
        print(f"  ⚠ Harness not found (already deleted): {harness_id}")
    except Exception as e:
        print(f"  ✗ Error deleting harness: {e}")


def save_config(config: dict, config_file: str = "runtime_config.json"):
    """Save deployment config to JSON file."""
    with open(config_file, "w") as f:
        json.dump(config, f, indent=2)
    print(f"  Config saved to: {config_file}")


def load_config(config_file: str = "runtime_config.json") -> dict:
    """Load deployment config from JSON file."""
    try:
        with open(config_file) as f:
            return json.load(f)
    except FileNotFoundError:
        print(f"Error: {config_file} not found. Run deploy.py first.")
        sys.exit(1)


def new_session_id() -> str:
    """Generate a new unique session ID."""
    return str(uuid.uuid4())
