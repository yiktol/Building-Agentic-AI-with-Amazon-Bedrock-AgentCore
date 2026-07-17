"""
Demo 3: Session-aware agent — demonstrates microVM session isolation.

This agent uses Strands with conversation history. When invoked with the
same runtimeSessionId, the microVM persists and the agent remembers
previous messages. Different session IDs get completely isolated environments.
"""

from bedrock_agentcore.runtime import BedrockAgentCoreApp
from strands import Agent
from strands.models.bedrock import BedrockModel

model = BedrockModel(model_id="global.anthropic.claude-haiku-4-5-20251001-v1:0")

agent = Agent(
    model=model,
    system_prompt=(
        "You are a helpful assistant with excellent memory. "
        "Remember everything the user tells you across messages. "
        "When asked about previous information, recall it accurately. "
        "Be concise in your responses."
    ),
)

app = BedrockAgentCoreApp()


@app.entrypoint
def invoke_agent(payload: dict) -> str:
    """Handle requests — state is preserved within the same session."""
    prompt = payload.get("prompt", "Hello!")
    print(f"[Session Agent] Received: {prompt}")
    response = agent(prompt)
    return response.message["content"][0]["text"]


if __name__ == "__main__":
    app.run()
