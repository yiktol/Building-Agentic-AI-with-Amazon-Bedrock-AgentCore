"""
Demo 3: Deploy agent + create GitHub OAuth2 credential provider.

Requires: GITHUB_CLIENT_ID and GITHUB_CLIENT_SECRET env vars.

Usage:
    export GITHUB_CLIENT_ID="..."
    export GITHUB_CLIENT_SECRET="..."
    python deploy.py
"""

import json
import os
import sys
import time

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))
from shared.stack_config import get_config
from shared.deploy_helpers import build_and_upload, create_runtime
from shared.colors import banner, step_header, success, info, error, config_val, done

AGENT_NAME = f"demo03_outbound_github_{int(time.time()) % 100000}"
PROVIDER_NAME = "github-provider"
CONFIG_FILE = "runtime_config.json"


def check_existing(region):
    """Check if a previously deployed runtime still exists and is READY."""
    if not os.path.exists(CONFIG_FILE):
        return None
    with open(CONFIG_FILE) as f:
        config = json.load(f)
    runtime_id = config.get("runtime_id")
    if not runtime_id:
        return None
    try:
        import boto3
        control = boto3.client("bedrock-agentcore-control", region_name=region)
        resp = control.get_agent_runtime(agentRuntimeId=runtime_id)
        if resp.get("status") in ("READY", "ACTIVE"):
            return config
    except Exception:
        pass
    return None


def main():
    os.chdir(os.path.dirname(os.path.abspath(__file__)))
    cfg = get_config()

    # Check if already deployed
    existing = check_existing(cfg["region"])
    if existing:
        banner("Demo 3: Outbound Auth \u2014 GitHub 3LO")
        success(f"Already deployed: {existing['runtime_id']}")
        config_val("Runtime ARN", existing["runtime_arn"])
        done("python invoke.py")
        return

    gh_id = os.environ.get("GITHUB_CLIENT_ID", "")
    gh_secret = os.environ.get("GITHUB_CLIENT_SECRET", "")
    if not gh_id or not gh_secret:
        error("Set: export GITHUB_CLIENT_ID=... GITHUB_CLIENT_SECRET=...")
        sys.exit(1)

    banner("Demo 3: Outbound Auth — GitHub 3LO")
    config_val("Agent", AGENT_NAME)
    config_val("GitHub Client", gh_id)

    step_header(1, 3, "Creating GitHub OAuth2 credential provider")
    info("Vendor: GithubOauth2 (pre-configured endpoints)")
    try:
        from bedrock_agentcore.services.identity import IdentityClient
        identity = IdentityClient(cfg["region"])
        provider = identity.create_oauth2_credential_provider({
            "name": PROVIDER_NAME,
            "credentialProviderVendor": "GithubOauth2",
            "oauth2ProviderConfigInput": {
                "githubOauth2ProviderConfig": {
                    "clientId": gh_id, "clientSecret": gh_secret,
                }
            },
        })
        success(f"Created: {PROVIDER_NAME}")
        callback_url = provider.get("callbackUrl", "see console")
        config_val("Callback URL", callback_url)
        info("UPDATE your GitHub OAuth App's callback URL to the value above!")
    except Exception as e:
        if "already exists" in str(e).lower() or "Conflict" in str(e):
            success(f"Provider exists: {PROVIDER_NAME}")
            callback_url = "(already configured)"
        else:
            error(f"Failed: {e}")
            sys.exit(1)

    step_header(2, 3, "Building arm64 package → S3")
    s3_key = build_and_upload(AGENT_NAME, cfg["region"], cfg["s3_bucket"], ["agent.py"])
    success("Uploaded to S3")

    step_header(3, 3, "Creating AgentCore Runtime")
    runtime = create_runtime(
        agent_name=AGENT_NAME, region=cfg["region"],
        role_arn=cfg["role_arn"], s3_bucket=cfg["s3_bucket"], s3_key=s3_key,
        description="Demo 3: Outbound auth with GitHub 3LO",
    )
    success(f"Runtime READY: {runtime['runtime_id']}")

    state = {
        "agent_name": AGENT_NAME, "runtime_id": runtime["runtime_id"],
        "runtime_arn": runtime["runtime_arn"], "region": cfg["region"],
        "s3_bucket": cfg["s3_bucket"], "s3_key": s3_key,
        "provider_name": PROVIDER_NAME,
    }
    with open("runtime_config.json", "w") as f:
        json.dump(state, f, indent=2)

    done("python invoke.py")
    print()


if __name__ == "__main__":
    main()
