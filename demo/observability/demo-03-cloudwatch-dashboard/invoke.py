"""
Demo 3: Query CloudWatch for trace data programmatically.

Shows how to:
  1. Query the GenAI observability log group for recent spans
  2. Display the session → trace → span hierarchy
  3. Show key metrics (latency, token usage, tool calls)

Requires Demo 1 to have been deployed and invoked first.

Usage:
    python invoke.py
"""

import json
import os
import sys
import time
from datetime import datetime, timedelta, timezone

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))
from shared.colors import banner, section, success, info, config_val, done

import boto3


def main():
    os.chdir(os.path.dirname(os.path.abspath(__file__)))

    # Try to load config from Demo 1
    demo1_config = os.path.join(os.path.dirname(__file__), "..", "demo-01-observability-setup", "runtime_config.json")
    if not os.path.exists(demo1_config):
        print("ERROR: Run Demo 1 first (deploy.py + invoke.py)")
        sys.exit(1)

    with open(demo1_config) as f:
        config = json.load(f)

    region = config["region"]
    log_group = config["log_group"]
    service_name = config["service_name"]

    banner("Demo 3: CloudWatch GenAI Observability — Programmatic Access")
    config_val("Region", region)
    config_val("Log Group", log_group)
    config_val("Service Name", service_name)

    logs = boto3.client("logs", region_name=region)

    # ── Part A: Query recent log events ────────────────────────────────
    section("Part A: Querying recent spans from CloudWatch Logs")
    info(f"Log group: {log_group}")

    end_time = int(datetime.now(timezone.utc).timestamp() * 1000)
    start_time = end_time - (30 * 60 * 1000)  # last 30 minutes

    try:
        events = logs.filter_log_events(
            logGroupName=log_group,
            startTime=start_time,
            endTime=end_time,
            limit=20,
        )
        event_list = events.get("events", [])
        success(f"Found {len(event_list)} log events in last 30 minutes")

        for evt in event_list[:5]:
            msg = evt["message"][:150]
            info(f"  {msg}")

    except logs.exceptions.ResourceNotFoundException:
        info(f"Log group not found yet — invoke the agent and wait 2-3 minutes")
    except Exception as e:
        info(f"Query error: {e}")

    # ── Part B: Dashboard navigation guide ─────────────────────────────
    section("Part B: CloudWatch Console Navigation")
    info("Open the CloudWatch Console and navigate to:")
    info("")
    info("  1. AGENTS VIEW")
    info("     CloudWatch → GenAI Observability → Bedrock AgentCore → Agents")
    info("     Shows: all agents, session count, error rate, throttle rate")
    info("")
    info("  2. AGENT DETAIL VIEW")
    info("     Click on your agent name")
    info("     Shows: individual metrics, runtime metrics, list of sessions")
    info("")
    info("  3. SESSION DETAIL VIEW")
    info("     Click on a session ID")
    info("     Shows: traces summary, server/client errors, throttles")
    info("")
    info("  4. TRACE DETAIL VIEW")
    info("     Click on a trace")
    info("     Shows: span count, P95 latency, timeline + trajectory views")
    info("")
    info("  5. SPAN DETAILS")
    info("     Click on a span in the timeline")
    info("     Shows: attributes, events, duration, error status")

    # ── Part C: Metrics ────────────────────────────────────────────────
    section("Part C: AgentCore Runtime Metrics")
    cw = boto3.client("cloudwatch", region_name=region)

    end = datetime.now(timezone.utc)
    start = end - timedelta(hours=1)

    try:
        resp = cw.get_metric_statistics(
            Namespace="AWS/BedRockAgentCore",
            MetricName="Invocations",
            StartTime=start,
            EndTime=end,
            Period=300,
            Statistics=["Sum"],
        )
        datapoints = resp.get("Datapoints", [])
        total = sum(dp["Sum"] for dp in datapoints)
        success(f"Runtime invocations (last hour): {int(total)}")
    except Exception as e:
        info(f"Metrics query: {e}")

    done()
    info("Key observability hierarchy:")
    info("  Session (conversation) → Trace (request-response) → Span (operation)")
    info("")
    info("Console URL:")
    info(f"  https://console.aws.amazon.com/cloudwatch/home?region={region}#container-insights:agentcore")
    print()


if __name__ == "__main__":
    main()
