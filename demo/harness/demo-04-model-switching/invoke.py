"""Demo 04: Model Switching — Same session, different models per invocation."""

import os
import sys

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from shared.colors import (
    banner, step_header, section, success, info, config_val, error,
    prompt_display, response_display, done,
    GREEN, YELLOW, DIM, RESET, MAGENTA, BOLD,
)
from shared.harness_helpers import (
    load_config, invoke_harness_prompt, execute_command, new_session_id,
)

CONFIG_FILE = os.path.join(os.path.dirname(__file__), "runtime_config.json")

MODEL_HAIKU = "global.anthropic.claude-haiku-4-5-20251001-v1:0"
MODEL_SONNET = "global.anthropic.claude-sonnet-4-5-20250929-v1:0"


def main():
    banner("Demo 04: Model Switching — Per-Invocation Model Selection")

    # ── Step 1: Load config ───────────────────────────────────────────────────
    step_header(1, 5, "Load deployment config")

    config = load_config(CONFIG_FILE)
    config_val("harness_arn", config["harness_arn"])
    config_val("region", config["region"])

    harness_arn = config["harness_arn"]
    region = config["region"]
    session_id = new_session_id()
    config_val("session_id", session_id)

    # ── Step 2: Invoke with Haiku ─────────────────────────────────────────────
    step_header(2, 5, "Invoke with Claude Haiku 4.5")

    print(f"  {MAGENTA}{BOLD}Model:{RESET} {MODEL_HAIKU}")
    prompt1 = "Write a haiku about cloud computing and save it to haiku_poem.txt"
    prompt_display(prompt1)
    print()

    text1, tools1 = invoke_harness_prompt(
        harness_arn, session_id, prompt1, region, model_id=MODEL_HAIKU
    )
    response_display(text1)
    if tools1:
        info(f"Tool calls: {', '.join(tools1)}")
    print()

    # ── Step 3: Invoke with Sonnet (same session) ─────────────────────────────
    step_header(3, 5, "Invoke with Claude Sonnet 4.5 (same session)")

    print(f"  {MAGENTA}{BOLD}Model:{RESET} {MODEL_SONNET}")
    prompt2 = "Now write a sonnet about artificial intelligence and save it to sonnet_poem.txt"
    prompt_display(prompt2)
    print()

    text2, tools2 = invoke_harness_prompt(
        harness_arn, session_id, prompt2, region, model_id=MODEL_SONNET
    )
    response_display(text2)
    if tools2:
        info(f"Tool calls: {', '.join(tools2)}")
    print()

    # ── Step 4: Verify shared filesystem ──────────────────────────────────────
    step_header(4, 5, "Verify shared filesystem via ExecuteCommand")

    info("Both models wrote to the SAME VM — files from both invocations:\n")

    stdout, stderr, exit_code = execute_command(harness_arn, session_id, "ls -la *.txt", region)
    if stdout:
        for line in stdout.strip().split("\n"):
            print(f"    {GREEN}{line}{RESET}")
    print()

    info("Contents of haiku_poem.txt (written by Haiku):")
    stdout, _, _ = execute_command(harness_arn, session_id, "cat haiku_poem.txt", region)
    if stdout:
        for line in stdout.strip().split("\n"):
            print(f"    {GREEN}{line}{RESET}")
    print()

    info("Contents of sonnet_poem.txt (written by Sonnet):")
    stdout, _, _ = execute_command(harness_arn, session_id, "cat sonnet_poem.txt", region)
    if stdout:
        for line in stdout.strip().split("\n"):
            print(f"    {GREEN}{line}{RESET}")

    # ── Step 5: Summary ───────────────────────────────────────────────────────
    step_header(5, 5, "Summary")

    success("Same harness, same session — two different models")
    info("Model is specified per-invocation, not at harness creation time")
    info("The filesystem state persists across model switches within a session")
    info("Use case: route simple tasks to Haiku, complex tasks to Sonnet")

    done("python cleanup.py")


if __name__ == "__main__":
    main()
