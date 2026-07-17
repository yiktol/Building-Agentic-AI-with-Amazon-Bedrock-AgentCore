"""
Demo 3: Create AgentCore Gateway + attach Lambda targets.

Creates a gateway, attaches the Lambda functions from CFN as targets,
then makes them available as MCP tools.

Usage:
    python deploy.py
"""

import json
import os
import sys
import time

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))
from shared.stack_config import get_config
from shared.colors import banner, step_header, section, success, info, error, config_val, done

import boto3

GATEWAY_NAME = f"demo03-gateway-{int(time.time()) % 100000}"


def main():
    os.chdir(os.path.dirname(os.path.abspath(__file__)))
    cfg = get_config()

    banner("Demo 3: AgentCore Gateway — Lambda Targets")
    config_val("Gateway", GATEWAY_NAME)
    config_val("Region", cfg["region"])

    control = boto3.client("bedrock-agentcore-control", region_name=cfg["region"])

    # Step 1: Create gateway
    step_header(1, 3, "Creating AgentCore Gateway")
    info("protocolType: MCP | authorizerType: NONE (for demo simplicity)")

    resp = control.create_gateway(
        name=GATEWAY_NAME,
        protocolType="MCP",
        authorizerType="NONE",
        roleArn=cfg["runtime_role_arn"],
        description="Demo 3: Gateway with Lambda tool targets",
    )
    gateway_id = resp["gatewayId"]
    info(f"Gateway ID: {gateway_id}")

    # Wait for READY
    info("Waiting for gateway READY...")
    while True:
        gw = control.get_gateway(gatewayIdentifier=gateway_id)
        status = gw.get("status", "CREATING")
        if status == "READY":
            break
        if "FAILED" in status:
            error(f"Gateway failed: {status}")
            sys.exit(1)
        time.sleep(10)
    gateway_url = gw.get("gatewayUrl", "")
    success(f"Gateway READY: {gateway_url}")

    # Step 2: Attach Lambda targets
    step_header(2, 3, "Attaching Lambda targets")

    targets = [
        {
            "name": "OrderService",
            "lambda_arn": cfg["order_service_arn"],
            "tools": [
                {"name": "get_order", "description": "Get order details by ID",
                 "inputSchema": {"type": "object", "properties": {"orderId": {"type": "string"}}, "required": ["orderId"]}},
                {"name": "list_orders", "description": "List all orders",
                 "inputSchema": {"type": "object", "properties": {}}},
            ],
        },
        {
            "name": "WeatherService",
            "lambda_arn": cfg["weather_service_arn"],
            "tools": [
                {"name": "get_weather", "description": "Get weather for a city",
                 "inputSchema": {"type": "object", "properties": {"city": {"type": "string"}}, "required": ["city"]}},
            ],
        },
        {
            "name": "CalculatorService",
            "lambda_arn": cfg["calculator_service_arn"],
            "tools": [
                {"name": "calculate", "description": "Evaluate a math expression",
                 "inputSchema": {"type": "object", "properties": {"expression": {"type": "string"}}, "required": ["expression"]}},
            ],
        },
    ]

    target_ids = []
    for t in targets:
        info(f"Attaching: {t['name']} → {t['lambda_arn'].split(':')[-1]}")
        resp = control.create_gateway_target(
            gatewayIdentifier=gateway_id,
            name=t["name"],
            targetConfiguration={
                "mcp": {
                    "lambda": {
                        "lambdaArn": t["lambda_arn"],
                        "toolSchema": {
                            "inlinePayload": t["tools"],
                        },
                    }
                }
            },
            credentialProviderConfigurations=[
                {"credentialProviderType": "GATEWAY_IAM_ROLE"}
            ],
            description=f"Lambda target: {t['name']}",
        )
        target_ids.append(resp.get("targetId", t["name"]))
        success(f"  Attached: {t['name']} ({len(t['tools'])} tools)")

    # Wait for targets to be ready
    step_header(3, 3, "Waiting for targets ACTIVE")
    time.sleep(10)
    success("All targets attached")

    # Save config
    state = {
        "gateway_name": GATEWAY_NAME,
        "gateway_id": gateway_id,
        "gateway_url": gateway_url,
        "region": cfg["region"],
        "target_ids": target_ids,
    }
    with open("runtime_config.json", "w") as f:
        json.dump(state, f, indent=2)

    done("python invoke.py")
    config_val("Gateway URL", gateway_url)
    config_val("Tools", "get_order, list_orders, get_weather, calculate")
    print()


if __name__ == "__main__":
    main()
