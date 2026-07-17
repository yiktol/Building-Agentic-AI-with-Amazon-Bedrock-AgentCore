"""
Demo 4: Async Agent — long-running background tasks.

Demonstrates:
- app.add_async_task() to register background work
- app.complete_async_task() to mark completion
- Agent responds immediately while work continues in background
- Session stays active for up to 8 hours
"""

import threading
import time

from bedrock_agentcore.runtime import BedrockAgentCoreApp
from strands import Agent, tool
from strands.models.bedrock import BedrockModel

app = BedrockAgentCoreApp()


# ── Background Task Tool ─────────────────────────────────────────────────────

@tool
def generate_report(topic: str, duration_seconds: int = 10) -> str:
    """Start a background report generation task.

    The report is generated asynchronously — the user gets an immediate
    response with a task ID and can check status later.

    Args:
        topic: The topic to generate a report about.
        duration_seconds: How long the report takes to generate (simulated).

    Returns:
        A message with the task ID.
    """
    # Register the async task with AgentCore
    task_id = app.add_async_task("report_generation", {"topic": topic})

    def background_work():
        """Simulate long-running report generation."""
        print(f"[Background] Starting report on '{topic}' (task: {task_id})")
        time.sleep(duration_seconds)  # Simulate work
        print(f"[Background] Completed report on '{topic}' (task: {task_id})")
        app.complete_async_task(task_id)

    # Start work in background thread
    threading.Thread(target=background_work, daemon=True).start()

    return (
        f"Started background report generation (Task ID: {task_id}). "
        f"Topic: '{topic}'. Estimated time: {duration_seconds} seconds. "
        f"The agent status is now BUSY while the task runs."
    )


@tool
def get_task_status() -> str:
    """Check the status of all running async tasks.

    Returns:
        A JSON string with current task information including task IDs and their statuses.
    """
    import json
    task_info = app.get_async_task_info()
    return json.dumps({"message": "Current task information", "task_info": task_info}, default=str)


@tool
def quick_summary(topic: str) -> str:
    """Generate a quick summary immediately (no background task).

    Args:
        topic: Topic to summarize.

    Returns:
        A brief summary.
    """
    return f"Quick summary for '{topic}': This is a synchronous response that returns immediately."


# ── Agent ────────────────────────────────────────────────────────────────────

model = BedrockModel(model_id="global.anthropic.claude-haiku-4-5-20251001-v1:0")

agent = Agent(
    model=model,
    tools=[generate_report, quick_summary, get_task_status],
    system_prompt=(
        "You are a report generation assistant. You have three tools:\n"
        "1. generate_report: Starts a long-running background task (async)\n"
        "2. quick_summary: Returns immediately (sync)\n"
        "3. get_task_status: Check status of running async tasks\n\n"
        "When the user asks for a detailed report, use generate_report. "
        "When they want a quick answer, use quick_summary. "
        "When they ask about task status, use get_task_status. "
        "Always tell the user the task ID when starting a background task."
    ),
)


@app.entrypoint
def invoke_agent(payload: dict) -> str:
    """Handle requests — async tasks continue after response."""
    prompt = payload.get("prompt", "Hello!")
    print(f"[Async Agent] Received: {prompt}")
    response = agent(prompt)
    return response.message["content"][0]["text"]


if __name__ == "__main__":
    app.run()
