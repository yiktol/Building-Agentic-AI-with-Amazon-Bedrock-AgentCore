"""Demo 1: Local test — verify agent responds before deploying."""

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
            "I prefer Python over Java.",
        ],
    )


if __name__ == "__main__":
    main()
