"""
Demo 3: CloudWatch Dashboard — no deploy needed.

This demo uses the runtime deployed in Demo 1 and walks through
the CloudWatch GenAI Observability dashboard views.

Usage:
    python deploy.py
"""

import os
import sys

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))
from shared.colors import banner, info, done


def main():
    banner("Demo 3: CloudWatch GenAI Observability Dashboard")
    info("This demo is a console walkthrough — no deployment needed.")
    info("")
    info("Prerequisites:")
    info("  1. Run Demo 1: deploy.py + invoke.py (generates traces)")
    info("  2. Wait 2-3 minutes for CloudWatch ingestion")
    info("")
    info("Then run: python invoke.py (queries traces programmatically)")
    info("Or walk through the Console views listed in the README.")
    done("python invoke.py")


if __name__ == "__main__":
    main()
