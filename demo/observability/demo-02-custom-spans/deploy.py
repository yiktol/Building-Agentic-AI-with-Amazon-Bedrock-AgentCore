"""
Demo 2: Custom Spans — setup .env file for local OTel instrumentation.

This demo runs locally (not on AgentCore Runtime) to show how custom
OpenTelemetry spans work with the ADOT SDK sending to CloudWatch.

Usage:
    python deploy.py
"""

import os
import sys
import shutil

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))
from shared.colors import banner, step_header, success, info, config_val, done


def main():
    os.chdir(os.path.dirname(os.path.abspath(__file__)))

    banner("Demo 2: Custom Spans — Local OTel Setup")

    step_header(1, 2, "Checking .env configuration")
    if os.path.exists(".env"):
        success(".env file exists")
    else:
        info("Creating .env from .env.example")
        shutil.copy(".env.example", ".env")
        success("Created .env — edit AWS_DEFAULT_REGION if needed")

    step_header(2, 2, "Installing dependencies")
    info("Run: pip install -r requirements.txt")
    info("")
    info("This demo runs LOCALLY with opentelemetry-instrument.")
    info("Traces go directly to CloudWatch via ADOT.")

    done("opentelemetry-instrument python custom_span_creation.py --session-id demo-001")
    info("")
    info("What to observe in CloudWatch:")
    info("  • travel_agent_session span (custom parent)")
    info("  • web_search span with search.query, search.results_count attributes")
    info("  • get_weather span with weather.location attribute")
    info("  • Span events: search_started, search_completed")
    print()


if __name__ == "__main__":
    main()
