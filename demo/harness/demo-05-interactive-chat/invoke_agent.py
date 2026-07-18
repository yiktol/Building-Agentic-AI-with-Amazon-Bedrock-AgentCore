"""Demo 05: Interactive Chat — Full interactive chatbot with persistent session."""

import os
import sys

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from shared.colors import (
    banner, section, success, info, config_val, error, done,
    GREEN, YELLOW, WHITE, BOLD, DIM, RESET, CYAN, MAGENTA,
)
from shared.harness_helpers import (
    load_config, invoke_harness_streaming, execute_command, new_session_id,
)

CONFIG_FILE = os.path.join(os.path.dirname(__file__), "runtime_config.json")


def main():
    banner("Demo 05: Interactive Chat — AgentCore Harness")

    config = load_config(CONFIG_FILE)
    harness_arn = config["harness_arn"]
    region = config["region"]
    session_id = new_session_id()

    config_val("harness_arn", harness_arn)
    config_val("session_id", session_id)

    print(f"\n  {DIM}Commands:{RESET}")
    print(f"  {DIM}  quit          — exit chat{RESET}")
    print(f"  {DIM}  exec <cmd>    — run shell command on microVM{RESET}")
    print(f"  {DIM}  new session   — start fresh session (clean slate){RESET}")
    print(f"  {DIM}  session       — show current session ID{RESET}")
    print()

    turn_count = 0

    while True:
        try:
            user_input = input(f"  {CYAN}{BOLD}You:{RESET} ").strip()
        except (KeyboardInterrupt, EOFError):
            print()
            break

        if not user_input:
            continue

        if user_input.lower() in ("quit", "exit", "q"):
            break

        if user_input.lower() == "new session":
            session_id = new_session_id()
            turn_count = 0
            success(f"New session: {session_id}")
            info("Fresh VM state — previous files and context are gone")
            continue

        if user_input.lower() == "session":
            config_val("session_id", session_id)
            info(f"Turns in this session: {turn_count}")
            continue

        if user_input.lower().startswith("exec "):
            cmd = user_input[5:].strip()
            info(f"ExecuteCommand: {cmd}")
            stdout, stderr, exit_code = execute_command(
                harness_arn, session_id, cmd, region
            )
            if stdout:
                print(f"  {GREEN}{stdout}{RESET}")
            if stderr:
                print(f"  {YELLOW}{stderr}{RESET}")
            print(f"  {DIM}exit_code={exit_code}{RESET}")
            continue

        # Regular prompt → invoke harness
        turn_count += 1
        print(f"  {GREEN}Agent:{RESET} ", end="", flush=True)
        text, tool_calls = invoke_harness_streaming(
            harness_arn=harness_arn,
            session_id=session_id,
            prompt=user_input,
            region=region,
            print_stream=True,
        )
        if tool_calls:
            print(f"  {DIM}[tools: {', '.join(tool_calls)}]{RESET}")
        print()

    print(f"\n  {DIM}Session turns: {turn_count}{RESET}")
    done()


if __name__ == "__main__":
    main()
