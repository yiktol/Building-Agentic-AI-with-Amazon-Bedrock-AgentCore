"""
Demo 3: Strands Agent with Gateway Tools — Interactive Chatbot.

Connects a local Strands agent to the AgentCore Gateway via MCP
(using mcp-proxy-for-aws). The agent discovers and uses gateway tools:
  - get_order, list_orders (OrderService)
  - get_weather (WeatherService)
  - calculate (CalculatorService)

Requires:
    pip install strands-agents strands-agents-tools mcp-proxy-for-aws

Usage:
    python invoke_agent.py                          # Interactive chatbot
    python invoke_agent.py "What's the weather in Tokyo?"  # Single prompt
"""

import json
import os
import re
import sys

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))
from shared.colors import (
    banner, section, success, info, error, config_val, done,
    prompt_display, response_display, GREEN, YELLOW, RED, RESET, BOLD, WHITE
)

from strands import Agent
from strands.models import BedrockModel
from strands.tools.mcp import MCPClient
from mcp_proxy_for_aws.client import aws_iam_streamablehttp_client


def run_chatbot(agent):
    """Interactive conversation loop with the gateway-connected agent."""
    print(f"\n{BOLD}{WHITE}  Gateway Agent Chat{RESET}")
    print(f"  Tools: get_order, list_orders, get_weather, calculate")
    print(f"  Type 'quit' or 'exit' to stop.\n")

    while True:
        try:
            user_input = input(f"  {GREEN}You:{RESET} ")
        except (EOFError, KeyboardInterrupt):
            print()
            break

        if user_input.strip().lower() in ("quit", "exit", "q"):
            break

        if not user_input.strip():
            continue

        try:
            response = agent(user_input)
            text = response.message["content"][0]["text"]
            text = re.sub(r"<thinking>.*?</thinking>\s*", "", text, flags=re.DOTALL).strip()
            print(f"  {YELLOW}Agent:{RESET} {text}\n")
        except Exception as e:
            print(f"  {RED}Error:{RESET} {str(e)[:200]}\n")


def main():
    os.chdir(os.path.dirname(os.path.abspath(__file__)))

    if not os.path.exists("runtime_config.json"):
        error("runtime_config.json not found. Run deploy.py first.")
        sys.exit(1)

    with open("runtime_config.json") as f:
        config = json.load(f)

    gateway_url = config["gateway_url"]
    region = config["region"]

    banner("Demo 3: Gateway Agent (Interactive)")
    config_val("Gateway", gateway_url)
    config_val("Region", region)

    # Connect to gateway using SigV4-authenticated MCP client
    mcp_client = MCPClient(
        lambda: aws_iam_streamablehttp_client(
            endpoint=gateway_url,
            aws_region=region,
            aws_service="bedrock-agentcore",
        )
    )

    with mcp_client:
        # Discover available tools
        tools = mcp_client.list_tools_sync()
        section("Discovered Gateway Tools")
        for t in tools:
            name = getattr(t, "tool_name", None) or getattr(t, "name", None) or str(t)
            print(f"    {GREEN}\u25cf{RESET} {name}")
        info(f"{len(tools)} tool(s) available")

        # Create agent
        model = BedrockModel(model_id="apac.amazon.nova-lite-v1:0")
        agent = Agent(
            model=model,
            tools=tools,
            system_prompt=(
                "You are a helpful assistant with access to order management, weather, "
                "and calculator tools. Use the appropriate tool to answer questions. "
                "Be concise and helpful."
            ),
        )

        # Single prompt or interactive mode
        if len(sys.argv) > 1:
            prompt = " ".join(sys.argv[1:])
            section("Single prompt mode")
            prompt_display(prompt)
            response = agent(prompt)
            text = response.message["content"][0]["text"]
            text = re.sub(r"<thinking>.*?</thinking>\s*", "", text, flags=re.DOTALL).strip()
            response_display(text)
        else:
            run_chatbot(agent)

    done()


if __name__ == "__main__":
    main()
