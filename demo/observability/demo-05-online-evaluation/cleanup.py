"""Demo 5: Disable and delete the online evaluation config."""

import json
import os
import sys

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))
from shared.deploy_helpers import load_config
from shared.colors import banner, success, info, done

import boto3


def main():
    os.chdir(os.path.dirname(os.path.abspath(__file__)))
    banner("Demo 5: Cleanup")

    config = load_config()
    region = config["region"]
    config_id = config.get("online_eval_config_id")

    if not config_id:
        info("No online eval config to delete.")
        done()
        return

    cp = boto3.client("bedrock-agentcore-control", region_name=region)

    # Disable first, then delete
    try:
        cp.update_online_evaluation_config(
            onlineEvaluationConfigId=config_id,
            executionStatus="DISABLED",
        )
        info(f"Disabled online eval config: {config_id}")
    except Exception as e:
        info(f"Warning (disable): {e}")

    try:
        cp.delete_online_evaluation_config(onlineEvaluationConfigId=config_id)
        success(f"Deleted online eval config: {config_id}")
    except Exception as e:
        info(f"Warning (delete): {e}")

    if os.path.exists("runtime_config.json"):
        os.remove("runtime_config.json")

    info("Runtime stays running (managed by Demo 1)")
    done()


if __name__ == "__main__":
    main()
