"""
Demo 4: Gateway Semantic Search — find tools by natural language.

Requires Demo 3's gateway to be deployed first.

Usage:
    python invoke.py
"""

import json
import os
import sys

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))
from shared.colors import banner, section, success, info, config_val, done, GREEN, YELLOW, RESET, BOLD

from botocore.auth import SigV4Auth
from botocore.awsrequest import AWSRequest
from botocore.session import Session as BotocoreSession
import urllib.request


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

    config_path = os.path.join("..", "demo-03-gateway-lambda", "runtime_config.json")
    if not os.path.exists(config_path):
        from shared.colors import error
        error("Deploy Demo 3 first: cd demo-03-gateway-lambda && python deploy.py")
        sys.exit(1)

    with open(config_path) as f:
        config = json.load(f)

    gateway_url = config["gateway_url"]
    region = config["region"]

    banner("Demo 4: Gateway Semantic Search")
    config_val("Gateway", gateway_url)

    # Show all tools first
    section("Comparison: tools/list returns ALL tools")
    result = send_gateway_rpc(gateway_url, "tools/list", {}, region)
    tools = result.get("result", {}).get("tools", [])
    info(f"tools/list returns {len(tools)} tools (all of them)")
    for t in tools:
        print(f"    {YELLOW}○{RESET} {t['name']}")

    # Search
    queries = ["find order information", "weather forecast", "do math calculation"]

    import time
    for query in queries:
        time.sleep(2)  # Avoid rate limiting
        section(f"Search: \"{query}\"")
        info("Uses x_amz_bedrock_agentcore_search (built-in)")
        result = send_gateway_rpc(gateway_url, "tools/call", {
            "name": "x_amz_bedrock_agentcore_search",
            "arguments": {"query": query},
        }, region, rpc_id=hash(query) % 1000)

        err = result.get("error", {})
        if err:
            info(f"Search unavailable: {err.get('message', str(err))[:200]}")
            info("(Search may need more tools to index, or isn't available yet)")
            continue

        content = result.get("result", {}).get("content", [])
        if content:
            for c in content:
                text = c.get("text", "")
                if text:
                    try:
                        matches = json.loads(text)
                        if isinstance(matches, list):
                            for m in matches:
                                print(f"    {GREEN}●{RESET} {BOLD}{m.get('name', '?')}{RESET}: {m.get('description', '')}")
                        else:
                            print(f"    {text[:200]}")
                    except json.JSONDecodeError:
                        print(f"    {text[:200]}")
            success("Search returned relevant tools")
        else:
            info(f"Raw: {json.dumps(result.get('result', {}))[:200]}")

    done()
    info("Key: Semantic search finds relevant tools without listing all")
    print()


if __name__ == "__main__":
    main()
