"""
Demo 5: Test IAM-scoped memory access.

Shows:
  1. Role A can read user-A's events → success
  2. Role A tries to read user-B's events → AccessDeniedException
  3. Role B can read user-B's events → success
  4. Demonstrates fine-grained IAM condition on actorId

Usage:
    python invoke.py
"""

import json
import os
import sys
import time

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))
from shared.stack_config import get_config
from shared.colors import banner, section, success, info, error, config_val, done

import boto3


def assume_role(role_arn: str, region: str, session_name: str = "demo") -> boto3.Session:
    """Assume an IAM role and return a boto3 session with those credentials."""
    sts = boto3.client("sts", region_name=region)
    resp = sts.assume_role(RoleArn=role_arn, RoleSessionName=session_name)
    creds = resp["Credentials"]
    return boto3.Session(
        aws_access_key_id=creds["AccessKeyId"],
        aws_secret_access_key=creds["SecretAccessKey"],
        aws_session_token=creds["SessionToken"],
        region_name=region,
    )


def try_list_events(session: boto3.Session, memory_id: str, actor_id: str, session_id: str, region: str):
    """Try listing events for an actor. Returns (success: bool, result)."""
    client = session.client("bedrock-agentcore", region_name=region)
    try:
        resp = client.list_events(
            memoryId=memory_id,
            actorId=actor_id,
            sessionId=session_id,
        )
        return True, resp.get("events", [])
    except Exception as e:
        return False, str(e)


def main():
    os.chdir(os.path.dirname(os.path.abspath(__file__)))
    cfg = get_config()
    memory_id = cfg["memory_semantic_id"]
    region = cfg["region"]
    role_a_arn = cfg["scoped_role_a_arn"]
    role_b_arn = cfg["scoped_role_b_arn"]

    banner("Demo 5: IAM-Scoped Memory Access")
    config_val("Memory ID", memory_id)
    config_val("Role A (user-A only)", role_a_arn.split("/")[-1])
    config_val("Role B (user-B only)", role_b_arn.split("/")[-1])

    # ── Test A: Role A reads user-A → should succeed ──────────────────
    section("Test A: Role A reads user-A's events")
    info("Expected: SUCCESS (actorId=user-A matches condition)")
    session_a = assume_role(role_a_arn, region, "role-A-reads-A")
    ok, result = try_list_events(session_a, memory_id, "user-A", "sess-A", region)
    if ok:
        success(f"✓ Role A can read user-A: {len(result)} event(s)")
    else:
        error(f"✗ Unexpected failure: {result[:150]}")

    # ── Test B: Role A reads user-B → should FAIL ─────────────────────
    section("Test B: Role A tries to read user-B's events")
    info("Expected: AccessDeniedException (actorId=user-B not allowed)")
    ok, result = try_list_events(session_a, memory_id, "user-B", "sess-B", region)
    if not ok:
        success("✓ Got expected denial: AccessDeniedException")
        info(f"  {str(result)[:150]}")
    else:
        error("✗ Unexpected success — IAM policy may not be enforced yet")

    # ── Test C: Role B reads user-B → should succeed ──────────────────
    section("Test C: Role B reads user-B's events")
    info("Expected: SUCCESS (actorId=user-B matches condition)")
    session_b = assume_role(role_b_arn, region, "role-B-reads-B")
    ok, result = try_list_events(session_b, memory_id, "user-B", "sess-B", region)
    if ok:
        success(f"✓ Role B can read user-B: {len(result)} event(s)")
    else:
        error(f"✗ Unexpected failure: {result[:150]}")

    # ── Test D: Role B reads user-A → should FAIL ─────────────────────
    section("Test D: Role B tries to read user-A's events")
    info("Expected: AccessDeniedException")
    ok, result = try_list_events(session_b, memory_id, "user-A", "sess-A", region)
    if not ok:
        success("✓ Got expected denial: AccessDeniedException")
    else:
        error("✗ Unexpected success")

    done()
    info("Key: IAM condition on bedrock-agentcore:actorId enforces tenant isolation")
    info("Each role can only access its own actor's memory — no cross-user leakage")
    print()

    # Show the IAM policy for reference
    section("Reference: IAM Policy (Role A)")
    policy = {
        "Effect": "Allow",
        "Action": ["bedrock-agentcore:CreateEvent", "bedrock-agentcore:ListEvents", "..."],
        "Resource": f"arn:aws:bedrock-agentcore:{region}:*:memory/{memory_id}",
        "Condition": {"StringEquals": {"bedrock-agentcore:actorId": "user-A"}},
    }
    print(json.dumps(policy, indent=2))
    print()


if __name__ == "__main__":
    main()
