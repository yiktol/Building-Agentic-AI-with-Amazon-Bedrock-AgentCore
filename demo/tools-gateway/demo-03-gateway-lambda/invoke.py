"""
Demo 3: Invoke Gateway — list tools + call tools via MCP JSON-RPC.

The gateway is invoked directly via HTTP POST to its URL (not via boto3).
Uses SigV4 signing for IAM authentication.

Usage:
    python invoke.py
"""

import json
import os
import sys

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))
from shared.colors import banner, section, success, info, config_val, done, GREEN, RESET, BOLD

import boto3
from botocore.auth import SigV4Auth
from botocore.awsrequest import AWSRequest
from botocore.session import Session as BotocoreSession
import urllib.request


def send_gateway_rpc(gateway_url: str, method: str, params: dict, region: str, rpc_id: int = 1) -> dict:
    """Send MCP JSON-RPC to the gateway URL with SigV4 signing."""
    msg = json.dumps({"jsonrpc": "2.0", "method": method, "id": rpc_id, "params": params})

    # Sign the request with SigV4
    session = BotocoreSession()
    credentials = session.get_credentials().get_frozen_credentials()

    request = AWSRequest(
        method="POST",
        url=gateway_url,
        data=msg,
        headers={"Content-Type": "application/json", "Accept": "application/json"},
    )
    SigV4Auth(credentials, "bedrock-agentcore", region).add_auth(request)

    # Send the signed request
    req = urllib.request.Request(
        gateway_url,
        data=msg.encode(),
        headers=dict(request.headers),
        method="POST",
    )
    with urllib.request.urlopen(req, timeout=30) as resp:
        return json.loads(resp.read().decode())


def main():
    os.chdir(os.path.dirname(os.path.abspath(__file__)))
    with open("runtime_config.json") as f:
        config = json.load(f)

    gateway_url = config["gateway_url"]
    region = config["region"]

    banner("Demo 3: Gateway — List & Invoke Tools")
    config_val("Gateway", gateway_url)

    # List tools
    section("tools/list — all tools across all targets")
    result = send_gateway_rpc(gateway_url, "tools/list", {}, region)
    tools = result.get("result", {}).get("tools", [])
    for t in tools:
        print(f"    {GREEN}●{RESET} {BOLD}{t['name']}{RESET}: {t.get('description', '')}")
    success(f"Total: {len(tools)} tools from 3 Lambda targets")

    # Call tools
    section("tools/call — OrderService___get_order")
    result = send_gateway_rpc(gateway_url, "tools/call",
        {"name": "OrderService___get_order", "arguments": {"orderId": "ORD-12345"}}, region, rpc_id=2)
    content = result.get("result", {}).get("content", [])
    for c in content:
        if c.get("text"):
            info(f"Result: {c['text'][:300]}")

    section("tools/call — WeatherService___get_weather")
    result = send_gateway_rpc(gateway_url, "tools/call",
        {"name": "WeatherService___get_weather", "arguments": {"city": "Tokyo"}}, region, rpc_id=3)
    content = result.get("result", {}).get("content", [])
    for c in content:
        if c.get("text"):
            info(f"Result: {c['text'][:300]}")

    section("tools/call — CalculatorService___calculate")
    result = send_gateway_rpc(gateway_url, "tools/call",
        {"name": "CalculatorService___calculate", "arguments": {"expression": "25 * 17 + 42"}}, region, rpc_id=4)
    content = result.get("result", {}).get("content", [])
    for c in content:
        if c.get("text"):
            info(f"Result: {c['text'][:300]}")

    done()
    info("Key: Gateway aggregates tools from multiple Lambda targets")
    info("Tool names: <TargetName>___<tool_name>")
    print()


if __name__ == "__main__":
    main()
