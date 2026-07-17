"""Demo 3: Delete gateway and targets."""

import json
import os
import sys
import time

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))
from shared.colors import banner, success, info, done

import boto3


def main():
    os.chdir(os.path.dirname(os.path.abspath(__file__)))
    banner("Demo 3: Cleanup")
    if not os.path.exists("runtime_config.json"):
        info("No config found")
        return
    with open("runtime_config.json") as f:
        config = json.load(f)

    control = boto3.client("bedrock-agentcore-control", region_name=config["region"])

    # Delete targets first
    try:
        targets = control.list_gateway_targets(gatewayIdentifier=config["gateway_id"])
        for t in targets.get("items", []):
            control.delete_gateway_target(gatewayIdentifier=config["gateway_id"], targetId=t["targetId"])
            info(f"Deleted target: {t.get('name', t['targetId'])}")
        if targets.get("items"):
            time.sleep(10)
    except Exception as e:
        info(f"Targets: {e}")

    # Delete gateway
    try:
        control.delete_gateway(gatewayIdentifier=config["gateway_id"])
        success(f"Deleted gateway: {config['gateway_id']}")
    except Exception as e:
        info(f"Gateway: {e}")

    os.remove("runtime_config.json")
    done()


if __name__ == "__main__":
    main()
