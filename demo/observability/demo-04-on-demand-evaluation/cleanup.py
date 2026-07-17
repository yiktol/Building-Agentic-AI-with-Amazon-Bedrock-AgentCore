"""Demo 4: No cleanup needed — uses Demo 1's runtime."""

import sys
import os

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))
from shared.colors import banner, info, done


def main():
    banner("Demo 4: Cleanup")
    info("No resources to clean up — uses Demo 1's runtime.")
    info("Clean up Demo 1 when done with all demos.")
    done()


if __name__ == "__main__":
    main()
