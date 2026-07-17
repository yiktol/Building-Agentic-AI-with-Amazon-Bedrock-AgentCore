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
        done()
        return

    with open("runtime_config.json") as f:
        config = json.load(f)

    control = boto3.client("bedrock-agentcore-control", region_name=config["region"])
    gateway_id = config["gateway_id"]
    pe_id = config["policy_engine_id"]

    # Detach policy engine from gateway (requires full gateway params)
    try:
        gw = control.get_gateway(gatewayIdentifier=gateway_id)
        # Update without policyEngineConfiguration to detach
        update_params = {
            "gatewayIdentifier": gateway_id,
            "name": gw["name"],
            "roleArn": gw["roleArn"],
            "authorizerType": gw["authorizerType"],
        }
        # Only include protocolType if present
        if "protocolType" in gw:
            update_params["protocolType"] = gw["protocolType"]
        control.update_gateway(**update_params)
        success("Detached policy engine from gateway")
    except Exception as e:
        info(f"Detach: {e}")

    # Delete all policies in the engine
    try:
        policies = control.list_policies(policyEngineId=pe_id)
        for p in policies.get("policies", []):
            control.delete_policy(policyEngineId=pe_id, policyId=p["policyId"])
            info(f"Deleted policy: {p.get('name', p['policyId'])}")
        if policies.get("policies"):
            info("Waiting for policy deletion...")
            time.sleep(10)
    except Exception as e:
        info(f"Policies: {e}")

    # Delete policy engine
    try:
        control.delete_policy_engine(policyEngineId=pe_id)
        success(f"Deleted policy engine: {pe_id}")
    except Exception as e:
        info(f"Engine: {e}")

    os.remove("runtime_config.json")
    done()


if __name__ == "__main__":
    main()
