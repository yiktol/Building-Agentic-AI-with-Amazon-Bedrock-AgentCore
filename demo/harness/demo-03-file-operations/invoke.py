"""Demo 03: File Operations — Agent writes/reads files and runs code in isolated VM."""

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


def main():
    banner("Demo 03: File Operations — Write, Read, Execute")

    # ── Step 1: Load config ───────────────────────────────────────────────────
    step_header(1, 5, "Load deployment config")

    config = load_config(CONFIG_FILE)
    config_val("harness_arn", config["harness_arn"])
    config_val("region", config["region"])

    harness_arn = config["harness_arn"]
    region = config["region"]
    session_id = new_session_id()
    config_val("session_id", session_id)

    # ── Step 2: Ask agent to create and run a Python script ───────────────────
    step_header(2, 5, "Ask agent to write and run code")

    prompt = "Create a Python script called fibonacci.py that calculates the first 20 Fibonacci numbers and prints them. Then run it."
    prompt_display(prompt)
    print()

    text, tool_calls = invoke_harness_prompt(harness_arn, session_id, prompt, region)
    response_display(text)
    if tool_calls:
        info(f"Tool calls: {', '.join(tool_calls)}")
    print()

    # ── Step 3: Ask agent what files exist ────────────────────────────────────
    step_header(3, 5, "Ask agent to list its files")

    prompt2 = "Show me the files you created. List them with their sizes."
    prompt_display(prompt2)
    print()

    text2, tool_calls2 = invoke_harness_prompt(harness_arn, session_id, prompt2, region)
    response_display(text2)
    if tool_calls2:
        info(f"Tool calls: {', '.join(tool_calls2)}")
    print()

    # ── Step 4: Verify with ExecuteCommand ────────────────────────────────────
    step_header(4, 5, "Verify via ExecuteCommand (direct shell)")

    info("Bypassing agent loop to inspect the VM directly:\n")

    stdout, stderr, exit_code = execute_command(harness_arn, session_id, "ls -la *.py", region)
    if stdout:
        for line in stdout.strip().split("\n"):
            print(f"    {GREEN}{line}{RESET}")
    print()

    info("Running fibonacci.py directly:")
    stdout, stderr, exit_code = execute_command(harness_arn, session_id, "python3 fibonacci.py", region)
    if stdout:
        for line in stdout.strip().split("\n"):
            print(f"    {GREEN}{line}{RESET}")
    if stderr:
        for line in stderr.strip().split("\n"):
            print(f"    {YELLOW}{line}{RESET}")
    print(f"    {DIM}exit_code={exit_code}{RESET}")

    # ── Step 5: Summary ───────────────────────────────────────────────────────
    step_header(5, 5, "Summary")

    success("Agent used built-in file_operations + shell tools")
    info("The harness VM is isolated — files persist within the session")
    info("ExecuteCommand confirms files exist without going through the agent loop")

    done("python cleanup.py")


if __name__ == "__main__":
    main()
