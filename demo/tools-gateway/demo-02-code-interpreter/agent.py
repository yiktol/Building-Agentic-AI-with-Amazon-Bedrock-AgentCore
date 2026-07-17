"""
Demo 2: Strands Agent with code execution capability.

The agent receives natural language questions, generates Python code
to solve them, and executes it. This demonstrates the Code Interpreter
pattern where the LLM writes and runs code to verify answers.

For production: use AgentCore Code Interpreter (managed sandbox).
For this demo: executes in the runtime's microVM (already isolated).
"""

import json
import io
import os
import sys
import traceback
import contextlib

from strands import Agent, tool
from strands.models import BedrockModel
from bedrock_agentcore.runtime import BedrockAgentCoreApp

app = BedrockAgentCoreApp()


@tool
def execute_python(code: str, description: str = "") -> str:
    """Execute Python code and return the output.

    Use this tool to run calculations, data analysis, or verify answers.
    The code runs in an isolated environment.

    Args:
        code: Python source code to execute.
        description: Brief description of what the code does.

    Returns:
        JSON with the code executed, stdout output, and any errors.
    """
    print(f"\n{'─' * 50}")
    print(f"[Code Execution] {description or 'Running code:'}")
    print(f"{'─' * 50}")
    print(code)
    print(f"{'─' * 50}")

    # Capture stdout
    stdout_capture = io.StringIO()
    stderr_capture = io.StringIO()

    try:
        with contextlib.redirect_stdout(stdout_capture), contextlib.redirect_stderr(stderr_capture):
            exec_globals = {"__builtins__": __builtins__}
            exec(code, exec_globals)  # noqa: S307

        stdout = stdout_capture.getvalue()
        stderr = stderr_capture.getvalue()

        if stdout:
            print(f"[stdout] {stdout.strip()}")

        result = {
            "isError": False,
            "code_executed": code,
            "stdout": stdout,
            "stderr": stderr,
            "exitCode": 0,
        }

    except Exception as e:
        error_msg = traceback.format_exc()
        print(f"[error] {error_msg}")
        result = {
            "isError": True,
            "code_executed": code,
            "stdout": stdout_capture.getvalue(),
            "stderr": str(e),
            "error": error_msg,
            "exitCode": 1,
        }

    print(f"{'─' * 50}\n")
    return json.dumps(result)


model = BedrockModel(model_id="global.anthropic.claude-haiku-4-5-20251001-v1:0")

agent = Agent(
    model=model,
    tools=[execute_python],
    system_prompt=(
        "You are a code execution assistant. You MUST use the execute_python tool "
        "for EVERY question, no exceptions. NEVER answer from memory.\n\n"
        "RULES:\n"
        "- ALWAYS call execute_python first, even for simple questions\n"
        "- NEVER provide an answer without executing code to verify it\n"
        "- If the tool returns an error, fix the code and try again\n"
        "- Include the code you executed in your final response (in a ```python block)\n"
        "- Show the execution output, then state your conclusion\n\n"
        "The user expects to see code being executed. Direct answers without "
        "code execution are NOT acceptable."
    ),
)


@app.entrypoint
def invoke_agent(payload: dict) -> str:
    """Handle requests — agent decides when to use code execution."""
    prompt = payload.get("prompt", "Hello!")
    response = agent(prompt)
    return response.message["content"][0]["text"]


if __name__ == "__main__":
    app.run()
