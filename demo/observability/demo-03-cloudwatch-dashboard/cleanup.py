"""Demo 3: No cleanup needed — console walkthrough only."""

import sys
import os

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))
from shared.colors import banner, info, done


def main():
    banner("Demo 3: Cleanup")
    info("No resources to clean up — this demo queries existing traces.")
    done()


if __name__ == "__main__":
    main()
