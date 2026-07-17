"""
Demo 5: Standard agent — workload identity is created automatically on deploy.
"""

from strands import Agent, tool
from strands.models import BedrockModel
from bedrock_agentcore.runtime import BedrockAgentCoreApp

app = BedrockAgentCoreApp()


@tool
def get_weather(city: str) -> str:
    """Get weather."""
    return f"sunny, 72°F in {city}"


model = BedrockModel(model_id="global.anthropic.claude-haiku-4-5-20251001-v1:0")
agent = Agent(model=model, tools=[get_weather], system_prompt="Be concise.")


@app.entrypoint
def invoke_agent(payload):
    response = agent(payload.get("prompt", "Hello!"))
    return response.message["content"][0]["text"]


if __name__ == "__main__":
    app.run()
