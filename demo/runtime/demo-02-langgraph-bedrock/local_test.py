"""
Demo 2: Local Testing — run the LangGraph agent on localhost before deploying.

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
            "What is 25 * 17 + 42?",
            "Calculate sqrt(144)",
        ],
    )


if __name__ == "__main__":
    main()
