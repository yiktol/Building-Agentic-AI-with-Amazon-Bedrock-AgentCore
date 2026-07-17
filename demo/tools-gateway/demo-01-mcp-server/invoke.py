"""
Demo 1: Invoke the MCP Server — shows JSON-RPC 2.0 protocol.

Demonstrates: initialize → tools/list → tools/call

Usage:
    python invoke.py
"""

import json
import sys
import os

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))
from shared.colors import banner, section, success, info, config_val, done, GREEN, RESET, BOLD

import boto3


def send_mcp_rpc(client, arn: str, method: str, params: dict, rpc_id: int = 1) -> dict:
    """Send MCP JSON-RPC message."""
    msg = {"jsonrpc": "2.0", "method": method, "id": rpc_id, "params": params}
    resp = client.invoke_agent_runtime(
        agentRuntimeArn=arn,
        payload=json.dumps(msg).encode(), contentType="application/json",
        accept="application/json, text/event-stream",
    )
    return json.loads(resp["response"].read().decode())


def main():
    os.chdir(os.path.dirname(os.path.abspath(__file__)))
    with open("runtime_config.json") as f:
        config = json.load(f)

    arn = config["runtime_arn"]
    region = config["region"]
    client = boto3.client("bedrock-agentcore", region_name=region)

    banner("Demo 1: MCP Server — JSON-RPC Protocol")
    config_val("Server", arn)

    # Initialize
    section("Step 1: Initialize MCP session")
    result = send_mcp_rpc(client, arn, "initialize", {
        "protocolVersion": "2025-03-26",
        "capabilities": {},
        "clientInfo": {"name": "demo-client", "version": "1.0.0"},
    })
    server_info = result.get("result", {}).get("serverInfo", {})
    success(f"Server: {server_info.get('name', '?')} v{server_info.get('version', '?')}")

    # List tools
    section("Step 2: tools/list")
    result = send_mcp_rpc(client, arn, "tools/list", {}, rpc_id=2)
    tools = result.get("result", {}).get("tools", [])
    for t in tools:
        print(f"    {GREEN}●{RESET} {BOLD}{t['name']}{RESET}: {t.get('description', '')}")
    success(f"Found {len(tools)} tools")

    # Call tools
    section("Step 3: tools/call — add_numbers(5, 3)")
    result = send_mcp_rpc(client, arn, "tools/call", {"name": "add_numbers", "arguments": {"a": 5, "b": 3}}, rpc_id=3)
    info(f"Result: {json.dumps(result.get('result', {}), indent=2)}")

    section("Step 4: tools/call — get_weather('Tokyo')")
    result = send_mcp_rpc(client, arn, "tools/call", {"name": "get_weather", "arguments": {"city": "Tokyo"}}, rpc_id=4)
    info(f"Result: {json.dumps(result.get('result', {}), indent=2)}")

    section("Step 5: tools/call — greet('Alice', 'spanish')")
    result = send_mcp_rpc(client, arn, "tools/call", {"name": "greet", "arguments": {"name": "Alice", "language": "spanish"}}, rpc_id=5)
    info(f"Result: {json.dumps(result.get('result', {}), indent=2)}")

    done()
    info("Key: MCP uses JSON-RPC 2.0 over streamable-HTTP")
    info("Methods: initialize, tools/list, tools/call")
    print()


if __name__ == "__main__":
    main()
