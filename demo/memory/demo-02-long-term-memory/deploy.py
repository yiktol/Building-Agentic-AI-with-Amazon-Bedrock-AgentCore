"""
Demo 2: Long-term memory — verify resources from CloudFormation stack.

All AWS resources (memory with semantic strategy, IAM roles) are created
by the CloudFormation template. This script confirms the memory is ACTIVE.

Usage:
    python deploy.py
"""

import os
import sys

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))
from shared.stack_config import get_config
from shared.colors import banner, step_header, success, info, config_val, done


def main():
    os.chdir(os.path.dirname(os.path.abspath(__file__)))
    cfg = get_config()

    banner("Demo 2: Long-Term Memory — Semantic Strategy")
    config_val("Region", cfg["region"])
    config_val("Memory ID (Semantic)", cfg["memory_semantic_id"])

    step_header(1, 1, "Verifying memory resource from CloudFormation")
    info("Memory resource created by: cloudformation/prerequisites.yaml")
    info("Strategy: Semantic → /users/{actorId}/facts/")
    info("Event expiry: 30 days")

    import boto3
    control = boto3.client("bedrock-agentcore-control", region_name=cfg["region"])
    resp = control.get_memory(memoryId=cfg["memory_semantic_id"])
    status = resp["memory"]["status"]

    if status == "ACTIVE":
        success(f"Memory is ACTIVE: {cfg['memory_semantic_id']}")
    else:
        info(f"Memory status: {status} (waiting...)")

    done("python invoke.py")
    print()


if __name__ == "__main__":
    main()
