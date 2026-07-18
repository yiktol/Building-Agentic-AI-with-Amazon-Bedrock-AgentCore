"""
Demo 3: Memory as Tool — verify resources from CloudFormation stack.

This demo runs LOCALLY (no runtime deployment needed). The local agent
uses the Memory SDK directly for immediate save/recall.

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

    banner("Demo 3: Strands Agent — Memory as Tool")
    config_val("Region", cfg["region"])
    config_val("Memory ID (UserPref)", cfg["memory_user_pref_id"])

    step_header(1, 1, "Verifying memory resource from CloudFormation")
    info("Memory resource created by: cloudformation/prerequisites.yaml")
    info("This demo runs LOCALLY — no runtime deployment needed")

    import boto3
    control = boto3.client("bedrock-agentcore-control", region_name=cfg["region"])
    resp = control.get_memory(memoryId=cfg["memory_user_pref_id"])
    status = resp["memory"]["status"]

    if status == "ACTIVE":
        success(f"Memory is ACTIVE: {cfg['memory_user_pref_id']}")
    else:
        info(f"Memory status: {status} (waiting...)")

    done("python invoke.py")
    info("Or for interactive chatbot: python invoke_agent.py")
    print()

if __name__ == "__main__":
    main()
