"""Demo 6: Delete all resources (harness, gateway, guardrail)."""

import json
import os
import sys
import time

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))
from shared.harness_helpers import delete_harness, load_config
from shared.colors import banner, success, info, done

import boto3


def main():
    os.chdir(os.path.dirname(os.path.abspath(__file__)))
    banner("Demo 6: Cleanup")

    if not os.path.exists("runtime_config.json"):
        info("No config found — nothing to clean up.")
        done()
        return

    config = load_config()
    region = config["region"]
    control = boto3.client("bedrock-agentcore-control", region_name=region)
    bedrock = boto3.client("bedrock", region_name=region)

    # Delete harness
    harness_id = config.get("harness_id")
    if harness_id:
        delete_harness(harness_id, region)

    # Delete gateway target + gateway
    gateway_id = config.get("gateway_id")
    target_id = config.get("target_id")
    if gateway_id and target_id:
        try:
            control.delete_gateway_target(gatewayIdentifier=gateway_id, targetId=target_id)
            info(f"  Deleted target: {target_id}")
            time.sleep(10)
        except Exception as e:
            info(f"  Target: {e}")

    if gateway_id:
        try:
            control.delete_gateway(gatewayIdentifier=gateway_id)
            success(f"  Deleted gateway: {gateway_id}")
        except Exception as e:
            info(f"  Gateway: {e}")

    # Delete guardrail
    guardrail_id = config.get("guardrail_id")
    if guardrail_id:
        try:
            bedrock.delete_guardrail(guardrailIdentifier=guardrail_id)
            success(f"  Deleted guardrail: {guardrail_id}")
        except Exception as e:
            info(f"  Guardrail: {e}")

    os.remove("runtime_config.json")
    done()


if __name__ == "__main__":
    main()
