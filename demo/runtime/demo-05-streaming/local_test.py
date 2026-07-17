"""
Demo 5: Local Testing — run the streaming agent on localhost before deploying.

Note: Local testing uses standard HTTP (non-streaming). SSE streaming
is demonstrated after deployment via invoke.py.

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
            "What is the weather in Tokyo?",
            "Calculate 3.14 * 100",
        ],
    )


if __name__ == "__main__":
    main()
