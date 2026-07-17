"""
Demo 5: Strands Agent with Cedar Policy Enforcement — Interactive Chatbot.

Connects a local Strands agent to the gateway (which has a Cedar policy engine
in ENFORCE mode). The agent can only use tools permitted by the policy.

- PERMITTED: WeatherService___get_weather
- DENIED: OrderService___get_order, CalculatorService___calculate, etc.

The agent will try to use tools based on your questions. When it tries a
denied tool, the gateway returns a policy denial — demonstrating deterministic
access control.

Requires:
    pip install strands-agents mcp-proxy-for-aws

Usage:
    python invoke_agent.py                 # Interactive chatbot loop
    python invoke_agent.py "What is the weather in Seattle?"  # Single prompt
"""

import json
import os
import sys

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))
from shared.colors import (
    banner, section, success, info, error, config_val, done,
    prompt_display, response_display, GREEN, RED, YELLOW, RESET, BOLD, WHITE
)

from strands import Agent
from strands.models import BedrockModel
from strands.tools.mcp import MCPClient
from mcp_proxy_for_aws.client import aws_iam_streamablehttp_client


def run_chatbot(agent):
    """Interactive conversation loop with the policy-enforced agent."""
    print(f"\n{BOLD}{WHITE}  Cedar Policy Chatbot{RESET}")
    print(f"  {YELLOW}Policy: ONLY get_weather is allowed. Other tools will be DENIED.{RESET}")
    print(f"  Try asking about weather (allowed) vs orders or math (denied).")
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
            # Strip <thinking> tags for cleaner output
            import re
            text = re.sub(r"<thinking>.*?</thinking>\s*", "", text, flags=re.DOTALL).strip()
            print(f"  {YELLOW}Agent:{RESET} {text}\n")
        except Exception as e:
            error_msg = str(e)
            if "denied" in error_msg.lower() or "forbidden" in error_msg.lower() or "policy" in error_msg.lower():
                print(f"  {RED}Agent:{RESET} Tool call was DENIED by Cedar policy: {error_msg[:200]}\n")
            else:
                print(f"  {RED}Agent:{RESET} Error: {error_msg[:200]}\n")


def main():
    os.chdir(os.path.dirname(os.path.abspath(__file__)))

    if not os.path.exists("runtime_config.json"):
        error("Run deploy.py first")
        sys.exit(1)

    with open("runtime_config.json") as f:
        config = json.load(f)

    gw_config_path = os.path.join("..", "demo-03-gateway-lambda", "runtime_config.json")
    with open(gw_config_path) as f:
        gw_config = json.load(f)

    gateway_url = gw_config["gateway_url"]
    region = config["region"]

    banner("Demo 5: Strands Agent + Cedar Policy (Interactive)")
    config_val("Gateway", gateway_url)
    config_val("Policy", "ENFORCE → only WeatherService___get_weather permitted")

    # Connect to gateway using SigV4-authenticated MCP client
    mcp_client = MCPClient(
        lambda: aws_iam_streamablehttp_client(
            endpoint=gateway_url,
            aws_region=region,
            aws_service="bedrock-agentcore",
        )
    )

    with mcp_client:
        # Discover available tools (only permitted ones visible)
        tools = mcp_client.list_tools_sync()
        section("Tools visible through policy")
        for t in tools:
            name = getattr(t, "tool_name", None) or getattr(t, "name", None) or str(t)
            print(f"    {GREEN}●{RESET} {name}")
        info(f"Only {len(tools)} tool(s) visible (Cedar filters tools/list)")

        # Create agent
        model = BedrockModel(model_id="apac.amazon.nova-lite-v1:0")
        agent = Agent(
            model=model,
            tools=tools,
            system_prompt=(
                "You are a helpful assistant. Use the available tools to answer questions. "
                "If a tool call is denied or fails due to policy, explain to the user that "
                "the tool is not permitted by the access policy. Be concise."
            ),
        )

        # Single prompt or interactive mode
        if len(sys.argv) > 1:
            prompt = " ".join(sys.argv[1:])
            section("Single prompt mode")
            prompt_display(prompt)
            response = agent(prompt)
            text = response.message["content"][0]["text"]
            # Strip <thinking> tags for cleaner output
            import re
            text = re.sub(r"<thinking>.*?</thinking>\s*", "", text, flags=re.DOTALL).strip()
            response_display(text)
        else:
            run_chatbot(agent)

    done()
    info("Key: Cedar policies provide deterministic, auditable access control")
    info("  • tools/list only shows PERMITTED tools")
    info("  • Denied tool calls get a clear error (not silent failure)")
    info("  • Policy changes take effect immediately — no redeployment")
    print()


if __name__ == "__main__":
    main()
