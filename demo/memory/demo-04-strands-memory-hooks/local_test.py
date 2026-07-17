"""Demo 4: Local test — verify agent responds (hooks require deployed memory)."""

import os
import sys

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))
from shared.local_test import run_local_test


def main():
    os.chdir(os.path.dirname(os.path.abspath(__file__)))
    print("Note: Memory hooks require a deployed memory resource.")
    print("This test only verifies the agent HTTP contract.\n")
    run_local_test(
        agent_file="agent.py",
        prompts=["Hello, who are you?"],
    )


if __name__ == "__main__":
    main()
