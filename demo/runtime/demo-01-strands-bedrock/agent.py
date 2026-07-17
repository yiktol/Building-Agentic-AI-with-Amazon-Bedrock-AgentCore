"""
Demo 1: Strands Agents + Amazon Bedrock on AgentCore Runtime

This agent demonstrates:
- Using the BedrockAgentCoreApp SDK to wrap agent logic
- Defining custom tools with @tool decorator
- Using Amazon Bedrock (Claude) as the LLM
- The /invocations + /ping HTTP contract
"""

from bedrock_agentcore.runtime import BedrockAgentCoreApp
from strands import Agent, tool
from strands.models.bedrock import BedrockModel


# ── Custom Tools ─────────────────────────────────────────────────────────────

@tool
def get_weather(city: str) -> dict:
    """Get current weather information for a city.

    Args:
        city: The city name to get weather for.

    Returns:
        Weather information as a dictionary.
    """
    # Simulated weather data for demo purposes
    weather_data = {
        "seattle": {"condition": "rainy", "temperature_f": 55, "humidity": 82},
        "miami": {"condition": "sunny", "temperature_f": 85, "humidity": 65},
        "new york": {"condition": "cloudy", "temperature_f": 62, "humidity": 70},
        "athens": {"condition": "very sunny", "temperature_f": 90, "humidity": 30},
    }
    data = weather_data.get(city.lower(), {"condition": "sunny", "temperature_f": 72, "humidity": 50})
    data["city"] = city
    return data


@tool
def calculator(expression: str) -> str:
    """Evaluate a mathematical expression.

    Args:
        expression: A math expression (e.g., "2 + 3 * 4", "100 / 5").

    Returns:
        The result as a string.
    """
    allowed = set("0123456789+-*/.() ")
    if all(c in allowed for c in expression):
        return str(eval(expression))  # noqa: S307
    return "Error: Invalid expression"


# ── Agent Configuration ──────────────────────────────────────────────────────

model = BedrockModel(model_id="global.anthropic.claude-haiku-4-5-20251001-v1:0")

agent = Agent(
    model=model,
    tools=[get_weather, calculator],
    system_prompt=(
        "You are a helpful assistant. You can check the weather for cities "
        "and perform mathematical calculations. Be concise in your responses."
    ),
)

# ── AgentCore SDK Wrapper ────────────────────────────────────────────────────

app = BedrockAgentCoreApp()


@app.entrypoint
def invoke_agent(payload: dict) -> str:
    """Handle POST /invocations requests.

    The SDK automatically creates:
      - POST /invocations → this function
      - GET /ping → returns 200 (health check)
    """
    prompt = payload.get("prompt", "Hello!")
    print(f"[Agent] Received prompt: {prompt}")
    response = agent(prompt)
    return response.message["content"][0]["text"]


if __name__ == "__main__":
    # Starts HTTP server on port 8080
    # Test locally: curl -X POST http://localhost:8080/invocations \
    #   -H "Content-Type: application/json" \
    #   -d '{"prompt": "What is the weather in Seattle?"}'
    app.run()
