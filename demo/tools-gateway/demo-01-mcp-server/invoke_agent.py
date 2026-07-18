"""
Demo 1: Interactive Agent connected to the deployed MCP Server.

Runs a local Strands agent that discovers tools from the deployed MCP server
and uses them interactively. This demonstrates an MCP client talking to
the deployed MCP server.

Requires: pip install strands-agents mcp-proxy-for-aws

Usage:
    python invoke_agent.py                       # Interactive chatbot
    python invoke_agent.py "Add 5 and 3"         # Single prompt
"""

import json
import os
import re
import sys

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))
from shared.colors import (
    banner, section, success, info, config_val, done,
    prompt_display, response_display, GREEN, YELLOW, RED, RESET, BOLD, WHITE
)

from strands import Agent
from strands.models import BedrockModel
from strands.tools.mcp import MCPClient
from mcp_proxy_for_aws.client import aws_iam_streamablehttp_client


def run_chatbot(agent):
    """Interactive chatbot connected to MCP server tools."""
    print(f"\n{BOLD}{WHITE}  MCP Server Chat{RESET}")
    print(f"  Tools: add_numbers, multiply_numbers, get_weather, greet")
    print(f"  Type 'quit' to stop.\n")

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
        from shared.colors import error
        error("runtime_config.json not found. Run deploy.py first.")
        sys.exit(1)

    with open("runtime_config.json") as f:
        config = json.load(f)

    # The MCP server URL is derived from the runtime ARN
    runtime_arn = config["runtime_arn"]
    region = config["region"]

    # Construct the MCP endpoint URL from runtime ARN
    runtime_id = runtime_arn.split("/")[-1]
    mcp_url = f"https://{runtime_id}.runtime.bedrock-agentcore.{region}.amazonaws.com/mcp"

    banner("Demo 1: MCP Server Agent (Interactive)")
    config_val("MCP Server", mcp_url)
    config_val("Region", region)

    # Connect to deployed MCP server via SigV4
    mcp_client = MCPClient(
        lambda: aws_iam_streamablehttp_client(
            endpoint=mcp_url,
            aws_region=region,
            aws_service="bedrock-agentcore",
        )
    )

    with mcp_client:
        tools = mcp_client.list_tools_sync()
        section("Discovered MCP Tools")
        for t in tools:
            name = getattr(t, "tool_name", None) or getattr(t, "name", None) or str(t)
            print(f"    {GREEN}●{RESET} {name}")
        info(f"{len(tools)} tool(s) from MCP server")

        model = BedrockModel(model_id="apac.amazon.nova-lite-v1:0")
        agent = Agent(
            model=model,
            tools=tools,
            system_prompt="You are a helpful assistant with access to math, weather, and greeting tools. Be concise.",
        )

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
