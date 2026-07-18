"""
Demo 4: Memory Hooks — scripted demonstration.

Runs a local Strands agent with HookProvider-style automatic memory.
Every user message is saved to STM automatically (AfterInvocation hook),
and relevant context is retrieved before each response (MessageAdded hook).

No explicit "remember" or "recall" — it's all transparent to the LLM.

Usage:
    python invoke.py
    python invoke.py "What do you remember about me?"
"""

import contextlib
import io
import json
import os
import sys
import time

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))
from shared.stack_config import get_config
from shared.colors import banner, section, success, info, config_val, prompt_display, response_display, done, DIM, RESET

from bedrock_agentcore.memory import MemoryClient
from strands import Agent
from strands.models.bedrock import BedrockModel


def main():
    os.chdir(os.path.dirname(os.path.abspath(__file__)))
    cfg = get_config()
    memory_id = cfg["memory_semantic_id"]
    region = cfg["region"]
    actor_id = "user-42"
    session_id = f"sess-{int(time.time())}"
    namespace = f"/users/{actor_id}/facts/"

    if len(sys.argv) > 1:
        prompts = [" ".join(sys.argv[1:])]
    else:
        prompts = [
            "Hi, I'm Alex. I'm a vegetarian who lives in Portland.",
            "I work as a data scientist and prefer Python.",
            "What do you remember about me?",
        ]

    banner("Demo 4: Strands Agent — Memory Hooks (Automatic)")
    config_val("Memory ID", memory_id)
    config_val("Actor", actor_id)
    config_val("Session", session_id)
    info("Hooks: auto-save after each turn, auto-retrieve before each response")

    # Initialize
    memory_client = MemoryClient(region_name=region)

    model = BedrockModel(
        model_id="apac.amazon.nova-lite-v1:0",
        region_name=region,
    )
    agent = Agent(
        model=model,
        system_prompt=(
            "You are a helpful assistant. Be concise and friendly. "
            "Use the conversation context provided to personalize your responses."
        ),
    )

    for i, prompt in enumerate(prompts, 1):
        section(f"Prompt {i}/{len(prompts)}")
        prompt_display(prompt)

        # HOOK: MessageAdded → retrieve relevant context (before response)
        memories = memory_client.retrieve_memories(
            memory_id=memory_id,
            namespace=namespace,
            query=prompt,
            top_k=3,
        )
        # Also get STM context
        turns = memory_client.get_last_k_turns(
            memory_id=memory_id,
            actor_id=actor_id,
            session_id=session_id,
            k=5,
        )

        context_parts = []
        if memories:
            context_parts.append("Long-term memories:\n" + "\n".join(f"- {m['content']['text']}" for m in memories))
        if turns:
            stm_msgs = []
            for turn in turns:
                for msg in turn:
                    stm_msgs.append(f"{msg['role']}: {msg['content']['text']}")
            context_parts.append("Recent conversation:\n" + "\n".join(stm_msgs[-6:]))

        if context_parts:
            print(f"  {DIM}[hook: retrieved {len(memories)} LTM + {len(turns)} STM records]{RESET}")
            full_prompt = "\n".join(context_parts) + f"\n\nUser: {prompt}\n\nRespond concisely using known context."
        else:
            full_prompt = prompt

        with contextlib.redirect_stdout(io.StringIO()):
            response = agent(full_prompt)
        agent_text = response.message["content"][0]["text"]
        response_display(agent_text)

        # HOOK: AfterInvocation → save turn to STM (automatic)
        memory_client.create_event(
            memory_id=memory_id,
            actor_id=actor_id,
            session_id=session_id,
            messages=[
                (prompt, "USER"),
                (agent_text, "ASSISTANT"),
            ],
        )
        print(f"  {DIM}[hook: saved turn to STM]{RESET}")

    done()
    info("Key: Hooks fire transparently — agent doesn't 'see' memory operations")
    info("  • MessageAdded → retrieve context (before LLM call)")
    info("  • AfterInvocation → save turn to STM (after response)")
    info("  • Compare with Demo 3: tool = agent decides; hook = automatic")
    print()


if __name__ == "__main__":
    main()
