"""
Demo 3: Interactive Agent with Memory Tools — Local Chatbot.

Runs a LOCAL Strands agent with custom memory tools that use AgentCore
Memory SDK directly. This demonstrates the memory-as-tool pattern where
the LLM decides when to save/recall.

Unlike the deployed runtime version, this local agent uses STM (immediate)
for within-session memory, so recall works instantly without waiting for
LTM extraction.

The agent has two memory tools:
  - remember(info): saves a fact to short-term memory
  - recall(query): retrieves recent conversation from STM

Usage:
    python invoke_agent.py                           # Interactive chatbot
    python invoke_agent.py "Remember: I like sushi"  # Single prompt
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
    prompt_display, response_display, GREEN, YELLOW, RED, RESET, BOLD, WHITE
)

from bedrock_agentcore.memory import MemoryClient
from strands import Agent, tool
from strands.models.bedrock import BedrockModel


# Global memory state (set in main, used by tools)
_memory_client: MemoryClient = None
_memory_id: str = ""
_actor_id: str = ""
_session_id: str = ""
_namespace: str = ""


@tool
def remember(information: str) -> str:
    """Save a piece of information about the user to memory.

    Args:
        information: The fact or preference to remember (e.g. "User likes sushi")

    Returns:
        Confirmation that the information was saved.
    """
    _memory_client.create_event(
        memory_id=_memory_id,
        actor_id=_actor_id,
        session_id=_session_id,
        messages=[
            (f"Remember: {information}", "USER"),
            (f"Saved to memory: {information}", "ASSISTANT"),
        ],
    )
    return f"Saved: {information}"


@tool
def recall(query: str) -> str:
    """Search memory for information about the user.

    Args:
        query: What to search for (e.g. "food preferences")

    Returns:
        Relevant memories found, or a message if nothing was found.
    """
    # First check STM (immediate - within session)
    turns = _memory_client.get_last_k_turns(
        memory_id=_memory_id,
        actor_id=_actor_id,
        session_id=_session_id,
        k=10,
    )

    # Search through STM events for relevant info
    relevant = []
    query_lower = query.lower()
    for turn in turns:
        for msg in turn:
            text = msg["content"]["text"].lower()
            if any(word in text for word in query_lower.split()):
                relevant.append(msg["content"]["text"])

    # Also try LTM semantic search (may have records from previous sessions)
    try:
        ltm_hits = _memory_client.retrieve_memories(
            memory_id=_memory_id,
            namespace=_namespace,
            query=query,
            top_k=3,
        )
        for h in ltm_hits:
            relevant.append(f"[LTM] {h['content']['text']}")
    except Exception:
        pass

    if relevant:
        return "Found in memory:\n" + "\n".join(f"- {r}" for r in relevant[:5])
    return "No relevant memories found."


def run_chatbot(agent):
    """Interactive conversation loop with memory tools."""
    print(f"\n{BOLD}{WHITE}  Memory Tools Agent Chat{RESET}")
    print(f"  The agent uses 'remember' and 'recall' tools explicitly.")
    print(f"  Try: 'Remember that I like sushi' then 'What food do I like?'")
    print(f"  Type 'quit' or 'exit' to stop.\n")

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

        try:
            with contextlib.redirect_stdout(io.StringIO()):
                response = agent(user_input)
            agent_text = response.message["content"][0]["text"]
            print(f"  {YELLOW}Agent:{RESET} {agent_text}\n")
        except Exception as e:
            print(f"  {RED}Error:{RESET} {str(e)[:200]}\n")


def main():
    global _memory_client, _memory_id, _actor_id, _session_id, _namespace

    os.chdir(os.path.dirname(os.path.abspath(__file__)))
    cfg = get_config()
    _memory_id = cfg["memory_user_pref_id"]
    region = cfg["region"]

    _actor_id = input(f"  Enter actor ID [{GREEN}user-42{RESET}]: ").strip() or "user-42"
    _session_id = f"sess-{int(time.time())}"
    _namespace = f"/users/{_actor_id}"

    banner("Demo 3: Memory Tools Agent (Interactive)")
    config_val("Memory ID", _memory_id)
    config_val("Actor", _actor_id)
    config_val("Session", _session_id)
    info("Agent has 'remember' and 'recall' tools — LLM decides when to use them")

    # Initialize memory client
    _memory_client = MemoryClient(region_name=region)

    # Initialize local agent with memory tools
    model = BedrockModel(
        model_id="apac.amazon.nova-lite-v1:0",
        region_name=region,
    )
    agent = Agent(
        model=model,
        tools=[remember, recall],
        system_prompt=(
            "You are a helpful assistant with memory tools.\n\n"
            "You have two tools:\n"
            "- remember(information): Save a fact about the user\n"
            "- recall(query): Search for stored information\n\n"
            "RULES:\n"
            "- When the user tells you something about themselves, ALWAYS call 'remember' to save it.\n"
            "- When the user asks what you know/remember, ALWAYS call 'recall' first.\n"
            "- Be concise in your responses."
        ),
    )

    if len(sys.argv) > 1:
        prompt = " ".join(sys.argv[1:])
        section("Single prompt mode")
        prompt_display(prompt)
        with contextlib.redirect_stdout(io.StringIO()):
            response = agent(prompt)
        response_display(response.message["content"][0]["text"])
    else:
        run_chatbot(agent)

    done()
    info("Key: Memory-as-tool = agent decides when to save/recall")
    info("  • 'remember' writes to STM (immediate)")
    info("  • 'recall' searches STM + LTM")
    info("  • LTM records appear after async extraction (~60-90s)")
    print()


if __name__ == "__main__":
    main()
