"""
Demo 5: Seed memory with events for both actors.

All AWS resources (memory, scoped IAM roles) are created by the
CloudFormation template. This script seeds events for two actors
so the invoke script can demonstrate IAM isolation.

Usage:
    python deploy.py
"""

import os
import sys

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))
from shared.stack_config import get_config
from shared.colors import banner, step_header, success, info, config_val, done

from bedrock_agentcore.memory import MemoryClient


def main():
    os.chdir(os.path.dirname(os.path.abspath(__file__)))
    cfg = get_config()
    memory_id = cfg["memory_semantic_id"]
    region = cfg["region"]

    banner("Demo 5: IAM-Scoped Memory Access")
    config_val("Region", region)
    config_val("Memory ID", memory_id)
    config_val("Role A (user-A)", cfg["scoped_role_a_arn"])
    config_val("Role B (user-B)", cfg["scoped_role_b_arn"])

    step_header(1, 2, "Verifying resources from CloudFormation")
    info("Memory resource: cloudformation/prerequisites.yaml")
    info("Scoped IAM roles: actorId conditions on bedrock-agentcore actions")

    import boto3
    control = boto3.client("bedrock-agentcore-control", region_name=region)
    resp = control.get_memory(memoryId=memory_id)
    status = resp["memory"]["status"]
    if status == "ACTIVE":
        success(f"Memory is ACTIVE: {memory_id}")
    else:
        info(f"Memory status: {status}")

    # Step 2: Seed events for both actors
    step_header(2, 2, "Seeding events for both actors")
    client = MemoryClient(region_name=region)

    client.create_event(
        memory_id=memory_id,
        actor_id="user-A",
        session_id="sess-A",
        messages=[
            ("I'm Alice. I prefer Java and live in New York.", "USER"),
            ("Nice to meet you, Alice!", "ASSISTANT"),
        ],
    )
    success("Created events for user-A (Alice)")

    client.create_event(
        memory_id=memory_id,
        actor_id="user-B",
        session_id="sess-B",
        messages=[
            ("I'm Bob. I prefer Rust and live in Tokyo.", "USER"),
            ("Nice to meet you, Bob!", "ASSISTANT"),
        ],
    )
    success("Created events for user-B (Bob)")

    done("python invoke.py")
    info("IAM policies restrict each scoped role to its own actorId")
    print()


if __name__ == "__main__":
    main()
