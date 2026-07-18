"""
Demo 3: Memory as Tool — Agent Code Reference.

This file shows what a deployed agent with AgentCoreMemoryToolProvider
would look like. In this demo, we run the agent LOCALLY via invoke.py
and invoke_agent.py to avoid runtime init timeout issues.

For a deployed version, see the temp/agentcore-samples reference:
  01-features/04-manage-context-of-your-agent/memory/01-short-term-memory/
  examples/single-agent/with-strands-agent/
"""

# The local agent implementation is in invoke.py and invoke_agent.py.
# They use custom @tool functions (remember, recall) backed by MemoryClient.
