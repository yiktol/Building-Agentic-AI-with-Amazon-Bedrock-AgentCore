"""
Demo 2: Local Testing — verify agent responds before deploying.

Note: @requires_api_key needs AgentCore Identity at runtime.
Local test verifies the agent structure and tool definitions work.

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
            "Look up the latest news about AI.",
        ],
    )


if __name__ == "__main__":
    main()
