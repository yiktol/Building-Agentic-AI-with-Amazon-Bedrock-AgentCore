"""
Demo 5: Create Online Evaluation config for continuous monitoring.

Creates a persistent evaluation configuration that automatically
scores every sampled session using built-in LLM evaluators.

Requires Demo 1 to be deployed.

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
from shared.colors import banner, step_header, success, info, config_val, done

import boto3


def main():
    os.chdir(os.path.dirname(os.path.abspath(__file__)))

    # Load Demo 1 config
    demo1_config = os.path.join(os.path.dirname(__file__), "..", "demo-01-observability-setup", "runtime_config.json")
    if not os.path.exists(demo1_config):
        print("ERROR: Run Demo 1 first (deploy.py)")
        sys.exit(1)

    with open(demo1_config) as f:
        runtime_config = json.load(f)

    cfg = get_config()
    region = cfg["region"]
    eval_role_arn = cfg["eval_role_arn"]

    banner("Demo 5: Online Evaluation — Continuous Monitoring")
    config_val("Region", region)
    config_val("Log Group", runtime_config["log_group"])
    config_val("Service Name", runtime_config["service_name"])

    cp = boto3.client("bedrock-agentcore-control", region_name=region)

    # Step 1: Create online evaluation config
    step_header(1, 1, "Creating online evaluation config")
    info("Evaluators: GoalSuccessRate, Helpfulness, Correctness")
    info("Sampling: 100% of sessions")
    info("Mode: Enabled on create (starts scoring immediately)")

    suffix = uuid.uuid4().hex[:8]
    config_name = f"hr_online_eval_{suffix}"

    evaluators = [
        "Builtin.GoalSuccessRate",
        "Builtin.Helpfulness",
        "Builtin.Correctness",
    ]

    resp = cp.create_online_evaluation_config(
        onlineEvaluationConfigName=config_name,
        rule={"samplingConfig": {"samplingPercentage": 100.0}},
        dataSourceConfig={
            "cloudWatchLogs": {
                "logGroupNames": [runtime_config["log_group"]],
                "serviceNames": [runtime_config["service_name"]],
            }
        },
        evaluators=[{"evaluatorId": eid} for eid in evaluators],
        evaluationExecutionRoleArn=eval_role_arn,
        enableOnCreate=True,
    )

    config_id = resp["onlineEvaluationConfigId"]
    config_arn = resp.get("onlineEvaluationConfigArn", "")

    success(f"Online evaluation config created: {config_id}")
    config_val("Config Name", config_name)
    config_val("Config ID", config_id)

    # Save config
    with open("runtime_config.json", "w") as f:
        json.dump({
            "agent_name": runtime_config["agent_name"],
            "runtime_arn": runtime_config["runtime_arn"],
            "online_eval_config_id": config_id,
            "online_eval_config_arn": config_arn,
            "online_eval_config_name": config_name,
            "region": region,
        }, f, indent=2)

    done("python invoke.py")
    info("")
    info("The config is now ACTIVE. Every new session will be scored automatically.")
    info("Results appear in CloudWatch:")
    info(f"  GenAI Observability → Agent Detail → Evaluations tab")
    print()


if __name__ == "__main__":
    main()
