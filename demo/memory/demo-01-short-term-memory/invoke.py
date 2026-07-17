"""
Demo 1: Short-term memory — create events and retrieve them.

Shows:
  1. Create events (conversation turns) in short-term memory
  2. List events for a session
  3. Retrieve last K turns via the SDK
  4. Demonstrate actor + session isolation

Usage:
    python invoke.py
"""

import os
import sys
import time

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))
from shared.stack_config import get_config
from shared.colors import banner, section, success, info, config_val, done

import boto3
from bedrock_agentcore.memory import MemoryClient


def main():
    os.chdir(os.path.dirname(os.path.abspath(__file__)))
    cfg = get_config()
    memory_id = cfg["memory_stm_only_id"]
    region = cfg["region"]

    banner("Demo 1: Short-Term Memory — Events & Sessions")
    config_val("Memory ID", memory_id)
    config_val("Region", region)

    client = MemoryClient(region_name=region)

    # ── Part A: Write conversation events ──────────────────────────────
    section("Part A: Writing conversation events")
    actor_id = "user-42"
    session_id = f"sess-{int(time.time())}"
    info(f"Actor: {actor_id} | Session: {session_id}")

    messages = [
        ("Hi, I'm Alex. I prefer Python over Java.", "USER"),
        ("Nice to meet you, Alex! I'll keep that in mind.", "ASSISTANT"),
        ("What's the weather like in Seattle?", "USER"),
        ("Seattle is currently rainy at 55°F.", "ASSISTANT"),
        ("I'm planning a trip to Miami next month.", "USER"),
    ]

    info(f"Creating event with {len(messages)} messages...")
    client.create_event(
        memory_id=memory_id,
        actor_id=actor_id,
        session_id=session_id,
        messages=messages,
    )
    success(f"Event created with {len(messages)} messages")

    # ── Part B: List events ────────────────────────────────────────────
    section("Part B: Listing events for the session")
    data = boto3.client("bedrock-agentcore", region_name=region)
    events = data.list_events(
        memoryId=memory_id,
        actorId=actor_id,
        sessionId=session_id,
    )["events"]
    success(f"Found {len(events)} event(s) in session {session_id}")
    for e in events:
        info(f"  Event ID: {e['eventId']} | Timestamp: {e['eventTimestamp']}")

    # ── Part C: Get last K turns (SDK helper) ──────────────────────────
    section("Part C: Retrieving last K turns (SDK)")
    turns = client.get_last_k_turns(
        memory_id=memory_id,
        actor_id=actor_id,
        session_id=session_id,
        k=5,
    )
    success(f"Retrieved {len(turns)} turn(s)")
    for turn in turns:
        for msg in turn:
            role = msg["role"]
            text = msg["content"]["text"]
            info(f"  {role}: {text[:80]}")

    # ── Part D: Actor isolation ────────────────────────────────────────
    section("Part D: Actor isolation — different actor sees nothing")
    other_events = data.list_events(
        memoryId=memory_id,
        actorId="user-99",
        sessionId=session_id,
    )["events"]
    success(f"user-99 sees {len(other_events)} events (expected: 0)")
    info("Actors are isolated — no cross-actor data leakage")

    done()
    info("Key: Short-term memory stores raw events scoped by actor + session")
    info("No extraction, no embeddings — immediate low-latency access")
    print()


if __name__ == "__main__":
    main()
