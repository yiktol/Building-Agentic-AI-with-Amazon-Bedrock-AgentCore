"""
Demo 5: Streaming Agent — Server-Sent Events (SSE) responses.

Demonstrates:
- Real-time token streaming via accept="text/event-stream"
- Same agent code as non-streaming — streaming is a CLIENT-SIDE choice
- Reduced perceived latency for end users
"""

from bedrock_agentcore.runtime import BedrockAgentCoreApp
from strands import Agent, tool
from strands.models.bedrock import BedrockModel


@tool
def get_weather(city: str) -> dict:
    """Get weather for a city.

    Args:
        city: City name.

    Returns:
        Weather data dictionary.
    """
    weather_data = {
        "seattle": {"condition": "rainy", "temp_f": 55, "humidity": 82},
        "miami": {"condition": "sunny", "temp_f": 85, "humidity": 65},
        "tokyo": {"condition": "clear", "temp_f": 68, "humidity": 55},
    }
    return weather_data.get(city.lower(), {"condition": "sunny", "temp_f": 72, "humidity": 50})


@tool
def calculator(expression: str) -> str:
    """Evaluate a math expression.

    Args:
        expression: Math expression string.

    Returns:
        Result string.
    """
    allowed = set("0123456789+-*/.() ")
    if all(c in allowed for c in expression):
        return str(eval(expression))  # noqa: S307
    return "Invalid expression"


model = BedrockModel(model_id="global.anthropic.claude-haiku-4-5-20251001-v1:0")

agent = Agent(
    model=model,
    tools=[get_weather, calculator],
    system_prompt=(
        "You are a helpful assistant. Provide detailed, thorough responses. "
        "When explaining concepts, be comprehensive so the streaming effect "
        "is visible to the user watching tokens appear."
    ),
)

app = BedrockAgentCoreApp()


@app.entrypoint
def invoke_agent(payload: dict) -> str:
    """Same entrypoint as non-streaming — streaming is client-side."""
    prompt = payload.get("prompt", "Hello!")
    response = agent(prompt)
    return response.message["content"][0]["text"]


if __name__ == "__main__":
    app.run()
