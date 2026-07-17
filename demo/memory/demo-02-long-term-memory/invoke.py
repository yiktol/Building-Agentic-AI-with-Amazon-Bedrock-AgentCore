"""
Demo 2: Long-term memory — write events, wait for extraction, retrieve records.

Shows:
  1. Write conversation events (user preferences and facts)
  2. Wait for async extraction (~60s)
  3. Retrieve structured memory records via semantic search
  4. Show that extracted records are organized by namespace

Usage:
    python invoke.py
"""

import os
import sys
import time

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))
from shared.stack_config import get_config
from shared.colors import banner, section, success, info, config_val, done

from bedrock_agentcore.memory import MemoryClient


EXTRACTION_WAIT = 90  # seconds


def main():
    os.chdir(os.path.dirname(os.path.abspath(__file__)))
    cfg = get_config()
    memory_id = cfg["memory_semantic_id"]
    region = cfg["region"]

    banner("Demo 2: Long-Term Memory — Semantic Extraction")
    config_val("Memory ID", memory_id)

    client = MemoryClient(region_name=region)
    actor_id = "user-42"
    session_id = f"sess-{int(time.time())}"

    # ── Part A: Write conversation events ──────────────────────────────
    section("Part A: Writing conversation events")
    info(f"Actor: {actor_id} | Session: {session_id}")

    messages = [
        ("Hi, I'm Alex. I prefer Python over Java and I'm based in Berlin.", "USER"),
        ("Nice to meet you, Alex! I'll remember your preferences.", "ASSISTANT"),
        ("I'm allergic to peanuts, by the way.", "USER"),
        ("Noted — I'll keep that in mind for any food recommendations.", "ASSISTANT"),
        ("I work as a data engineer at a startup.", "USER"),
        ("That's great! Python is an excellent choice for data engineering.", "ASSISTANT"),
    ]

    client.create_event(
        memory_id=memory_id,
        actor_id=actor_id,
        session_id=session_id,
        messages=messages,
    )
    success(f"Created event with {len(messages)} messages")

    # ── Part B: Wait for extraction ────────────────────────────────────
    section("Part B: Waiting for async extraction")
    info("Semantic strategy processes events in the background")
    info(f"Waiting {EXTRACTION_WAIT}s for extraction to complete...")
    for i in range(EXTRACTION_WAIT, 0, -10):
        info(f"  {i}s remaining...")
        time.sleep(10)
    success("Extraction window complete")

    # ── Part C: Retrieve memory records ────────────────────────────────
    section("Part C: Retrieving memory records (semantic search)")
    namespace = f"/users/{actor_id}/facts/"
    info(f"Namespace: {namespace}")
    info("Query: 'What are Alex's preferences and constraints?'")

    hits = client.retrieve_memories(
        memory_id=memory_id,
        namespace=namespace,
        query="What are Alex's preferences and constraints?",
        top_k=5,
    )

    if hits:
        success(f"Retrieved {len(hits)} memory record(s):")
        for i, h in enumerate(hits, 1):
            text = h["content"]["text"]
            info(f"  {i}. {text[:120]}")
    else:
        info("No records yet — extraction may still be processing")
        info("Try running again in 30 seconds")

    # ── Part D: Different query ────────────────────────────────────────
    section("Part D: Different semantic query")
    info("Query: 'What food allergies does the user have?'")

    hits2 = client.retrieve_memories(
        memory_id=memory_id,
        namespace=namespace,
        query="What food allergies does the user have?",
        top_k=3,
    )

    if hits2:
        success(f"Retrieved {len(hits2)} record(s):")
        for h in hits2:
            info(f"  → {h['content']['text'][:120]}")
    else:
        info("No records found for this query yet")

    done()
    info("Key: Events → async extraction → structured records → semantic search")
    info("Namespace /users/{actorId}/facts/ isolates per-user knowledge")
    print()


if __name__ == "__main__":
    main()
