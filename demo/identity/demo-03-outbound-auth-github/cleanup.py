"""Demo 3: Cleanup runtime + GitHub credential provider."""

import json
import os
import sys

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))
from shared.deploy_helpers import cleanup_runtime
from shared.colors import banner, success, info, done

import boto3


def main():
    os.chdir(os.path.dirname(os.path.abspath(__file__)))
    banner("Demo 3: Cleanup")
    try:
        if os.path.exists("runtime_config.json"):
            with open("runtime_config.json") as f:
                config = json.load(f)
            control = boto3.client("bedrock-agentcore-control", region_name=config.get("region", "ap-southeast-1"))
            control.delete_oauth2_credential_provider(name=config.get("provider_name", "github-provider"))
            success("Deleted GitHub credential provider")
    except Exception as e:
        info(f"Provider: {e}")
    cleanup_runtime()
    done()


if __name__ == "__main__":
    main()
