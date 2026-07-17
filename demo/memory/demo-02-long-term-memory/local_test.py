"""Demo 2: Local test — verify agent responds before deploying."""

import os
import sys

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))
from shared.local_test import run_local_test


def main():
    os.chdir(os.path.dirname(os.path.abspath(__file__)))
    run_local_test(
        agent_file="agent.py",
        prompts=[
            "I prefer Python and I'm based in Berlin.",
            "What did I tell you about myself?",
        ],
    )


if __name__ == "__main__":
    main()
