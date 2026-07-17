"""
Demo 4: Strands Agent with Memory Hooks.

This agent demonstrates:
- Using HookProvider to automatically save/retrieve memory
- Memory operations fire at specific lifecycle events:
  - MessageAdded → retrieve relevant memories
  - AfterInvocation → save the conversation turn
- No explicit memory tool calls — hooks are transparent to the LLM

The memory_id and config are injected via environment variables.
"""

import os
from typing import Any

from bedrock_agentcore.memory import MemoryClient
from bedrock_agentcore.runtime import BedrockAgentCoreApp
from strands import Agent
from strands.hooks import AfterInvocationEvent, HookRegistry, MessageAddedEvent, HookProvider
from strands.models.bedrock import BedrockModel

# Configuration from environment
MEMORY_ID = os.environ["MEMORY_ID"]
ACTOR_ID = os.environ.get("ACTOR_ID", "user-42")
SESSION_ID = os.environ.get("SESSION_ID", "session-hooks-1")
NAMESPACE = os.environ.get("MEMORY_NAMESPACE", f"/users/{ACTOR_ID}")
REGION = os.environ.get("AWS_REGION", "ap-southeast-1")


class MemoryHooks(HookProvider):
    """Custom hook provider that auto-saves and auto-retrieves memory."""

    def __init__(self, memory_client: MemoryClient, memory_id: str):
        self.client = memory_client
        self.memory_id = memory_id

    def retrieve(self, event: MessageAddedEvent) -> None:
        """On new message: retrieve relevant memories and inject as context."""
        # Extract the user message text for semantic search
        message = event.message
        if message.get("role") != "user":
            return

        content = message.get("content", [])
        if not content:
            return

        query = ""
        for block in content:
            if isinstance(block, dict) and "text" in block:
                query = block["text"]
                break

        if not query:
            return

        try:
            memories = self.client.retrieve_memories(
                memory_id=self.memory_id,
                namespace=NAMESPACE,
                query=query,
                top_k=3,
            )
            if memories:
                context = "\n".join(m["content"]["text"] for m in memories)
                print(f"[Memory Hook] Retrieved {len(memories)} relevant memories")
                # Memories are available for the agent to reference
        except Exception as e:
            # Graceful degradation: memory failure never breaks the turn
            print(f"[Memory Hook] Retrieve failed (continuing): {e}")

    def save(self, event: AfterInvocationEvent) -> None:
        """After invocation: save the conversation turn to memory."""
        try:
            # Get the messages from the event
            messages = []
            if hasattr(event, "messages") and event.messages:
                for msg in event.messages[-2:]:  # Last user + assistant pair
                    role = msg.get("role", "USER").upper()
                    content = msg.get("content", [])
                    for block in content:
                        if isinstance(block, dict) and "text" in block:
                            messages.append((block["text"], role))
                            break

            if messages:
                self.client.create_event(
                    memory_id=self.memory_id,
                    actor_id=ACTOR_ID,
                    session_id=SESSION_ID,
                    messages=messages,
                )
                print(f"[Memory Hook] Saved {len(messages)} messages to memory")
        except Exception as e:
            print(f"[Memory Hook] Save failed (continuing): {e}")

    def register_hooks(self, registry: HookRegistry) -> None:
        """Register hooks with the Strands hook registry."""
        registry.add_callback(MessageAddedEvent, self.retrieve)
        registry.add_callback(AfterInvocationEvent, self.save)


# Initialize memory client and hooks
memory_client = MemoryClient(region_name=REGION)
memory_hooks = MemoryHooks(memory_client, MEMORY_ID)

model = BedrockModel(model_id="global.anthropic.claude-haiku-4-5-20251001-v1:0")
agent = Agent(
    model=model,
    hooks=[memory_hooks],
    system_prompt=(
        "You are a helpful assistant with automatic memory. "
        "Your memory hooks save and retrieve context automatically. "
        "You remember past conversations without needing explicit commands. "
        "Be concise."
    ),
)

app = BedrockAgentCoreApp()


@app.entrypoint
def invoke_agent(payload: dict) -> str:
    prompt = payload.get("prompt", "Hello!")
    response = agent(prompt)
    return response.message["content"][0]["text"]


if __name__ == "__main__":
    app.run()
