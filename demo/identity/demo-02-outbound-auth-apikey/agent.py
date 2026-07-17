"""
Demo 2: Agent with @requires_api_key for outbound auth.

The API key is retrieved from AgentCore Identity's token vault at runtime.
It never appears in agent code, logs, or LLM context.
"""

from strands import Agent, tool
from strands.models import BedrockModel
from bedrock_agentcore.runtime import BedrockAgentCoreApp
from bedrock_agentcore.identity.auth import requires_api_key

app = BedrockAgentCoreApp()


@requires_api_key(provider_name="demo-apikey-provider", into="api_key")
@tool
def call_external_api(query: str, api_key: str = None) -> str:
    """Call an external API with the securely retrieved key."""
    preview = f"{api_key[:8]}..." if api_key and len(api_key) > 8 else "retrieved"
    return f"API called successfully (key: {preview}). Query: '{query}'"


model = BedrockModel(model_id="global.anthropic.claude-haiku-4-5-20251001-v1:0")
agent = Agent(model=model, tools=[call_external_api],
              system_prompt="You can query external APIs. Use call_external_api when asked.")


@app.entrypoint
def invoke_agent(payload):
    response = agent(payload.get("prompt", "Hello!"))
    return response.message["content"][0]["text"]


if __name__ == "__main__":
    app.run()
