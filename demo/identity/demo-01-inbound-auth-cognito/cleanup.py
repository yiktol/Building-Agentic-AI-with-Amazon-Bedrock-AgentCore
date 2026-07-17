"""Demo 1: Clean up AgentCore Runtime (CFN resources remain)."""

import os
import sys

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))
from shared.deploy_helpers import cleanup_runtime
from shared.colors import banner, done


def main():
    os.chdir(os.path.dirname(os.path.abspath(__file__)))
    banner("Demo 1: Cleanup")
    cleanup_runtime()
    done()


if __name__ == "__main__":
    main()
