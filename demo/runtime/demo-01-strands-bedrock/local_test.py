"""
Demo 1: Local Testing — run the agent on localhost before deploying.

Starts the agent on port 8080, sends test prompts via HTTP,
and verifies the /invocations + /ping contract works.

Usage:
    python local_test.py
"""

import os
import sys

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))
from shared.local_test import run_local_test


def main():
    os.chdir(os.path.dirname(os.path.abspath(__file__)))
    run_local_test(
        agent_file="agent.py",
        prompts=[
            "What is the weather in Seattle?",
            "Calculate 25 * 17 + 42",
        ],
    )


if __name__ == "__main__":
    main()
