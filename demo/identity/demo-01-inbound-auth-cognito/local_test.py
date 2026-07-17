"""
Demo 1: Local Testing — verify agent responds before deploying.

Note: Local test does NOT enforce JWT auth (that's a Runtime-level feature).
It only confirms the agent code works correctly.

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
            "Calculate 10 * 5 + 3",
        ],
    )


if __name__ == "__main__":
    main()
