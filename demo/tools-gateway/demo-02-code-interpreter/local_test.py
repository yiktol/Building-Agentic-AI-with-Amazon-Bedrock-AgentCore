"""
Demo 2: Local Testing — run the Code Interpreter agent locally.

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
            "What is 2 to the power of 10?",
        ],
    )


if __name__ == "__main__":
    main()
