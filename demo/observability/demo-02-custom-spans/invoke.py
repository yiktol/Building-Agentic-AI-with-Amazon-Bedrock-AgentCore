"""
Demo 2: Run the custom spans demo with OTel instrumentation.

Wraps the custom_span_creation.py execution with colored output.

Usage:
    python invoke.py
"""

import os
import subprocess
import sys

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))
from shared.colors import banner, section, success, info, done


def main():
    os.chdir(os.path.dirname(os.path.abspath(__file__)))

    banner("Demo 2: Custom Spans — Running Travel Agent")
    info("Agent: Travel agent with web_search + get_weather tools")
    info("Custom spans wrap each tool call with rich attributes")

    section("Running with opentelemetry-instrument")
    info("Command: opentelemetry-instrument python custom_span_creation.py --session-id demo-001")
    print()

    result = subprocess.run(
        ["opentelemetry-instrument", "python", "custom_span_creation.py", "--session-id", "demo-001"],
        cwd=os.path.dirname(os.path.abspath(__file__)),
        env={**os.environ},
    )

    if result.returncode == 0:
        success("Agent completed successfully")
    else:
        info(f"Exit code: {result.returncode}")

    done()
    info("View custom spans in CloudWatch:")
    info("  Console → CloudWatch → GenAI Observability → Traces")
    info("  Look for: travel_agent_session → web_search → get_weather")
    info("  Check span attributes: search.query, search.results_count, weather.location")
    print()


if __name__ == "__main__":
    main()
