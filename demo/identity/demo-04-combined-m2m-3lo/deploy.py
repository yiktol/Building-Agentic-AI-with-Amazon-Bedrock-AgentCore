"""
Demo 4: Deploy agent with M2M + 3LO credential providers.

M2M uses the Cognito machine client from CloudFormation.
3LO requires GOOGLE_CLIENT_ID and GOOGLE_CLIENT_SECRET env vars.

Usage:
    export GOOGLE_CLIENT_ID="..."
    export GOOGLE_CLIENT_SECRET="..."
    python deploy.py
"""

import json
import os
import sys
import time

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))
from shared.stack_config import get_config
from shared.deploy_helpers import build_and_upload, create_runtime
from shared.colors import banner, step_header, section, success, info, error, config_val, done

import boto3

AGENT_NAME = f"demo04_m2m_3lo_{int(time.time()) % 100000}"


def main():
    os.chdir(os.path.dirname(os.path.abspath(__file__)))
    cfg = get_config()

    google_id = os.environ.get("GOOGLE_CLIENT_ID", "")
    google_secret = os.environ.get("GOOGLE_CLIENT_SECRET", "")

    banner("Demo 4: Combined M2M + 3LO Outbound Auth")
    config_val("Agent", AGENT_NAME)
    config_val("Region", cfg["region"])

    # Step 1: Create M2M credential provider (using Cognito machine client from CFN)
    step_header(1, 4, "Creating M2M credential provider")
    info(f"Token endpoint: {cfg['cognito_token_endpoint']}")
    info("Grant type: client_credentials (no user interaction)")

    # Get machine client secret from Cognito
    cognito = boto3.client("cognito-idp", region_name=cfg["region"])
    client_resp = cognito.describe_user_pool_client(
        UserPoolId=cfg["cognito_user_pool_id"],
        ClientId=cfg["cognito_machine_client_id"],
    )
    machine_secret = client_resp["UserPoolClient"].get("ClientSecret", "")

    try:
        from bedrock_agentcore.services.identity import IdentityClient
        identity = IdentityClient(cfg["region"])
        identity.create_oauth2_credential_provider({
            "name": "m2m-provider",
            "credentialProviderVendor": "CustomOauth2",
            "oauth2ProviderConfigInput": {
                "customOauth2ProviderConfig": {
                    "oauthDiscovery": {
                        "discoveryUrl": cfg["cognito_discovery_url"],
                    },
                    "clientId": cfg["cognito_machine_client_id"],
                    "clientSecret": machine_secret,
                }
            },
        })
        success("Created M2M provider: m2m-provider")
    except Exception as e:
        if "already exists" in str(e).lower() or "Conflict" in str(e):
            success("M2M provider exists")
        else:
            error(f"M2M provider: {e}")

    # Step 2: Create Google 3LO provider (optional)
    step_header(2, 4, "Creating Google 3LO credential provider")
    if google_id and google_secret:
        try:
            provider = identity.create_oauth2_credential_provider({
                "name": "google-3lo-provider",
                "credentialProviderVendor": "GoogleOauth2",
                "oauth2ProviderConfigInput": {
                    "googleOauth2ProviderConfig": {
                        "clientId": google_id, "clientSecret": google_secret,
                    }
                },
            })
            success("Created Google 3LO provider")
            config_val("Callback URL", provider.get("callbackUrl", "see console"))
            info("Add this callback URL to Google Cloud Console → Authorized redirect URIs")
        except Exception as e:
            if "already exists" in str(e).lower() or "Conflict" in str(e):
                success("Google 3LO provider exists")
            else:
                info(f"Google provider: {e}")
    else:
        info("Skipping Google 3LO (GOOGLE_CLIENT_ID/SECRET not set)")
        info("M2M flow will still work without Google credentials")

    # Step 3: Build & upload
    step_header(3, 4, "Building arm64 package → S3")
    s3_key = build_and_upload(AGENT_NAME, cfg["region"], cfg["s3_bucket"], ["agent.py"])
    success("Uploaded to S3")

    # Step 4: Create runtime with inbound auth
    step_header(4, 4, "Creating runtime with inbound auth")
    info("Protected by Cognito JWT (user must authenticate)")
    runtime = create_runtime(
        agent_name=AGENT_NAME, region=cfg["region"],
        role_arn=cfg["role_arn"], s3_bucket=cfg["s3_bucket"], s3_key=s3_key,
        authorizer_config={
            "customJWTAuthorizer": {
                "discoveryUrl": cfg["cognito_discovery_url"],
                "allowedClients": [cfg["cognito_user_client_id"]],
            }
        },
        description="Demo 4: Combined M2M + 3LO outbound auth",
    )
    success(f"Runtime READY: {runtime['runtime_id']}")

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
