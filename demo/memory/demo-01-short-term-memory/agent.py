"""
Demo 1: Short-Term Memory — Events and Sessions.

This agent demonstrates:
- Creating a memory resource (short-term only, no strategies)
- Writing conversation events with CreateEvent
- Retrieving events with ListEvents / get_last_k_turns
- Actor and session scoping
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
        Weather information.
    """
    data = {
        "seattle": {"condition": "rainy", "temp_f": 55},
        "miami": {"condition": "sunny", "temp_f": 85},
        "berlin": {"condition": "cloudy", "temp_f": 60},
    }
    return data.get(city.lower(), {"condition": "clear", "temp_f": 72})


model = BedrockModel(model_id="global.anthropic.claude-haiku-4-5-20251001-v1:0")
agent = Agent(
    model=model,
    tools=[get_weather],
    system_prompt=(
        "You are a helpful travel assistant. Be concise. "
        "Remember what users tell you within the conversation."
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
