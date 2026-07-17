"""Demo 4: Clean up all resources."""

import os
import sys

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))
from shared.deploy_helpers import cleanup_all
from shared.colors import banner, done


def main():
    os.chdir(os.path.dirname(os.path.abspath(__file__)))
    banner("Demo 4: Cleanup")
    cleanup_all()
    done()


if __name__ == "__main__":
    main()
