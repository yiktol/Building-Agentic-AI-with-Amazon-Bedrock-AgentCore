"""
Demo 3: Strands Agent connected to the Gateway via MCP.

The agent discovers tools from the gateway at runtime and uses them
to answer natural language questions.

Usage:
    python invoke_agent.py
    python invoke_agent.py "What is the weather in Miami?"
"""

import json
import os
import sys

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))
from shared.colors import banner, section, success, info, config_val, prompt_display, response_display, done

from strands import Agent
from strands.models import BedrockModel
from strands.tools.mcp import MCPClient
from mcp.client.streamable_http import streamablehttp_client
from botocore.auth import SigV4Auth
from botocore.awsrequest import AWSRequest
from botocore.session import Session as BotocoreSession


class SigV4StreamableHTTP:
    """Wrapper that adds SigV4 signing to the MCP streamable-HTTP client."""

    def __init__(self, gateway_url: str, region: str):
        self.gateway_url = gateway_url
        self.region = region

    def get_headers(self) -> dict:
        """Generate SigV4 signed headers for the gateway."""
        session = BotocoreSession()
        credentials = session.get_credentials().get_frozen_credentials()
        request = AWSRequest(
            method="POST", url=self.gateway_url, data="",
            headers={"Content-Type": "application/json", "Accept": "application/json"},
        )
        SigV4Auth(credentials, "bedrock-agentcore", self.region).add_auth(request)
        return dict(request.headers)


def main():
    os.chdir(os.path.dirname(os.path.abspath(__file__)))
    with open("runtime_config.json") as f:
        config = json.load(f)

    gateway_url = config["gateway_url"]
    region = config["region"]

    if len(sys.argv) > 1:
        prompts = [" ".join(sys.argv[1:])]
    else:
        prompts = [
            "What is the weather in Tokyo?",
            "Calculate 99 * 77 + 15",
            "Show me order ORD-12345",
        ]

    banner("Demo 3: Strands Agent + Gateway MCP Tools")
    config_val("Gateway", gateway_url)
    info("Agent discovers tools from gateway via MCP protocol")

    # Connect to gateway as an MCP client
    sigv4 = SigV4StreamableHTTP(gateway_url, region)
    headers = sigv4.get_headers()

    mcp_client = MCPClient(
        lambda: streamablehttp_client(gateway_url, headers=headers)
    )

    with mcp_client:
        # Get tools from gateway
        tools = mcp_client.list_tools_sync()
        section("Tools discovered from gateway")
        for t in tools:
            name = t.name if hasattr(t, 'name') else str(t)
            info(f"● {name}")
        success(f"Agent has {len(tools)} tools available")

        # Create agent with gateway tools
        model = BedrockModel(model_id="global.anthropic.claude-haiku-4-5-20251001-v1:0")
        agent = Agent(
            model=model,
            tools=tools,
            system_prompt="You are a helpful assistant. Use the available tools to answer questions. Be concise.",
        )

        # Invoke with prompts
        for i, prompt in enumerate(prompts, 1):
            section(f"Prompt {i}/{len(prompts)}")
            prompt_display(prompt)
            response = agent(prompt)
            text = response.message["content"][0]["text"]
            response_display(text)

    done()
    info("Key: Agent discovers and uses gateway tools dynamically")
    info("  • No hardcoded tool definitions in agent code")
    info("  • Gateway handles routing to the correct Lambda")
    print()


if __name__ == "__main__":
    main()
