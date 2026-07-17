"""
Demo 1: Agent protected by inbound JWT authentication.

The agent code has NO auth logic — protection is at the Runtime level.
"""

from strands import Agent, tool
from strands.models import BedrockModel
from bedrock_agentcore.runtime import BedrockAgentCoreApp

app = BedrockAgentCoreApp()


@tool
def weather(city: str) -> str:
    """Get weather for a city."""
    return {"seattle": "rainy, 55°F", "miami": "sunny, 85°F"}.get(city.lower(), f"sunny in {city}")


@tool
def calculator(expression: str) -> str:
    """Evaluate a math expression."""
    allowed = set("0123456789+-*/.() ")
    if all(c in allowed for c in expression):
        return str(eval(expression))  # noqa: S307
    return "Invalid"


model = BedrockModel(model_id="global.anthropic.claude-haiku-4-5-20251001-v1:0")
agent = Agent(model=model, tools=[calculator, weather],
              system_prompt="You are a helpful assistant. Be concise.")


@app.entrypoint
def invoke_agent(payload):
    response = agent(payload.get("prompt", "Hello!"))
    return response.message["content"][0]["text"]


if __name__ == "__main__":
    app.run()
