"""
Demo 1: Local Testing — run MCP server locally and send JSON-RPC requests.

Starts the MCP server on port 8000, sends initialize + tools/list + tools/call.

Usage:
    python local_test.py
"""

import json
import os
import subprocess
import sys
import time
import urllib.request
import urllib.error

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))
from shared.colors import banner, section, success, info, error, config_val, done, GREEN, RESET, BOLD


def wait_for_server(url: str, timeout: int = 30) -> bool:
    """Poll the MCP server with a proper POST initialize request."""
    init_msg = json.dumps({
        "jsonrpc": "2.0", "method": "initialize", "id": 0,
        "params": {"protocolVersion": "2025-03-26", "capabilities": {}, "clientInfo": {"name": "probe", "version": "1.0"}},
    }).encode()
    start = time.time()
    while time.time() - start < timeout:
        try:
            req = urllib.request.Request(
                url, data=init_msg, method="POST",
                headers={"Content-Type": "application/json", "Accept": "application/json"},
            )
            with urllib.request.urlopen(req, timeout=3) as resp:
                if resp.status == 200:
                    return True
        except (urllib.error.URLError, ConnectionRefusedError, OSError):
            time.sleep(1)
    return False


def send_rpc(url: str, method: str, params: dict, rpc_id: int = 1) -> dict:
    msg = json.dumps({"jsonrpc": "2.0", "method": method, "id": rpc_id, "params": params})
    req = urllib.request.Request(
        url, data=msg.encode(),
        headers={"Content-Type": "application/json", "Accept": "application/json"},
        method="POST",
    )
    with urllib.request.urlopen(req, timeout=30) as resp:
        return json.loads(resp.read().decode())


def main():
    os.chdir(os.path.dirname(os.path.abspath(__file__)))
    port = 8000
    mcp_url = f"http://localhost:{port}/mcp"

    banner("Local Testing: MCP Server")
    config_val("Server file", "mcp_server.py")
    config_val("Port", str(port))
    config_val("Endpoint", mcp_url)

    # Start server
    section("Starting MCP server")
    info(f"Running: python mcp_server.py")

    proc = subprocess.Popen(
        [sys.executable, "mcp_server.py"],
        stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL,
    )

    try:
        time.sleep(2)
        if proc.poll() is not None:
            error(f"Server exited with code {proc.returncode}")
            error("Run 'python mcp_server.py' directly to debug")
            sys.exit(1)

        info("Waiting for server to respond...")
        if not wait_for_server(mcp_url, timeout=30):
            error("Server didn't respond within 30s")
            proc.terminate()
            sys.exit(1)
        success(f"MCP server running on port {port}")

        # Initialize
        section("Step 1: initialize")
        result = send_rpc(mcp_url, "initialize", {
            "protocolVersion": "2025-03-26",
            "capabilities": {},
            "clientInfo": {"name": "local-test", "version": "1.0.0"},
        })
        server_info = result.get("result", {}).get("serverInfo", {})
        success(f"Server: {server_info.get('name', '?')}")

        # List tools
        section("Step 2: tools/list")
        result = send_rpc(mcp_url, "tools/list", {}, rpc_id=2)
        tools = result.get("result", {}).get("tools", [])
        for t in tools:
            print(f"    {GREEN}●{RESET} {BOLD}{t['name']}{RESET}: {t.get('description', '')}")
        success(f"Found {len(tools)} tools")

        # Call tools
        section("Step 3: tools/call — add_numbers(10, 5)")
        result = send_rpc(mcp_url, "tools/call", {"name": "add_numbers", "arguments": {"a": 10, "b": 5}}, rpc_id=3)
        info(f"Result: {json.dumps(result.get('result', {}))}")
        success("Tool call succeeded")

        section("Step 4: tools/call — greet('World', 'french')")
        result = send_rpc(mcp_url, "tools/call", {"name": "greet", "arguments": {"name": "World", "language": "french"}}, rpc_id=4)
        info(f"Result: {json.dumps(result.get('result', {}))}")
        success("Tool call succeeded")

        done("python deploy.py")
        info("Local test passed — MCP server ready to deploy")

    finally:
        section("Stopping server")
        proc.terminate()
        try:
            proc.wait(timeout=5)
        except subprocess.TimeoutExpired:
            proc.kill()
        success("Server stopped")


if __name__ == "__main__":
    main()
