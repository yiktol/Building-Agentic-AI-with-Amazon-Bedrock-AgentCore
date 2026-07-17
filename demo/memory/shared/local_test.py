"""
Shared local testing utility for Module 05 Memory demos.

Starts the agent locally on port 8080, sends test prompts, and prints responses.

Usage:
    from shared.local_test import run_local_test
    run_local_test(agent_file="agent.py", prompts=["Hello!"])
"""

import json
import subprocess
import sys
import time
import urllib.request

sys.path.insert(0, __file__.rsplit("/", 1)[0])
from colors import banner, section, success, info, error, prompt_display, response_display, done


def run_local_test(agent_file: str = "agent.py", prompts: list = None, port: int = 8080):
    """Start agent locally and send test prompts."""
    if prompts is None:
        prompts = ["Hello!"]

    banner("Local Test")
    info(f"Starting {agent_file} on port {port}...")

    # Start agent process
    proc = subprocess.Popen(
        [sys.executable, agent_file],
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
    )

    # Wait for server to be ready
    url = f"http://localhost:{port}"
    for _ in range(30):
        try:
            urllib.request.urlopen(f"{url}/ping", timeout=1)
            success(f"Agent running at {url}")
            break
        except Exception:
            time.sleep(1)
    else:
        error("Agent failed to start within 30 seconds")
        proc.terminate()
        sys.exit(1)

    # Send prompts
    try:
        for i, prompt in enumerate(prompts, 1):
            section(f"Prompt {i}/{len(prompts)}")
            prompt_display(prompt)

            req = urllib.request.Request(
                f"{url}/invocations",
                data=json.dumps({"prompt": prompt}).encode(),
                headers={"Content-Type": "application/json"},
            )
            resp = urllib.request.urlopen(req, timeout=60)
            body = resp.read().decode()
            response_display(body)

        done()
    finally:
        proc.terminate()
        proc.wait()
