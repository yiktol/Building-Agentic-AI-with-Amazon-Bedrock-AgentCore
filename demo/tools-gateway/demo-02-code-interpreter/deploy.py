"""
Demo 2: Deploy Code Interpreter agent to AgentCore Runtime.

The agent uses Code Interpreter as a tool — it decides when to
write and execute code to answer questions.

Usage:
    python deploy.py
"""

import json
import os
import shutil
import subprocess
import sys
import time

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))
from shared.stack_config import get_config
from shared.colors import banner, step_header, success, info, config_val, done

import boto3
from botocore.exceptions import ClientError

AGENT_NAME = f"demo02_code_interp_{int(time.time()) % 100000}"
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

    banner("Demo 2: Code Interpreter Agent")

    # Check if already deployed
    existing = check_existing(cfg["region"])
    if existing:
        success(f"Already deployed: {existing['runtime_id']}")
        config_val("Runtime ARN", existing["runtime_arn"])
        done("python invoke.py")
        return

    config_val("Agent", AGENT_NAME)
    config_val("Region", cfg["region"])
    info("Agent uses execute_python tool → Code Interpreter sandbox")

    # Build package
    step_header(1, 2, "Building arm64 package → S3")
    s3_key = f"{AGENT_NAME}/code.zip"
    pkg_dir = "deployment_package"
    zip_file = "deployment_package.zip"

    if os.path.isdir(pkg_dir):
        shutil.rmtree(pkg_dir)
    subprocess.run([
        "uv", "pip", "install", "--python-platform", "aarch64-manylinux2014",
        "--python-version", "3.13", "--target", pkg_dir,
        "--only-binary", ":all:", "-r", "requirements.txt",
    ], check=True, capture_output=True)
    subprocess.run(["zip", "-r", f"../{zip_file}", "."], cwd=pkg_dir, check=True, capture_output=True)
    subprocess.run(["zip", zip_file, "agent.py"], check=True, capture_output=True)

    s3 = boto3.client("s3", region_name=cfg["region"])
    s3.upload_file(zip_file, cfg["s3_bucket"], s3_key)
    shutil.rmtree(pkg_dir)
    os.remove(zip_file)
    success("Uploaded to S3")

    # Create runtime
    step_header(2, 2, "Creating AgentCore Runtime")
    info("Agent has execute_python tool → calls Code Interpreter API")
    control = boto3.client("bedrock-agentcore-control", region_name=cfg["region"])

    # Get the Code Interpreter ID
    ci_list = control.list_code_interpreters()
    ci_summaries = ci_list.get("codeInterpreterSummaries", [])
    if ci_summaries:
        ci_id = ci_summaries[0]["codeInterpreterId"]
        info(f"Using Code Interpreter: {ci_id}")
    else:
        ci_id = "aws.codeinterpreter.v1"
        info("Using default Code Interpreter")

    for attempt in range(5):
        try:
            resp = control.create_agent_runtime(
                agentRuntimeName=AGENT_NAME,
                agentRuntimeArtifact={
                    "codeConfiguration": {
                        "code": {"s3": {"bucket": cfg["s3_bucket"], "prefix": s3_key}},
                        "runtime": "PYTHON_3_13",
                        "entryPoint": ["agent.py"],
                    }
                },
                roleArn=cfg["runtime_role_arn"],
                networkConfiguration={"networkMode": "PUBLIC"},
                protocolConfiguration={"serverProtocol": "HTTP"},
                environmentVariables={"CODE_INTERPRETER_ID": ci_id},
                description="Demo 2: Agent with Code Interpreter tool",
            )
            break
        except ClientError as e:
            if "role" in str(e).lower() and attempt < 4:
                time.sleep(2**attempt * 4)
            else:
                raise

    runtime_id = resp["agentRuntimeId"]
    runtime_arn = resp["agentRuntimeArn"]

    info("Waiting for READY...")
    while True:
        status = control.get_agent_runtime(agentRuntimeId=runtime_id)["status"]
        if status == "READY":
            break
        if "FAILED" in status:
            from shared.colors import error
            error(f"Failed: {status}")
            sys.exit(1)
        time.sleep(15)

    control.create_agent_runtime_endpoint(agentRuntimeId=runtime_id, name="default")
    while True:
        eps = control.list_agent_runtime_endpoints(agentRuntimeId=runtime_id)
        for ep in eps.get("runtimeEndpoints", []):
            if ep["name"] == "default" and ep["status"] == "READY":
                success(f"Runtime READY: {runtime_id}")
                state = {
                    "agent_name": AGENT_NAME, "runtime_id": runtime_id,
                    "runtime_arn": runtime_arn, "region": cfg["region"],
                    "s3_bucket": cfg["s3_bucket"], "s3_key": s3_key,
                }
                with open("runtime_config.json", "w") as f:
                    json.dump(state, f, indent=2)
                done("python invoke.py")
                config_val("Runtime ARN", runtime_arn)
                print()
                return
        time.sleep(15)


if __name__ == "__main__":
    main()
