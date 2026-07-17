"""
Demo 2: Invoke the Code Interpreter agent.

The agent receives natural language questions and uses Code Interpreter
to write + execute Python code to answer them.

Usage:
    python invoke.py
    python invoke.py "What are the first 10 prime numbers?"
"""

import json
import sys
import os

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))
from shared.colors import banner, section, success, info, config_val, prompt_display, response_display, done

import boto3

# Colors for code display
CYAN = "\033[96m"
GREEN = "\033[92m"
YELLOW = "\033[93m"
DIM = "\033[2m"
RESET_ALL = "\033[0m"
BOLD_W = "\033[1;97m"


def display_with_code(body: str):
    """Display agent response with code blocks highlighted."""
    # Try to parse as JSON string (agent may return quoted string)
    text = body
    try:
        parsed = json.loads(body)
        if isinstance(parsed, str):
            text = parsed
    except (json.JSONDecodeError, TypeError):
        pass

    lines = text.split("\\n") if "\\n" in text else text.split("\n")
    in_code_block = False

    for line in lines:
        stripped = line.strip()
        if stripped.startswith("```python") or stripped.startswith("```"):
            if not in_code_block:
                in_code_block = True
                print(f"    {DIM}{'─' * 45}{RESET_ALL}")
                print(f"    {CYAN}[Generated Code]{RESET_ALL}")
                continue
            else:
                in_code_block = False
                print(f"    {DIM}{'─' * 45}{RESET_ALL}")
                continue

        if in_code_block:
            print(f"    {YELLOW}{line}{RESET_ALL}")
        else:
            if stripped:
                print(f"    {GREEN}{line}{RESET_ALL}")


def main():
    os.chdir(os.path.dirname(os.path.abspath(__file__)))
    with open("runtime_config.json") as f:
        config = json.load(f)

    client = boto3.client("bedrock-agentcore", region_name=config["region"])

    if len(sys.argv) > 1:
        prompts = [" ".join(sys.argv[1:])]
    else:
        prompts = [
            "What is the largest prime number less than 100?",
            "Calculate the factorial of 15 and show all the digits.",
            "Generate a list of the first 8 Fibonacci numbers.",
        ]

    banner("Demo 2: Code Interpreter Agent")
    config_val("Runtime", config["runtime_arn"])
    info("Agent uses execute_python → Code Interpreter sandbox")

    for i, prompt in enumerate(prompts, 1):
        section(f"Prompt {i}/{len(prompts)}")
        prompt_display(prompt)
        response = client.invoke_agent_runtime(
            agentRuntimeArn=config["runtime_arn"],
            payload=json.dumps({"prompt": prompt}).encode(),
            contentType="application/json",
            accept="application/json",
        )
        body = response["response"].read().decode()

        # Display with code blocks highlighted
        display_with_code(body)
        success("Agent wrote + executed code to verify the answer")

    done()
    info("Key: Agent decides WHEN to use Code Interpreter")
    info("  • LLM generates code → sandbox executes → result returned")
    info("  • Isolated per session (no data leakage)")
    print()


if __name__ == "__main__":
    main()
