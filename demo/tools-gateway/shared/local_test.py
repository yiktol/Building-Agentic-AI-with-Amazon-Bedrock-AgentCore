"""
Local testing utility for demo agents.

Starts the agent locally on port 8080 and sends test prompts via HTTP,
simulating how AgentCore Runtime invokes the agent.

Usage (from a demo folder):
    python local_test.py
"""

import json
import os
import subprocess
import sys
import time

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))
from shared.colors import banner, section, success, info, error, config_val, prompt_display, response_display, done, YELLOW, RESET


def wait_for_server(url: str, timeout: int = 60) -> bool:
    """Poll the /ping endpoint until the server is ready."""
    import urllib.request
    import urllib.error

    start = time.time()
    while time.time() - start < timeout:
        try:
            req = urllib.request.Request(url)
            with urllib.request.urlopen(req, timeout=2) as resp:
                if resp.status == 200:
                    return True
        except (urllib.error.URLError, ConnectionRefusedError, OSError):
            time.sleep(1)
    return False


def invoke_local(prompt: str, port: int = 8080) -> str:
    """Send a prompt to the local agent."""
    import urllib.request

    url = f"http://localhost:{port}/invocations"
    payload = json.dumps({"prompt": prompt}).encode("utf-8")

    req = urllib.request.Request(
        url,
        data=payload,
        headers={"Content-Type": "application/json"},
        method="POST",
    )
    with urllib.request.urlopen(req, timeout=120) as resp:
        return resp.read().decode("utf-8")


def run_local_test(agent_file: str = "agent.py", prompts: list = None, port: int = 8080):
    """Start agent locally, send test prompts, then stop.

    Args:
        agent_file: Path to the agent.py file to run.
        prompts: List of test prompts to send.
        port: Port to run the local server on.
    """
    if prompts is None:
        prompts = ["Hello! What can you do?"]

    banner("Local Testing")
    config_val("Agent file", agent_file)
    config_val("Port", str(port))
    config_val("Endpoint", f"http://localhost:{port}/invocations")

    # Start the agent process
    section("Starting local agent server")
    info(f"Running: python {agent_file}")
    info("This simulates how AgentCore Runtime runs your code")

    env = os.environ.copy()
    env["PORT"] = str(port)

    # Don't capture stdout/stderr — let agent logs show in terminal
    # Use DEVNULL to suppress if you prefer silent operation
    proc = subprocess.Popen(
        [sys.executable, agent_file],
        stdout=subprocess.DEVNULL,
        stderr=subprocess.DEVNULL,
        env=env,
    )

    try:
        # Check the process didn't crash immediately
        time.sleep(2)
        if proc.poll() is not None:
            error(f"Agent process exited immediately with code {proc.returncode}")
            error("Run 'python agent.py' directly to see the error")
            sys.exit(1)

        # Wait for the server to be ready
        info("Waiting for /ping to respond (up to 60s)...")
        ping_url = f"http://localhost:{port}/ping"
        if not wait_for_server(ping_url, timeout=60):
            error("Server failed to start within 60 seconds")
            error("Run 'python agent.py' directly to debug")
            proc.terminate()
            sys.exit(1)

        success(f"Agent server running on port {port}")
        success("GET /ping → 200 OK")

        # Send test prompts
        section("Sending test prompts to POST /invocations")
        for i, prompt in enumerate(prompts, 1):
            info(f"[{i}/{len(prompts)}]")
            prompt_display(prompt)
            try:
                response = invoke_local(prompt, port)
                response_display(response)
                success("Response received")
            except Exception as e:
                error(f"Invocation failed: {e}")

        done("python deploy.py")
        info("Local test passed — agent is ready to deploy")

    finally:
        # Stop the server
        section("Stopping local server")
        proc.terminate()
        try:
            proc.wait(timeout=5)
        except subprocess.TimeoutExpired:
            proc.kill()
            proc.wait()
        success("Server stopped")
