"""
Demo 4: Local Testing — verify agent responds before deploying.

Note: OAuth decorators need AgentCore Identity at runtime.
Local test verifies the agent structure and tool definitions.

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
            "Query the internal API for team status.",
        ],
    )


if __name__ == "__main__":
    main()
