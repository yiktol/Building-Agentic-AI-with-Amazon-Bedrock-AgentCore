"""
Demo 4: Interactive Agent with Memory Hooks — Local Chatbot.

Runs a local Strands agent with automatic memory hooks:
  - Before each response: retrieve relevant context from STM + LTM
  - After each response: save the turn to STM

Memory is transparent — the agent doesn't need to call tools explicitly.
Just have a conversation and context builds automatically.

Usage:
    python invoke_agent.py                      # Interactive chatbot
    python invoke_agent.py "My name is Alice"   # Single prompt
"""

import contextlib
import io
import json
import os
import sys
import time

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))
from shared.stack_config import get_config
from shared.colors import (
    banner, section, success, info, config_val, done,
    prompt_display, response_display, GREEN, YELLOW, RED, DIM, RESET, BOLD, WHITE
)

from bedrock_agentcore.memory import MemoryClient
from strands import Agent
from strands.models.bedrock import BedrockModel


def run_chatbot(agent, memory_client, memory_id, actor_id, session_id, namespace):
    """Interactive chatbot with automatic memory hooks."""
    print(f"\n{BOLD}{WHITE}  Memory Hooks Agent Chat{RESET}")
    print(f"  Memory is automatic — no explicit 'remember' commands needed.")
    print(f"  Just chat naturally. Context builds over turns.")
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

        # HOOK: MessageAdded → retrieve context
        memories = memory_client.retrieve_memories(
            memory_id=memory_id,
            namespace=namespace,
            query=user_input,
            top_k=3,
        )
        turns = memory_client.get_last_k_turns(
            memory_id=memory_id,
            actor_id=actor_id,
            session_id=session_id,
            k=5,
        )

        context_parts = []
        if memories:
            context_parts.append("Known facts:\n" + "\n".join(f"- {m['content']['text']}" for m in memories))
        if turns:
            stm_msgs = []
            for turn in turns:
                for msg in turn:
                    stm_msgs.append(f"{msg['role']}: {msg['content']['text']}")
            context_parts.append("Recent conversation:\n" + "\n".join(stm_msgs[-6:]))

        if context_parts:
            retrieved = len(memories) + len(turns)
            print(f"  {DIM}[hook: retrieved {retrieved} record(s)]{RESET}")
            full_prompt = "\n".join(context_parts) + f"\n\nUser: {user_input}\n\nRespond concisely."
        else:
            full_prompt = user_input

        try:
            with contextlib.redirect_stdout(io.StringIO()):
                response = agent(full_prompt)
            agent_text = response.message["content"][0]["text"]
            print(f"  {YELLOW}Agent:{RESET} {agent_text}")
        except Exception as e:
            agent_text = f"Error: {str(e)[:150]}"
            print(f"  {RED}Agent:{RESET} {agent_text}")

        # HOOK: AfterInvocation → save turn to STM
        memory_client.create_event(
            memory_id=memory_id,
            actor_id=actor_id,
            session_id=session_id,
            messages=[
                (user_input, "USER"),
                (agent_text, "ASSISTANT"),
            ],
        )
        print(f"  {DIM}[hook: saved to STM]{RESET}\n")


def main():
    os.chdir(os.path.dirname(os.path.abspath(__file__)))
    cfg = get_config()
    memory_id = cfg["memory_semantic_id"]
    region = cfg["region"]

    actor_id = input(f"  Enter actor ID [{GREEN}user-42{RESET}]: ").strip() or "user-42"
    session_id = f"sess-{int(time.time())}"
    namespace = f"/users/{actor_id}/facts/"

    banner("Demo 4: Memory Hooks Agent (Interactive)")
    config_val("Memory ID", memory_id)
    config_val("Actor", actor_id)
    config_val("Session", session_id)
    info("Hooks: MessageAdded → retrieve | AfterInvocation → save")

    memory_client = MemoryClient(region_name=region)

    model = BedrockModel(
        model_id="apac.amazon.nova-lite-v1:0",
        region_name=region,
    )
    agent = Agent(
        model=model,
        system_prompt=(
            "You are a helpful assistant. Be concise and friendly. "
            "Use the conversation context provided to personalize responses."
        ),
    )

    if len(sys.argv) > 1:
        prompt = " ".join(sys.argv[1:])
        section("Single prompt mode")
        prompt_display(prompt)
        with contextlib.redirect_stdout(io.StringIO()):
            response = agent(prompt)
        response_display(response.message["content"][0]["text"])
        memory_client.create_event(
            memory_id=memory_id,
            actor_id=actor_id,
            session_id=session_id,
            messages=[(prompt, "USER"), (response.message["content"][0]["text"], "ASSISTANT")],
        )
    else:
        run_chatbot(agent, memory_client, memory_id, actor_id, session_id, namespace)

    done()
    info("Key: Hooks fire transparently — no explicit memory tool calls")
    info("  • MessageAdded → retrieve STM + LTM context")
    info("  • AfterInvocation → save turn to STM")
    info("  • Compare with Demo 3: tool = explicit; hook = automatic")
    print()


if __name__ == "__main__":
    main()
