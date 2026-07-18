"""Demo 01: Getting Started — Invoke harness with a prompt and stream response."""

import os
import sys

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from shared.colors import (
    banner, step_header, section, success, info, config_val,
    prompt_display, response_display, done,
)
from shared.harness_helpers import (
    load_config, invoke_harness_streaming, new_session_id,
)

CONFIG_FILE = os.path.join(os.path.dirname(__file__), "runtime_config.json")


def main():
    banner("Demo 01: Getting Started — Invoke Harness")

    # ── Step 1: Load config ───────────────────────────────────────────────────
    step_header(1, 3, "Load deployment config")

    config = load_config(CONFIG_FILE)
    config_val("harness_arn", config["harness_arn"])
    config_val("region", config["region"])

    harness_arn = config["harness_arn"]
    region = config["region"]
    session_id = new_session_id()
    config_val("session_id", session_id)

    # ── Step 2: Invoke with a prompt ──────────────────────────────────────────
    step_header(2, 3, "Invoke harness (streaming)")

    prompt = "What are three fun things to do in Seattle on a rainy day? Save to a Markdown file."
    prompt_display(prompt)
    print()

    info("Streaming response...")
    print()
    text, tool_calls = invoke_harness_streaming(
        harness_arn=harness_arn,
        session_id=session_id,
        prompt=prompt,
        region=region,
    )

    # ── Step 3: Summary ───────────────────────────────────────────────────────
    step_header(3, 3, "Summary")

    success(f"Response length: {len(text)} chars")
    if tool_calls:
        info(f"Tool calls made: {', '.join(tool_calls)}")
    else:
        info("No tool calls (text-only response)")

    done("python invoke_agent.py  # Interactive chat\npython cleanup.py       # Delete harness")


if __name__ == "__main__":
    main()
