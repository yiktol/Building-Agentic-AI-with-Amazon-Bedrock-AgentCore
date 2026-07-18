"""Demo 02: Execute Command — Run shell commands on the agent's microVM."""

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


def run_cmd(harness_arn, session_id, cmd, region):
    """Run a command and display results."""
    info(f"$ {cmd}")
    stdout, stderr, exit_code = execute_command(harness_arn, session_id, cmd, region)
    if stdout:
        for line in stdout.strip().split("\n"):
            print(f"    {GREEN}{line}{RESET}")
    if stderr:
        for line in stderr.strip().split("\n"):
            print(f"    {YELLOW}{line}{RESET}")
    print(f"    {DIM}exit_code={exit_code}{RESET}")
    print()


def main():
    banner("Demo 02: Execute Command — Shell on MicroVM")

    # ── Step 1: Load config ───────────────────────────────────────────────────
    step_header(1, 4, "Load deployment config")

    config = load_config(CONFIG_FILE)
    config_val("harness_arn", config["harness_arn"])
    config_val("region", config["region"])

    harness_arn = config["harness_arn"]
    region = config["region"]
    session_id = new_session_id()
    config_val("session_id", session_id)

    # ── Step 2: Ask agent to create files ─────────────────────────────────────
    step_header(2, 4, "Ask agent to create files")

    prompt = "Create a file called hello.md with the content '# Hello from Harness' and a Python script called greet.py that prints 'Hello from the microVM!'"
    prompt_display(prompt)
    print()

    text, tool_calls = invoke_harness_prompt(harness_arn, session_id, prompt, region)
    response_display(text)
    if tool_calls:
        info(f"Tool calls: {', '.join(tool_calls)}")

    # ── Step 3: Run shell commands via ExecuteCommand ─────────────────────────
    step_header(3, 4, "Execute commands on microVM")

    info("These commands bypass the agent loop — direct shell access.\n")

    run_cmd(harness_arn, session_id, "ls -la", region)
    run_cmd(harness_arn, session_id, "cat hello.md", region)
    run_cmd(harness_arn, session_id, "python3 greet.py", region)
    run_cmd(harness_arn, session_id, "python3 --version", region)
    run_cmd(harness_arn, session_id, "uname -a", region)

    # ── Step 4: Summary ───────────────────────────────────────────────────────
    step_header(4, 4, "Summary")

    success("ExecuteCommand lets you run arbitrary shell commands on the microVM")
    info("Key difference: invoke_harness = agent loop; ExecuteCommand = direct shell")
    info("Both share the same filesystem and session state")

    done("python cleanup.py")


if __name__ == "__main__":
    main()
