"""
Demo 2: Long-Term Memory — Strategy Extraction.

This agent demonstrates:
- Creating a memory resource with a semantic strategy
- Writing events that trigger asynchronous extraction
- Retrieving structured memory records via semantic search
- Namespace organization with {actorId} templates
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
        "You are a helpful assistant with long-term memory. "
        "You remember facts about users across conversations."
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
