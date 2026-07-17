"""Demo 2: No cleanup needed — runs locally, no cloud resources created."""

import sys
import os

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))
from shared.colors import banner, info, done


def main():
    banner("Demo 2: Cleanup")
    info("This demo runs locally — no cloud resources to clean up.")
    info("Traces in CloudWatch will expire per your retention settings.")
    done()


if __name__ == "__main__":
    main()
