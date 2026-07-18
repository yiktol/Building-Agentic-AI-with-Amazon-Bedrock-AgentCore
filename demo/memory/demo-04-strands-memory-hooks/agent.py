"""
Demo 4: Memory Hooks — Agent Code Reference.

This file shows what a deployed agent with HookProvider would look like.
In this demo, we simulate hooks LOCALLY via invoke.py and invoke_agent.py
to avoid runtime init timeout issues.

The hook pattern is:
  - MessageAdded → retrieve relevant memories (before LLM call)
  - AfterInvocation → save turn to STM (after response)

For a deployed version, see the temp/agentcore-samples reference:
  01-features/04-manage-context-of-your-agent/memory/01-short-term-memory/
  examples/single-agent/with-strands-agent/
"""

# The local agent implementation is in invoke.py and invoke_agent.py.
# They simulate hooks with explicit SDK calls before/after each turn.
