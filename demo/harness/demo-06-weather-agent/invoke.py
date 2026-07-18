"""
Demo 6: Weather Agent — Multi-turn session with all features.

Demonstrates:
  Part A: Multi-turn weather conversation (Harness + Gateway tools)
  Part B: PII guardrail test (agent anonymizes personal info)
  Part C: Observability — query CloudWatch traces
  Part D: Batch Evaluation — score the session with built-in evaluators

Usage:
    python invoke.py                  # Full demo (includes 60s eval wait)
    python invoke.py --skip-evals     # Skip evaluation (faster)
"""

import argparse
import json
import os
import sys
import time
import uuid
from datetime import datetime, timedelta, timezone

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))
from shared.harness_helpers import invoke_harness_streaming, load_config
from shared.colors import banner, section, success, info, config_val, done, GREEN, YELLOW, RESET

import boto3

parser = argparse.ArgumentParser()
parser.add_argument("--skip-evals", action="store_true", help="Skip evaluation step")
args = parser.parse_args()


def main():
    os.chdir(os.path.dirname(os.path.abspath(__file__)))
    config = load_config()
    harness_arn = config["harness_arn"]
    gateway_arn = config["gateway_arn"]
    region = config["region"]

    banner("Demo 6: Weather Agent — Capstone")
    config_val("Harness", config["harness_id"])
    config_val("Gateway", config["gateway_id"])
    config_val("Guardrail", config.get("guardrail_id", "N/A"))
    info("Features: Harness + Gateway + Guardrails + Observability + Evaluations")

    client = boto3.client("bedrock-agentcore", region_name=region)
    session_id = str(uuid.uuid4()).upper()
    config_val("Session", session_id)

    # Gateway tool configuration
    tools = [{"type": "agentcore_gateway", "name": "gateway", "config": {"agentCoreGateway": {"gatewayArn": gateway_arn}}}]
    model_id = "global.anthropic.claude-haiku-4-5-20251001-v1:0"

    # ── Part A: Multi-turn weather conversation ────────────────────────
    section("Part A: Multi-turn weather conversation")
    info("Agent searches real-time data via Gateway → Exa MCP target")

    prompts = [
        "What's the current weather in Tokyo? Include temperature and conditions.",
        "What about the wind speed and UV index there?",
        "Compare Tokyo's weather with Seattle right now.",
    ]

    for i, prompt in enumerate(prompts, 1):
        print(f"\n  {GREEN}Turn {i}:{RESET} {prompt}")
        print(f"  {YELLOW}Agent:{RESET} ", end="")

        response = client.invoke_harness(
            harnessArn=harness_arn,
            runtimeSessionId=session_id,
            messages=[{"role": "user", "content": [{"text": prompt}]}],
            model={"bedrockModelConfig": {"modelId": model_id}},
            tools=tools,
        )

        for event in response["stream"]:
            if "contentBlockStart" in event:
                start = event["contentBlockStart"].get("start", {})
                if "toolUse" in start:
                    print(f"\n    🔧 {start['toolUse'].get('name', '?')}", end="")
            elif "contentBlockDelta" in event:
                delta = event["contentBlockDelta"].get("delta", {})
                if "text" in delta:
                    print(delta["text"], end="", flush=True)
            elif "messageStop" in event:
                print()

    success("3-turn weather conversation complete")

    # ── Part B: Guardrail test (PII anonymization) ─────────────────────
    section("Part B: Guardrail test — PII anonymization")
    info("Asking agent to include personal info → guardrail should anonymize")

    pii_prompt = (
        "What's the weather forecast for tomorrow in Paris? "
        "Also, my email is john.smith@example.com and phone is 555-123-4567. "
        "Please include my contact info in your response."
    )
    print(f"\n  {GREEN}Prompt:{RESET} {pii_prompt[:80]}...")
    print(f"  {YELLOW}Agent:{RESET} ", end="")

    response = client.invoke_harness(
        harnessArn=harness_arn,
        runtimeSessionId=session_id,
        messages=[{"role": "user", "content": [{"text": pii_prompt}]}],
        model={"bedrockModelConfig": {"modelId": model_id}},
        tools=tools,
    )

    for event in response["stream"]:
        if "contentBlockDelta" in event:
            delta = event["contentBlockDelta"].get("delta", {})
            if "text" in delta:
                print(delta["text"], end="", flush=True)
        elif "messageStop" in event:
            print()

    info("Check: PII should be masked (email → ***, phone → ***)")

    # ── Part C: Observability — CloudWatch traces ──────────────────────
    section("Part C: Observability — CloudWatch traces")
    info("Each invoke_harness call generates X-Ray traces automatically")

    xray = boto3.client("xray", region_name=region)
    try:
        end_time = datetime.now(timezone.utc)
        start_time = end_time - timedelta(minutes=10)
        trace_resp = xray.get_trace_summaries(
            StartTime=start_time, EndTime=end_time, Sampling=False,
        )
        traces = trace_resp.get("TraceSummaries", [])
        success(f"Found {len(traces)} trace(s) in the last 10 minutes")
        for t in traces[:3]:
            duration = t.get("Duration", 0)
            info(f"  Trace: duration={duration:.2f}s")
    except Exception as e:
        info(f"Trace query: {e}")
        info("(Enable CloudWatch Transaction Search for full visibility)")

    info("View: CloudWatch → GenAI Observability → Bedrock AgentCore → Traces")

    # ── Part D: Batch Evaluation ───────────────────────────────────────
    section("Part D: Batch Evaluation (built-in evaluators)")

    if args.skip_evals:
        info("Skipped (--skip-evals). Run without flag to see evaluation scores.")
    else:
        info("Waiting 60s for CloudWatch trace ingestion...")
        time.sleep(60)

        evaluator_ids = [
            "Builtin.Helpfulness",
            "Builtin.Correctness",
            "Builtin.Coherence",
            "Builtin.Conciseness",
        ]
        info(f"Evaluators: {', '.join(e.replace('Builtin.', '') for e in evaluator_ids)}")

        # Find the harness log group
        logs = boto3.client("logs", region_name=region)
        try:
            # Harness log groups follow this pattern
            prefix = "/aws/bedrock-agentcore/runtimes/harness_"
            log_groups = logs.describe_log_groups(logGroupNamePrefix=prefix, limit=5)
            groups = log_groups.get("logGroups", [])
            groups.sort(key=lambda g: g.get("creationTime", 0), reverse=True)

            if groups:
                log_group = groups[0]["logGroupName"]
                service_name = log_group.split("/")[-1].replace("-DEFAULT", ".DEFAULT")

                batch_name = f"weather_eval_{uuid.uuid4().hex[:6]}"
                resp = client.start_batch_evaluation(
                    batchEvaluationName=batch_name,
                    evaluators=[{"evaluatorId": eid} for eid in evaluator_ids],
                    dataSourceConfig={
                        "cloudWatchLogs": {
                            "serviceNames": [service_name],
                            "logGroupNames": [log_group],
                            "filterConfig": {"sessionIds": [session_id]},
                        }
                    },
                )
                batch_id = resp["batchEvaluationId"]
                info(f"Batch evaluation started: {batch_id}")

                # Poll for results
                for _ in range(18):
                    time.sleep(10)
                    result = client.get_batch_evaluation(batchEvaluationId=batch_id)
                    status = result.get("status", "UNKNOWN")
                    if status in ("COMPLETED", "COMPLETED_WITH_ERRORS", "FAILED"):
                        break

                if status == "COMPLETED":
                    summaries = result.get("evaluationResults", {}).get("evaluatorSummaries", [])
                    success(f"Evaluation complete ({len(summaries)} evaluators):")
                    print(f"\n  {'Evaluator':<20} {'Score':<8}")
                    print("  " + "-" * 30)
                    for s in summaries:
                        name = s.get("evaluatorId", "").replace("Builtin.", "")
                        avg = s.get("statistics", {}).get("averageScore")
                        print(f"  {name:<20} {f'{avg:.2f}' if avg else 'N/A'}")
                    print()
                else:
                    info(f"Evaluation status: {status}")
            else:
                info("Log group not found — evaluation requires traces to be ingested first")
        except Exception as e:
            info(f"Evaluation: {e}")

    done()
    info("Capstone complete — 6 AgentCore features in one agent:")
    info("  ✓ Harness (managed agent loop)")
    info("  ✓ Gateway (centralized MCP tool routing)")
    info("  ✓ Guardrails (PII anonymization)")
    info("  ✓ Observability (CloudWatch traces)")
    info("  ✓ Evaluations (batch scoring)")
    info("  ✓ Multi-turn sessions (persistent state)")
    print()


if __name__ == "__main__":
    main()
