"""
Demo 1: Interactive Agent with Short-Term Memory — Chatbot.

Demonstrates how a local Strands agent uses AgentCore short-term memory
to maintain conversation context. Each turn is saved as an event in STM,
and previous turns are retrieved with get_last_k_turns before each response.

This simulates how a real production agent uses STM for session continuity:
  1. User sends a message
  2. Agent retrieves last K turns from STM (conversation context)
  3. Agent generates a response with full context
  4. Both user message and agent response are saved to STM

Try having a multi-turn conversation — the agent remembers everything
within the session because STM provides the context window.

Usage:
    python invoke_agent.py                          # Interactive chatbot
    python invoke_agent.py "I prefer dark mode"     # Single prompt
"""

import os
import sys
import time
import uuid

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))
from shared.stack_config import get_config
from shared.colors import (
    banner, section, success, info, config_val, done,
    prompt_display, response_display, GREEN, YELLOW, RED, RESET, BOLD, WHITE
)

from bedrock_agentcore.memory import MemoryClient
from strands import Agent
from strands.models import BedrockModel


def run_chatbot(agent, memory_client, memory_id, actor_id, session_id):
    """Interactive chatbot with STM-backed conversation context."""
    print(f"\n{BOLD}{WHITE}  Short-Term Memory Chatbot{RESET}")
    print(f"  Each message is saved to STM. Context is reloaded each turn.")
    print(f"  Try a multi-turn conversation — the agent remembers everything.")
    print(f"  Type 'quit' to stop, 'history' to show stored events.\n")

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

        # Special command: show history
        if user_input.strip().lower() == "history":
            turns = memory_client.get_last_k_turns(
                memory_id=memory_id,
                actor_id=actor_id,
                session_id=session_id,
                k=10,
            )
            print(f"\n  {BOLD}--- STM History ({len(turns)} turn(s)) ---{RESET}")
            for turn in turns:
                for msg in turn:
                    role = msg["role"]
                    text = msg["content"]["text"]
                    color = GREEN if role == "USER" else YELLOW
                    print(f"  {color}{role}:{RESET} {text[:100]}")
            print(f"  {BOLD}--- End History ---{RESET}\n")
            continue

        turn_count += 1

        # Step 1: Retrieve context from STM
        context_turns = memory_client.get_last_k_turns(
            memory_id=memory_id,
            actor_id=actor_id,
            session_id=session_id,
            k=5,
        )

        # Build context string from previous turns
        context_messages = []
        for turn in context_turns:
            for msg in turn:
                context_messages.append(f"{msg['role']}: {msg['content']['text']}")

        # Step 2: Generate response with context
        if context_messages:
            full_prompt = (
                f"Previous conversation:\n"
                + "\n".join(context_messages[-10:])  # Last 10 messages
                + f"\n\nUser: {user_input}\n\nRespond concisely."
            )
        else:
            full_prompt = user_input

        try:
            import io
            import contextlib
            # Suppress streaming output from Strands agent
            with contextlib.redirect_stdout(io.StringIO()):
                response = agent(full_prompt)
            agent_text = response.message["content"][0]["text"]
        except Exception as e:
            agent_text = f"Error: {str(e)[:150]}"

        print(f"  {YELLOW}Agent:{RESET} {agent_text}\n")

        # Step 3: Save this turn to STM
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
    print(f"\n  {BOLD}Session complete:{RESET} {turn_count} turn(s) saved to STM")
    print(f"  Actor: {actor_id} | Session: {session_id}")


def main():
    os.chdir(os.path.dirname(os.path.abspath(__file__)))
    cfg = get_config()
    memory_id = cfg["memory_stm_only_id"]
    region = cfg["region"]

    actor_id = input(f"  Enter actor ID [{GREEN}user-42{RESET}]: ").strip() or "user-42"
    session_id = f"sess-{int(time.time())}"

    banner("Demo 1: Short-Term Memory Agent (Interactive)")
    config_val("Memory ID", memory_id)
    config_val("Actor", actor_id)
    config_val("Session", session_id)
    config_val("Session", session_id)
    info("Each turn: retrieve context from STM → respond → save to STM")

    # Initialize memory client
    memory_client = MemoryClient(region_name=region)

    # Initialize local agent (not deployed — runs locally)
    model = BedrockModel(
        model_id="apac.amazon.nova-lite-v1:0",
        region_name=region,
    )
    agent = Agent(
        model=model,
        system_prompt=(
            "You are a helpful assistant. Be concise and friendly. "
            "Use the conversation context provided to maintain continuity."
        ),
    )

    if len(sys.argv) > 1:
        # Single prompt mode
        prompt = " ".join(sys.argv[1:])
        section("Single prompt mode")
        prompt_display(prompt)

        import io
        import contextlib
        with contextlib.redirect_stdout(io.StringIO()):
            response = agent(prompt)
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
        success("Turn saved to short-term memory")
    else:
        run_chatbot(agent, memory_client, memory_id, actor_id, session_id)

    done()
    info("Key: STM provides immediate context for session continuity")
    info("  • Each turn saved as an event (actor + session scoped)")
    info("  • get_last_k_turns reloads context for the next response")
    info("  • No extraction — raw events available instantly")
    print()


if __name__ == "__main__":
    main()
