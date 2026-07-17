"""Demo 4: Cleanup runtime + credential providers."""

import json
import os
import sys

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))
from shared.deploy_helpers import cleanup_runtime
from shared.colors import banner, success, info, done

import boto3


def main():
    os.chdir(os.path.dirname(os.path.abspath(__file__)))
    banner("Demo 4: Cleanup")

    if os.path.exists("runtime_config.json"):
        with open("runtime_config.json") as f:
            config = json.load(f)
        region = config.get("region", "ap-southeast-1")
        control = boto3.client("bedrock-agentcore-control", region_name=region)
        for name in ["m2m-provider", "google-3lo-provider"]:
            try:
                control.delete_oauth2_credential_provider(name=name)
                success(f"Deleted provider: {name}")
            except Exception as e:
                info(f"{name}: {e}")

    cleanup_runtime()
    done()


if __name__ == "__main__":
    main()
