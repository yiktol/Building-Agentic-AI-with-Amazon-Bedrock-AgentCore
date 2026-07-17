"""
Demo 4: On-Demand Evaluation — invoke agent then evaluate.

Shows:
  1. Invoke the HR agent for a multi-turn session
  2. Wait for CloudWatch span ingestion (~90s)
  3. Run EvaluationClient with built-in evaluators
  4. Display evaluation scores

Requires Demo 1 to be deployed.

Usage:
    python invoke.py
"""

import json
import os
import sys
import time
import uuid
from datetime import timedelta

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))
from shared.colors import banner, section, success, info, error, config_val, prompt_display, response_display, done

import boto3


def main():
    os.chdir(os.path.dirname(os.path.abspath(__file__)))

    # Load Demo 1 config
    demo1_config = os.path.join(os.path.dirname(__file__), "..", "demo-01-observability-setup", "runtime_config.json")
    if not os.path.exists(demo1_config):
        print("ERROR: Run Demo 1 first (deploy.py)")
        sys.exit(1)

    with open(demo1_config) as f:
        config = json.load(f)

    runtime_arn = config["runtime_arn"]
    runtime_id = config["runtime_id"]
    region = config["region"]

    banner("Demo 4: On-Demand Evaluation (LLM-as-a-Judge)")
    config_val("Runtime", runtime_arn)
    config_val("Region", region)

    dp = boto3.client("bedrock-agentcore", region_name=region)

    # ── Part A: Invoke agent for a multi-turn session ──────────────────
    section("Part A: Invoking HR Assistant (multi-turn session)")
    session_id = str(uuid.uuid4())
    info(f"Session ID: {session_id}")

    turns = [
        "Employee ID: EMP-001. What is my current PTO balance?",
        "Employee ID: EMP-001. Please submit a PTO request from 2026-08-01 to 2026-08-05.",
        "What is the company remote work policy?",
    ]

    for i, prompt in enumerate(turns, 1):
        prompt_display(f"Turn {i}: {prompt}")
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

    # ── Part B: Wait for CloudWatch ingestion ──────────────────────────
    section("Part B: Waiting for CloudWatch span ingestion")
    info("Spans need ~90s to appear in CloudWatch Logs...")
    for remaining in range(90, 0, -15):
        info(f"  {remaining}s remaining...")
        time.sleep(15)
    success("Ingestion window complete")

    # ── Part C: Run on-demand evaluation ───────────────────────────────
    section("Part C: Running on-demand evaluation")
    info("Using EvaluationClient with built-in evaluators:")
    info("  • Builtin.GoalSuccessRate (SESSION)")
    info("  • Builtin.Helpfulness (TRACE)")
    info("  • Builtin.Correctness (TRACE)")

    try:
        from bedrock_agentcore.evaluation import EvaluationClient

        ec = EvaluationClient(region_name=region)

        # Derive agent_id from runtime_id
        agent_id = runtime_id

        evaluator_ids = [
            "Builtin.GoalSuccessRate",
            "Builtin.Helpfulness",
            "Builtin.Correctness",
        ]

        # Pre-populate level cache for built-in evaluators
        ec._evaluator_level_cache.update({
            "Builtin.GoalSuccessRate": "SESSION",
            "Builtin.Correctness": "TRACE",
            "Builtin.Helpfulness": "TRACE",
        })

        results = ec.run(
            evaluator_ids=evaluator_ids,
            agent_id=agent_id,
            session_id=session_id,
            look_back_time=timedelta(hours=1),
        )

        if results:
            success(f"Received {len(results)} evaluation result(s):")
            print()
            print(f"  {'Evaluator':<35} {'Score':<8} {'Label'}")
            print("  " + "-" * 60)
            for r in results:
                eid = r.get("evaluatorId", "unknown")
                value = r.get("value", r.get("score", "N/A"))
                label = r.get("label", r.get("rating", ""))
                err = r.get("errorCode")
                if err:
                    print(f"  {eid:<35} {'ERR':<8} {err}")
                else:
                    print(f"  {eid:<35} {str(value):<8} {label}")
        else:
            info("No results returned — spans may not have been ingested yet")
            info("Try running again after a few more minutes")

    except ImportError:
        error("bedrock_agentcore.evaluation not available")
        info("Install: pip install bedrock-agentcore>=1.5.0")
    except Exception as e:
        error(f"Evaluation failed: {e}")
        info("This may be due to spans not yet available in CloudWatch")
        info("Try running again after 2-3 minutes")

    done()
    info("Key: On-demand evaluation scores specific sessions after they complete")
    info("Evaluators: Helpfulness, Correctness (per-turn) + GoalSuccessRate (per-session)")
    info("Results also visible in CloudWatch GenAI Observability → Evaluations tab")
    print()


if __name__ == "__main__":
    main()
