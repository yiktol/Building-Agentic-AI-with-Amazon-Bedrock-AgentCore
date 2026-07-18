"""
Demo 6: Weather Agent — Capstone (Harness + Gateway + Guardrails + Observability + Evaluations).

Creates all resources:
  1. Gateway with Exa MCP target (real-time weather search)
  2. Harness (managed agent loop)
  3. Bedrock Guardrail (PII anonymization)

This is a capstone demo showing 6 AgentCore features in one agent.

Usage:
    python deploy.py
"""

import json
import os
import sys
import time
import uuid

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))
from shared.stack_config import get_config
from shared.harness_helpers import create_harness, get_harness_status, save_config
from shared.colors import banner, step_header, success, info, error, config_val, done

import boto3

CONFIG_FILE = "runtime_config.json"


def check_existing(region):
    """Check if resources from a previous run still exist."""
    if not os.path.exists(CONFIG_FILE):
        return None
    with open(CONFIG_FILE) as f:
        config = json.load(f)
    harness_id = config.get("harness_id")
    if not harness_id:
        return None
    status = get_harness_status(harness_id, region)
    if status == "READY":
        return config
    return None


def main():
    os.chdir(os.path.dirname(os.path.abspath(__file__)))
    cfg = get_config()
    region = cfg["region"]
    role_arn = cfg["harness_role_arn"]

    banner("Demo 6: Weather Agent — Capstone")
    config_val("Region", region)

    # Check existing
    existing = check_existing(region)
    if existing:
        success(f"Already deployed: {existing['harness_id']}")
        config_val("Harness ARN", existing["harness_arn"])
        config_val("Gateway", existing.get("gateway_id", "N/A"))
        done("python invoke.py")
        return

    control = boto3.client("bedrock-agentcore-control", region_name=region)
    bedrock = boto3.client("bedrock", region_name=region)

    # Step 1: Create Gateway with Exa MCP target
    step_header(1, 3, "Creating Gateway + Exa MCP target")
    info("Gateway proxies tool traffic → centralized observability")

    gateway_name = f"weather-gw-{uuid.uuid4().hex[:6]}"
    resp = control.create_gateway(
        name=gateway_name,
        roleArn=role_arn,
        protocolType="MCP",
        authorizerType="NONE",
    )
    gateway_id = resp["gatewayId"]
    gateway_arn = resp["gatewayArn"]
    info(f"Gateway ID: {gateway_id}")

    # Wait for READY
    for _ in range(24):
        gw = control.get_gateway(gatewayIdentifier=gateway_id)
        if gw.get("status") == "READY":
            break
        time.sleep(5)
    success("Gateway READY")

    # Attach Exa MCP target (real-time web search)
    resp = control.create_gateway_target(
        gatewayIdentifier=gateway_id,
        name="exa-weather-search",
        targetConfiguration={"mcp": {"mcpServer": {"endpoint": "https://mcp.exa.ai/mcp"}}},
    )
    target_id = resp["targetId"]
    info(f"Target: Exa MCP (real-time weather search)")

    for _ in range(24):
        t = control.get_gateway_target(gatewayIdentifier=gateway_id, targetId=target_id)
        if t.get("status") == "READY":
            break
        time.sleep(5)
    success("Exa MCP target READY")

    # Step 2: Create Harness
    step_header(2, 3, "Creating Harness (managed agent loop)")
    info("Zero code — declare model at invoke time")

    harness = create_harness(f"WeatherAgent_{uuid.uuid4().hex[:6]}", role_arn, region)
    success(f"Harness READY: {harness['harness_id']}")

    # Step 3: Create Guardrail (PII anonymization)
    step_header(3, 3, "Creating Bedrock Guardrail (PII anonymization)")
    info("Anonymizes: email, phone, SSN, credit card, address")

    gr_resp = bedrock.create_guardrail(
        name=f"weather-pii-{uuid.uuid4().hex[:6]}",
        description="Anonymize PII in weather agent responses",
        sensitiveInformationPolicyConfig={
            "piiEntitiesConfig": [
                {"type": "EMAIL", "action": "ANONYMIZE"},
                {"type": "PHONE", "action": "ANONYMIZE"},
                {"type": "US_SOCIAL_SECURITY_NUMBER", "action": "ANONYMIZE"},
                {"type": "CREDIT_DEBIT_CARD_NUMBER", "action": "ANONYMIZE"},
                {"type": "ADDRESS", "action": "ANONYMIZE"},
            ]
        },
        blockedInputMessaging="Your message contains restricted content.",
        blockedOutputsMessaging="The response contains restricted content.",
    )
    guardrail_id = gr_resp["guardrailId"]
    bedrock.create_guardrail_version(guardrailIdentifier=guardrail_id, description="v1")
    success(f"Guardrail created: {guardrail_id}")

    # Save config
    save_config({
        "harness_id": harness["harness_id"],
        "harness_arn": harness["harness_arn"],
        "gateway_id": gateway_id,
        "gateway_arn": gateway_arn,
        "target_id": target_id,
        "guardrail_id": guardrail_id,
        "region": region,
    }, CONFIG_FILE)

    done("python invoke.py")
    info("")
    info("Features integrated:")
    info("  1. Harness — managed agent loop (zero code)")
    info("  2. Gateway — centralized MCP tool routing")
    info("  3. Guardrails — PII anonymization")
    info("  4. Observability — CloudWatch X-Ray traces")
    info("  5. Evaluations — batch scoring (in invoke.py)")
    info("  6. Multi-turn sessions — persistent state")
    print()


if __name__ == "__main__":
    main()
