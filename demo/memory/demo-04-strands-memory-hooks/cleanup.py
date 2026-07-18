"""Demo 4: No cleanup needed — runs locally, resources managed by CloudFormation."""

import sys
import os

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))
from shared.colors import banner, info, done

def main():
    banner("Demo 4: Cleanup")
    info("This demo runs locally — no cloud resources to clean up.")
    info("Memory resource is managed by the CloudFormation stack.")
    info("To delete everything: cd cloudformation && ./cleanup-stack.sh")
    done()

if __name__ == "__main__":
    main()
