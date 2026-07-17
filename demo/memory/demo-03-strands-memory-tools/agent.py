"""
Demo 3: Strands Agent with Memory as Tool.

This agent demonstrates:
- AgentCoreMemoryToolProvider gives the agent explicit memory read/write tools
- The LLM decides WHEN to recall/save information
- Memory operations exposed as tools the agent invokes deliberately

The memory_id, actor_id, session_id, and namespace are injected via
environment variables at deploy time.
"""

import os

from bedrock_agentcore.runtime import BedrockAgentCoreApp
from strands import Agent
from strands.models.bedrock import BedrockModel
from strands_tools.agent_core_memory import AgentCoreMemoryToolProvider

# Configuration from environment (set by deploy.py)
MEMORY_ID = os.environ["MEMORY_ID"]
ACTOR_ID = os.environ.get("ACTOR_ID", "user-42")
SESSION_ID = os.environ.get("SESSION_ID", "session-1")
NAMESPACE = os.environ.get("MEMORY_NAMESPACE", f"/users/{ACTOR_ID}")
REGION = os.environ.get("AWS_REGION", "us-east-1")

# Memory tool provider — gives the agent read/write memory tools
memory_provider = AgentCoreMemoryToolProvider(
    memory_id=MEMORY_ID,
    actor_id=ACTOR_ID,
    session_id=SESSION_ID,
    namespace=NAMESPACE,
    region=REGION,
)

model = BedrockModel(model_id="global.anthropic.claude-haiku-4-5-20251001-v1:0")
agent = Agent(
    model=model,
    tools=memory_provider.tools,
    system_prompt=(
        "You are a helpful assistant with persistent memory. "
        "Use your memory tools to save important user preferences and facts. "
        "When users ask about previous conversations, use memory to recall. "
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
