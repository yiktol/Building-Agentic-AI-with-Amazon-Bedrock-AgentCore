"""
Demo 2: Interactive Agent with Long-Term Memory — Chatbot.

Demonstrates how a local Strands agent uses AgentCore long-term memory
to recall facts across sessions. Each turn is saved to STM (which triggers
async extraction into LTM), and before each response the agent retrieves
relevant memories via semantic search.

This simulates how a production agent with LTM works:
  1. User sends a message
  2. Agent searches LTM for relevant memories (semantic search)
  3. Agent generates a response enriched with recalled context
  4. Conversation is saved to STM → extraction pipeline builds LTM

Try telling the agent facts about yourself, then ask about them later.
Memories extracted into LTM persist across sessions.

Usage:
    python invoke_agent.py                              # Interactive chatbot
    python invoke_agent.py "What do you know about me?" # Single prompt
"""

import contextlib
import io
import os
import sys
import time

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))
from shared.stack_config import get_config
from shared.colors import (
    banner, section, success, info, config_val, done,
    prompt_display, response_display, GREEN, YELLOW, RED, RESET, BOLD, WHITE, DIM
)

from bedrock_agentcore.memory import MemoryClient
from strands import Agent
from strands.models import BedrockModel


def run_chatbot(agent, memory_client, memory_id, actor_id, session_id, namespace, region):
    """Interactive chatbot with LTM-backed recall."""
    print(f"\n{BOLD}{WHITE}  Long-Term Memory Chatbot{RESET}")
    print(f"  The agent searches LTM before each response for relevant context.")
    print(f"  Tell it facts → they get extracted into LTM → recalled later.")
    print(f"  Type 'quit' to stop, 'recall <query>' to search LTM directly.\n")

    turn_count = 0

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

        # Special command: direct LTM search
        if user_input.strip().lower().startswith("recall "):
            query = user_input.strip()[7:]
            hits = memory_client.retrieve_memories(
                memory_id=memory_id,
                namespace=namespace,
                query=query,
                top_k=5,
            )
            if hits:
                print(f"\n  {BOLD}--- LTM Records ({len(hits)}) ---{RESET}")
                for i, h in enumerate(hits, 1):
                    print(f"  {DIM}{i}.{RESET} {h['content']['text'][:120]}")
                print(f"  {BOLD}--- End ---{RESET}\n")
            else:
                print(f"  {DIM}No LTM records found for: '{query}'{RESET}\n")
            continue

        turn_count += 1

        # Step 1: Search LTM for relevant context
        memories = memory_client.retrieve_memories(
            memory_id=memory_id,
            namespace=namespace,
            query=user_input,
            top_k=3,
        )

        # Build context from recalled memories
        memory_context = ""
        if memories:
            facts = [m["content"]["text"] for m in memories]
            memory_context = "Known facts about the user:\n" + "\n".join(f"- {f}" for f in facts)
            print(f"  {DIM}[recalled {len(memories)} memory record(s)]{RESET}")

        # Step 2: Generate response with LTM context
        if memory_context:
            full_prompt = f"{memory_context}\n\nUser: {user_input}\n\nRespond concisely using the known facts when relevant."
        else:
            full_prompt = user_input

        try:
            with contextlib.redirect_stdout(io.StringIO()):
                response = agent(full_prompt)
            agent_text = response.message["content"][0]["text"]
        except Exception as e:
            agent_text = f"Error: {str(e)[:150]}"

        print(f"  {YELLOW}Agent:{RESET} {agent_text}\n")

        # Step 3: Save this turn to STM (triggers async LTM extraction)
        memory_client.create_event(
            memory_id=memory_id,
            actor_id=actor_id,
            session_id=session_id,
            messages=[
                (user_input, "USER"),
                (agent_text, "ASSISTANT"),
            ],
        )

    # Show final stats
    print(f"\n  {BOLD}Session complete:{RESET} {turn_count} turn(s) saved")
    print(f"  Events saved to STM → async extraction builds LTM records")
    print(f"  LTM records will be available via semantic search in ~60-90s")


def main():
    os.chdir(os.path.dirname(os.path.abspath(__file__)))
    cfg = get_config()
    memory_id = cfg["memory_semantic_id"]
    region = cfg["region"]

    actor_id = input(f"  Enter actor ID [{GREEN}user-42{RESET}]: ").strip() or "user-42"
    session_id = f"sess-{int(time.time())}"
    namespace = f"/users/{actor_id}/facts/"

    banner("Demo 2: Long-Term Memory Agent (Interactive)")
    config_val("Memory ID", memory_id)
    config_val("Actor", actor_id)
    config_val("Session", session_id)
    config_val("Namespace", namespace)
    info("Flow: search LTM → respond with context → save to STM → async extraction")

    # Initialize memory client
    memory_client = MemoryClient(region_name=region)

    # Initialize local agent
    model = BedrockModel(
        model_id="apac.amazon.nova-lite-v1:0",
        region_name=region,
    )
    agent = Agent(
        model=model,
        system_prompt=(
            "You are a helpful assistant with long-term memory. "
            "Use the known facts provided to personalize your responses. "
            "Be concise and friendly."
        ),
    )

    if len(sys.argv) > 1:
        # Single prompt mode
        prompt = " ".join(sys.argv[1:])
        section("Single prompt mode")
        prompt_display(prompt)

        # Search LTM
        memories = memory_client.retrieve_memories(
            memory_id=memory_id,
            namespace=namespace,
            query=prompt,
            top_k=3,
        )
        if memories:
            info(f"Recalled {len(memories)} memory record(s)")

        memory_context = ""
        if memories:
            facts = [m["content"]["text"] for m in memories]
            memory_context = "Known facts about the user:\n" + "\n".join(f"- {f}" for f in facts)

        full_prompt = f"{memory_context}\n\nUser: {prompt}" if memory_context else prompt

        with contextlib.redirect_stdout(io.StringIO()):
            response = agent(full_prompt)
        agent_text = response.message["content"][0]["text"]
        response_display(agent_text)

        # Save to STM
        memory_client.create_event(
            memory_id=memory_id,
            actor_id=actor_id,
            session_id=session_id,
            messages=[
                (prompt, "USER"),
                (agent_text, "ASSISTANT"),
            ],
        )
        success("Turn saved → extraction will build LTM records in ~60-90s")
    else:
        run_chatbot(agent, memory_client, memory_id, actor_id, session_id, namespace, region)

    done()
    info("Key: LTM provides cross-session recall via semantic search")
    info("  • Events saved to STM trigger async extraction")
    info("  • Semantic strategy extracts structured facts")
    info("  • retrieve_memories finds relevant records by meaning")
    info("  • Use 'recall <query>' to search LTM directly")
    print()


if __name__ == "__main__":
    main()
