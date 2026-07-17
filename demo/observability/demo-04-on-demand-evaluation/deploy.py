"""
Demo 4: On-Demand Evaluation — uses Demo 1's deployed runtime.

No additional deployment needed. This demo invokes the agent from Demo 1,
waits for CloudWatch span ingestion, then evaluates the session.

Usage:
    python deploy.py
"""

import os
import sys

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))
from shared.colors import banner, info, done


def main():
    banner("Demo 4: On-Demand Evaluation")
    info("This demo uses the runtime deployed in Demo 1.")
    info("")
    info("Prerequisites:")
    info("  1. Demo 1 deployed and running")
    info("  2. pip install -r requirements.txt")
    info("")
    info("The invoke.py script will:")
    info("  1. Invoke the HR agent for a multi-turn session")
    info("  2. Wait ~90s for CloudWatch span ingestion")
    info("  3. Run on-demand evaluation with built-in evaluators")
    info("  4. Display scores for Helpfulness, Correctness, GoalSuccessRate")
    done("python invoke.py")


if __name__ == "__main__":
    main()
