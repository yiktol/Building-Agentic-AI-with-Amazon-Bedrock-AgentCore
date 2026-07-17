"""
Demo 5: Trigger online evaluation by invoking the agent.

Sends prompts to generate live traffic that the online evaluation
config will automatically score.

Usage:
    python invoke.py
"""

import json
import os
import sys
import uuid

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))
from shared.deploy_helpers import load_config as load_demo5_config
from shared.colors import banner, section, success, info, config_val, prompt_display, response_display, done

import boto3


def main():
    os.chdir(os.path.dirname(os.path.abspath(__file__)))

    # Load Demo 1 config for runtime ARN
    demo1_config = os.path.join(os.path.dirname(__file__), "..", "demo-01-observability-setup", "runtime_config.json")
    with open(demo1_config) as f:
        runtime_config = json.load(f)

    # Load Demo 5 config for online eval info
    config = load_demo5_config()

    runtime_arn = runtime_config["runtime_arn"]
    region = runtime_config["region"]

    banner("Demo 5: Online Evaluation — Triggering Live Scoring")
    config_val("Runtime", runtime_arn)
    config_val("Online Eval Config", config.get("online_eval_config_name", ""))

    dp = boto3.client("bedrock-agentcore", region_name=region)

    # Send several sessions to trigger evaluation
    sessions = [
        {
            "prompts": [
                "Employee ID: EMP-042. What is my PTO balance?",
                "What health insurance options does the company offer?",
            ]
        },
        {
            "prompts": [
                "Employee ID: EMP-002. What is the parental leave policy?",
                "How many weeks do primary caregivers get?",
            ]
        },
    ]

    for i, session in enumerate(sessions, 1):
        section(f"Session {i}/{len(sessions)}")
        session_id = str(uuid.uuid4())
        info(f"Session ID: {session_id}")

        for prompt in session["prompts"]:
            prompt_display(prompt)
            resp = dp.invoke_agent_runtime(
                agentRuntimeArn=runtime_arn,
                runtimeSessionId=session_id,
                payload=json.dumps({"prompt": prompt}).encode("utf-8"),
            )
            raw = resp["response"].read().decode("utf-8")
            # Parse SSE streaming response
            parts = []
            for line in raw.splitlines():
                if line.startswith("data: "):
                    chunk = line[len("data: "):]
                    if chunk.startswith('"') and chunk.endswith('"'):
                        chunk = chunk[1:-1]
                    parts.append(chunk)
            reply = "".join(parts) if parts else raw
            response_display(reply[:200])

    done()
    info("Online evaluation will score these sessions automatically.")
    info("Results appear in CloudWatch within 5-10 minutes:")
    info("  GenAI Observability → Agent Detail → Evaluations tab")
    info("")
    info("Evaluated metrics per level:")
    info("  SESSION: GoalSuccessRate (did the agent complete the user's goal?)")
    info("  TRACE:   Helpfulness (was it useful?), Correctness (was it accurate?)")
    info("")
    info("Key: Online evaluation = continuous monitoring of live production traffic")
    info("     On-demand evaluation = targeted assessment of specific sessions")
    print()


if __name__ == "__main__":
    main()
