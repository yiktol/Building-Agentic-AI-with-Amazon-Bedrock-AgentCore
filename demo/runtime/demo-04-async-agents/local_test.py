"""
Demo 4: Local Testing — run the async agent on localhost before deploying.

Tests both synchronous (quick_summary) and asynchronous (generate_report) tools.

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
            "Give me a quick summary about cloud computing.",
            "Generate a detailed report about AI trends. Make it take 5 seconds.",
        ],
    )


if __name__ == "__main__":
    main()
