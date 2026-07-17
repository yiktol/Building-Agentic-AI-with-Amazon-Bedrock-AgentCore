"""
Demo 5: Create a Cedar Policy Engine + attach to gateway.

Requires Demo 3's gateway to be deployed first.

Usage:
    python deploy.py
"""

import json
import os
import sys
import time

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))
from shared.colors import banner, step_header, section, success, info, error, config_val, done

import boto3


def main():
    os.chdir(os.path.dirname(os.path.abspath(__file__)))

    # Use Demo 3's gateway config
    gw_config_path = os.path.join("..", "demo-03-gateway-lambda", "runtime_config.json")
    if not os.path.exists(gw_config_path):
        error("Deploy Demo 3 first: cd demo-03-gateway-lambda && python deploy.py")
        sys.exit(1)

    with open(gw_config_path) as f:
        gw_config = json.load(f)

    region = gw_config["region"]
    gateway_id = gw_config["gateway_id"]
    gateway_arn = f"arn:aws:bedrock-agentcore:{region}:{boto3.client('sts').get_caller_identity()['Account']}:gateway/{gateway_id}"

    control = boto3.client("bedrock-agentcore-control", region_name=region)

    banner("Demo 5: Cedar Policy Engine")
    config_val("Gateway", gw_config["gateway_url"])
    config_val("Region", region)

    # Step 1: Create policy engine
    step_header(1, 3, "Creating Cedar Policy Engine")
    info("type: CEDAR | mode: ENFORCE (default-deny)")

    pe_resp = control.create_policy_engine(name="demo05-policy-engine", type="CEDAR")
    pe_id = pe_resp["policyEngineId"]
    pe_arn = pe_resp["policyEngineArn"]
    info(f"Policy Engine ID: {pe_id}")

    info("Waiting for ACTIVE...")
    while True:
        pe = control.get_policy_engine(policyEngineId=pe_id)
        if pe.get("status") == "ACTIVE":
            break
        time.sleep(10)
    success("Policy Engine ACTIVE")

    # Step 2: Attach to gateway
    step_header(2, 3, "Attaching policy engine to gateway")
    info("mode: ENFORCE → default-deny (only permitted tools are accessible)")

    control.update_gateway(
        gatewayIdentifier=gateway_id,
        policyEngineConfiguration={"arn": pe_arn, "mode": "ENFORCE"},
    )
    success("Policy engine attached in ENFORCE mode")
    info("All tool calls are now BLOCKED until a permit policy is added")

    # Step 3: Create a permit policy
    step_header(3, 3, "Creating Cedar permit policy")

    cedar_statement = f"""permit(
  principal,
  action == AgentCore::Action::"WeatherService___get_weather",
  resource == AgentCore::gateway::"{gateway_arn}"
);"""

    info("Policy: Allow ONLY the get_weather tool")
    print(f"\n    {cedar_statement}\n")

    control.create_policy(
        policyEngineId=pe_id,
        name="allow-weather-only",
        definition={"cedar": {"statement": cedar_statement}},
    )
    success("Policy created: allow-weather-only")
    info("Now: get_weather → ALLOWED, all other tools → DENIED")

    # Save config
    state = {
        "policy_engine_id": pe_id,
        "policy_engine_arn": pe_arn,
        "gateway_id": gateway_id,
        "region": region,
    }
    with open("runtime_config.json", "w") as f:
        json.dump(state, f, indent=2)

    done("python invoke.py")
    print()


if __name__ == "__main__":
    main()
