"""Demo 05: Interactive Chat — Scripted multi-turn conversation showing state persistence."""

import os
import sys

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from shared.colors import (
    banner, step_header, section, success, info, config_val, error,
    prompt_display, response_display, done,
    GREEN, YELLOW, DIM, RESET,
)
from shared.harness_helpers import (
    load_config, invoke_harness_prompt, execute_command, new_session_id,
)

CONFIG_FILE = os.path.join(os.path.dirname(__file__), "runtime_config.json")

# Scripted conversation demonstrating state persistence
CONVERSATION = [
    "My name is Alice and I'm working on a data pipeline project. Create a project directory called 'pipeline' with a README.md that mentions my name.",
    "What's my name? And can you add a Python script to the pipeline directory that reads CSV files?",
    "Show me all the files you've created so far in the pipeline directory.",
]


def main():
    banner("Demo 05: Interactive Chat — State Persistence")

    # ── Step 1: Load config ───────────────────────────────────────────────────
    step_header(1, 4, "Load deployment config")

    config = load_config(CONFIG_FILE)
    config_val("harness_arn", config["harness_arn"])
    config_val("region", config["region"])

    harness_arn = config["harness_arn"]
    region = config["region"]
    session_id = new_session_id()
    config_val("session_id", session_id)

    # ── Step 2: Multi-turn conversation ───────────────────────────────────────
    step_header(2, 4, "Multi-turn conversation (3 prompts)")

    info("Same session_id across all turns — agent remembers context\n")

    for i, prompt in enumerate(CONVERSATION, 1):
        section(f"Turn {i}/{len(CONVERSATION)}")
        prompt_display(prompt)
        print()

        text, tool_calls = invoke_harness_prompt(harness_arn, session_id, prompt, region)
        response_display(text)
        if tool_calls:
            info(f"Tool calls: {', '.join(tool_calls)}")
        print()

    # ── Step 3: Verify state via ExecuteCommand ───────────────────────────────
    step_header(3, 4, "Verify state via ExecuteCommand")

    info("Checking the files created across all turns:\n")

    stdout, stderr, exit_code = execute_command(
        harness_arn, session_id, "find pipeline -type f 2>/dev/null || echo 'No pipeline dir'", region
    )
    if stdout:
        for line in stdout.strip().split("\n"):
            print(f"    {GREEN}{line}{RESET}")
    print()

    info("Checking README for Alice's name:")
    stdout, _, _ = execute_command(
        harness_arn, session_id, "cat pipeline/README.md 2>/dev/null || echo 'File not found'", region
    )
    if stdout:
        for line in stdout.strip().split("\n"):
            print(f"    {GREEN}{line}{RESET}")

    # ── Step 4: Summary ───────────────────────────────────────────────────────
    step_header(4, 4, "Summary")

    success("Session state persists across invocations")
    info("The agent remembers user's name, project context, and created files")
    info("Filesystem state accumulates across turns in the same session")
    info("A new session_id starts fresh (no memory, clean VM)")

    done("python invoke_agent.py  # Full interactive chatbot\npython cleanup.py       # Delete harness")


if __name__ == "__main__":
    main()
