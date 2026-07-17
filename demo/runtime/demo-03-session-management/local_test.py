"""
Demo 3: Local Testing — run the session agent on localhost before deploying.

Note: Local testing does NOT demonstrate session isolation (that requires
AgentCore Runtime's microVM infrastructure). It only verifies the agent
responds correctly to prompts.

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
            "My name is Alice and I live in Seattle.",
            "What is my name?",
        ],
    )


if __name__ == "__main__":
    main()
