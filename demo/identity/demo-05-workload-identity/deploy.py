"""
Demo 5: Deploy agent and inspect workload identity.

Fully self-contained — uses resources from CloudFormation stack.
Deployment triggers automatic workload identity creation.

Usage:
    python deploy.py
"""

import json
import os
import sys
import time

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))
from shared.stack_config import get_config
from shared.deploy_helpers import build_and_upload, create_runtime
from shared.colors import banner, step_header, section, success, info, config_val, done, GREEN, MAGENTA, BOLD, WHITE, YELLOW, RESET

import boto3

AGENT_NAME = f"demo05_workload_id_{int(time.time()) % 100000}"


def main():
    os.chdir(os.path.dirname(os.path.abspath(__file__)))
    cfg = get_config()

    banner("Demo 5: Workload Identity & Execution Role")
    config_val("Agent", AGENT_NAME)
    config_val("Region", cfg["region"])

    # Step 1: Show execution role permissions
    step_header(1, 3, "Execution role identity permissions")
    info("The CFN role includes GetWorkloadAccessToken:")
    print(f"""
    {YELLOW}Standard:{RESET} Logs, X-Ray, CloudWatch, Bedrock
    {YELLOW}Identity:{RESET} {WHITE}{BOLD}bedrock-agentcore:GetWorkloadAccessToken{RESET}
             Resource: ...workload-identity-directory/*/workload-identity/*
    {YELLOW}Outbound:{RESET} GetResourceApiKey, GetResourceOauth2Token
             secretsmanager:GetSecretValue (bedrock-agentcore*)
    """)

    # Step 2: Deploy
    step_header(2, 3, "Deploying agent (triggers identity creation)")
    s3_key = build_and_upload(AGENT_NAME, cfg["region"], cfg["s3_bucket"], ["agent.py"])
    success("Code uploaded")
    info("Creating runtime — this automatically creates a workload identity")
    runtime = create_runtime(
        agent_name=AGENT_NAME, region=cfg["region"],
        role_arn=cfg["role_arn"], s3_bucket=cfg["s3_bucket"], s3_key=s3_key,
        description="Demo 5: Workload identity demo",
    )
    success(f"Runtime READY: {runtime['runtime_id']}")

    # Step 3: Inspect workload identities
    step_header(3, 3, "Inspecting workload identity directory")
    info("aws bedrock-agentcore-control list-workload-identities")
    control = boto3.client("bedrock-agentcore-control", region_name=cfg["region"])
    try:
        resp = control.list_workload_identities()
        identities = resp.get("workloadIdentities", [])
        if identities:
            print(f"\n  {WHITE}{BOLD}Workload Identities:{RESET}\n")
            for wid in identities:
                print(f"    {GREEN}●{RESET} {BOLD}{wid.get('workloadIdentityName', '?')}{RESET}")
                print(f"      ARN: {MAGENTA}{wid.get('workloadIdentityArn', '')}{RESET}")
                print(f"      Created by: {wid.get('createdBy', '?')}")
                print()
            success(f"Found {len(identities)} workload identity(ies)")
        else:
            info("No identities found yet (may take a moment)")
    except Exception as e:
        info(f"list_workload_identities: {e}")

    section("Using workload identity ARN in IAM policies")
    print(f"""
    The ARN can restrict resource access to specific agents:

    "Condition": {{
      "StringEquals": {{
        "aws:PrincipalTag/WorkloadIdentity":
          "arn:aws:bedrock-agentcore:{cfg['region']}:{cfg['account_id']}:
           workload-identity-directory/default/workload-identity/{AGENT_NAME}"
      }}
    }}
    """)

    state = {
        "agent_name": AGENT_NAME, "runtime_id": runtime["runtime_id"],
        "runtime_arn": runtime["runtime_arn"], "region": cfg["region"],
        "s3_bucket": cfg["s3_bucket"], "s3_key": s3_key,
    }
    with open("runtime_config.json", "w") as f:
        json.dump(state, f, indent=2)

    done("python invoke.py")
    print()


if __name__ == "__main__":
    main()
