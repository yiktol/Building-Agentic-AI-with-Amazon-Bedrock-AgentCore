"""Demo 5: No cleanup needed — resources managed by CloudFormation stack."""

import sys
import os

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))
from shared.colors import banner, info, done


def main():
    banner("Demo 5: Cleanup")
    info("All resources are managed by the CloudFormation stack.")
    info("To delete everything: cd cloudformation && ./cleanup-stack.sh")
    done()


if __name__ == "__main__":
    main()
