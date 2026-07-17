"""Demo 5: Delete policy engine (detach from gateway first)."""

import json
import os
import sys
import time

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))
from shared.colors import banner, success, info, done

import boto3


def main():
    os.chdir(os.path.dirname(os.path.abspath(__file__)))
    banner("Demo 5: Cleanup")
    if not os.path.exists("runtime_config.json"):
        info("No config found")
        return
    with open("runtime_config.json") as f:
        config = json.load(f)

    control = boto3.client("bedrock-agentcore-control", region_name=config["region"])

    # Detach policy engine from gateway
    try:
        control.update_gateway(
            gatewayIdentifier=config["gateway_id"],
            policyEngineConfiguration={"arn": "", "mode": "MONITOR"},
        )
        info("Detached policy engine from gateway")
    except Exception as e:
        info(f"Detach: {e}")

    # Delete policies
    try:
        policies = control.list_policies(policyEngineId=config["policy_engine_id"])
        for p in policies.get("policies", []):
            control.delete_policy(policyEngineId=config["policy_engine_id"], policyId=p["policyId"])
            info(f"Deleted policy: {p.get('name', p['policyId'])}")
    except Exception as e:
        info(f"Policies: {e}")

    # Delete policy engine
    try:
        control.delete_policy_engine(policyEngineId=config["policy_engine_id"])
        success(f"Deleted policy engine: {config['policy_engine_id']}")
    except Exception as e:
        info(f"Engine: {e}")

    os.remove("runtime_config.json")
    done()


if __name__ == "__main__":
    main()
