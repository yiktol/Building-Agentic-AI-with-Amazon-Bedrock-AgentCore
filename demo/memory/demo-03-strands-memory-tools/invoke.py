"""
Demo 3: Memory-as-tool — scripted demonstration.

Runs a local Strands agent with custom 'remember' and 'recall' tools
backed by AgentCore Memory STM. Shows the agent saving facts and
recalling them immediately within the same session.

Usage:
    python invoke.py
    python invoke.py "Do you remember my preferences?"
"""

import contextlib
import io
import json
import os
import sys
import time

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))
from shared.stack_config import get_config
from shared.colors import banner, section, success, info, config_val, prompt_display, response_display, done

from bedrock_agentcore.memory import MemoryClient
from strands import Agent, tool
from strands.models.bedrock import BedrockModel


# Global memory state
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
    # Check STM (immediate - within session)
    turns = _memory_client.get_last_k_turns(
        memory_id=_memory_id,
        actor_id=_actor_id,
        session_id=_session_id,
        k=10,
    )

    relevant = []
    query_lower = query.lower()
    for turn in turns:
        for msg in turn:
            text = msg["content"]["text"].lower()
            if any(word in text for word in query_lower.split()):
                relevant.append(msg["content"]["text"])

    # Also try LTM semantic search
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


def main():
    global _memory_client, _memory_id, _actor_id, _session_id, _namespace

    os.chdir(os.path.dirname(os.path.abspath(__file__)))
    cfg = get_config()
    _memory_id = cfg["memory_user_pref_id"]
    region = cfg["region"]
    _actor_id = "user-42"
    _session_id = f"sess-{int(time.time())}"
    _namespace = f"/users/{_actor_id}"

    if len(sys.argv) > 1:
        prompts = [" ".join(sys.argv[1:])]
    else:
        prompts = [
            "I'm vegetarian and I love Italian cuisine.",
            "I prefer morning meetings and I work remotely from Portland.",
            "Do you remember my food preferences?",
            "What do you know about my work setup?",
        ]

    banner("Demo 3: Strands Agent — Memory as Tool")
    config_val("Memory ID", _memory_id)
    config_val("Actor", _actor_id)
    config_val("Session", _session_id)
    info("Agent uses 'remember' and 'recall' tools — LLM decides when")

    # Initialize
    _memory_client = MemoryClient(region_name=region)

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

    for i, prompt in enumerate(prompts, 1):
        section(f"Prompt {i}/{len(prompts)}")
        prompt_display(prompt)
        with contextlib.redirect_stdout(io.StringIO()):
            response = agent(prompt)
        response_display(response.message["content"][0]["text"])

    done()
    info("Key: Agent explicitly calls memory tools — deliberate save/recall")
    info("  • 'remember' writes to STM (immediate)")
    info("  • 'recall' searches STM + LTM")
    info("  • Pattern: memory-as-tool = agent decides when to use memory")
    print()


if __name__ == "__main__":
    main()
