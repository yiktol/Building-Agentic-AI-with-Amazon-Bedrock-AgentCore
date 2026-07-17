"""Demo 5: Cleanup runtime (workload identity is auto-deleted)."""

import os
import sys

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))
from shared.deploy_helpers import cleanup_runtime
from shared.colors import banner, info, done


def main():
    os.chdir(os.path.dirname(os.path.abspath(__file__)))
    banner("Demo 5: Cleanup")
    cleanup_runtime()
    info("Workload identity is automatically deleted with the runtime")
    done()


if __name__ == "__main__":
    main()
