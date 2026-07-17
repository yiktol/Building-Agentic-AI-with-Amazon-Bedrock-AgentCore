"""
Demo 5: Test policy enforcement — allowed vs denied tool calls.

Usage:
    python invoke.py
"""

import json
import os
import sys

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))
from shared.colors import banner, section, success, info, error, config_val, done, GREEN, RED, RESET

from botocore.auth import SigV4Auth
from botocore.awsrequest import AWSRequest
from botocore.session import Session as BotocoreSession
import urllib.request
import urllib.error


def send_gateway_rpc(gateway_url: str, method: str, params: dict, region: str, rpc_id: int = 1) -> dict:
    msg = json.dumps({"jsonrpc": "2.0", "method": method, "id": rpc_id, "params": params})
    session = BotocoreSession()
    credentials = session.get_credentials().get_frozen_credentials()
    request = AWSRequest(method="POST", url=gateway_url, data=msg,
                         headers={"Content-Type": "application/json", "Accept": "application/json"})
    SigV4Auth(credentials, "bedrock-agentcore", region).add_auth(request)
    req = urllib.request.Request(gateway_url, data=msg.encode(), headers=dict(request.headers), method="POST")
    try:
        with urllib.request.urlopen(req, timeout=30) as resp:
            return json.loads(resp.read().decode())
    except urllib.error.HTTPError as e:
        body = e.read().decode()
        try:
            return json.loads(body)
        except json.JSONDecodeError:
            return {"error": {"code": e.code, "message": body[:200]}}


def main():
    os.chdir(os.path.dirname(os.path.abspath(__file__)))
    with open("runtime_config.json") as f:
        config = json.load(f)

    # Get gateway URL from demo-03
    gw_config_path = os.path.join("..", "demo-03-gateway-lambda", "runtime_config.json")
    with open(gw_config_path) as f:
        gw_config = json.load(f)

    gateway_url = gw_config["gateway_url"]
    region = config["region"]

    banner("Demo 5: Cedar Policy Enforcement")
    info("Policy: ONLY WeatherService___get_weather is permitted")
    info("All other tools are DENIED (ENFORCE mode = default-deny)")

    # Test 1: Allowed tool
    section("Test 1: Call get_weather (PERMITTED)")
    result = send_gateway_rpc(gateway_url, "tools/call", {
        "name": "WeatherService___get_weather", "arguments": {"city": "Seattle"},
    }, region)
    if "error" not in result:
        content = result.get("result", {}).get("content", [])
        text = content[0].get("text", "") if content else str(result.get("result", {}))
        print(f"    {GREEN}✓ ALLOWED{RESET}: {text[:200]}")
        success("Policy permitted this call")
    else:
        error(f"Unexpected: {result.get('error', {})}")

    # Test 2: Denied tool
    section("Test 2: Call get_order (DENIED)")
    result = send_gateway_rpc(gateway_url, "tools/call", {
        "name": "OrderService___get_order", "arguments": {"orderId": "ORD-12345"},
    }, region, rpc_id=2)
    err = result.get("error", {})
    if err:
        print(f"    {RED}✗ DENIED{RESET}: {err.get('message', str(err))[:200]}")
        success("Policy correctly blocked this call")
    else:
        info(f"Unexpected success: {json.dumps(result.get('result', {}))[:100]}")

    # Test 3: tools/list
    section("Test 3: tools/list (only permitted tools visible)")
    result = send_gateway_rpc(gateway_url, "tools/list", {}, region, rpc_id=3)
    tools = result.get("result", {}).get("tools", [])
    for t in tools:
        print(f"    {GREEN}●{RESET} {t['name']}")
    info(f"Only {len(tools)} tool(s) visible (vs 4+ without policy)")

    done()
    info("Key: Cedar policies = deterministic, auditable access control")
    print()


if __name__ == "__main__":
    main()
