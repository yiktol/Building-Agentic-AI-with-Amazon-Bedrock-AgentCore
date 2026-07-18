"""
Demo 4: Interactive Agent with Gateway Semantic Search.

Runs a local Strands agent that uses gateway semantic search to find
relevant tools before calling them. Demonstrates how an agent discovers
tools dynamically via natural language search.

Requires: pip install strands-agents mcp-proxy-for-aws

Usage:
    python invoke_agent.py                              # Interactive
    python invoke_agent.py "Show me order ORD-12345"    # Single prompt
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
    """Interactive chatbot connected to gateway tools (discovered via search)."""
    print(f"\n{BOLD}{WHITE}  Gateway Search Agent Chat{RESET}")
    print(f"  Agent discovers tools via semantic search, then uses them.")
    print(f"  Try: weather, orders, math — agent finds the right tool.")
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

    config_path = os.path.join("..", "demo-03-gateway-lambda", "runtime_config.json")
    if not os.path.exists(config_path):
        from shared.colors import error
        error("Deploy Demo 3 first: cd demo-03-gateway-lambda && python deploy.py")
        sys.exit(1)

    with open(config_path) as f:
        config = json.load(f)

    gateway_url = config["gateway_url"]
    region = config["region"]

    banner("Demo 4: Gateway Search Agent (Interactive)")
    config_val("Gateway", gateway_url)
    info("Agent discovers tools via semantic search + calls them")

    mcp_client = MCPClient(
        lambda: aws_iam_streamablehttp_client(
            endpoint=gateway_url,
            aws_region=region,
            aws_service="bedrock-agentcore",
        )
    )

    with mcp_client:
        tools = mcp_client.list_tools_sync()
        section("All Gateway Tools (including search)")
        for t in tools:
            name = getattr(t, "tool_name", None) or getattr(t, "name", None) or str(t)
            print(f"    {GREEN}●{RESET} {name}")
        info(f"{len(tools)} tool(s) available")

        model = BedrockModel(model_id="apac.amazon.nova-lite-v1:0")
        agent = Agent(
            model=model,
            tools=tools,
            system_prompt=(
                "You are a helpful assistant with access to tools via a gateway. "
                "You can get weather, look up orders, and do math. "
                "Use x_amz_bedrock_agentcore_search to find relevant tools when unsure. "
                "Be concise."
            ),
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
