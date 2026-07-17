"""
Demo 5: IAM-Scoped Memory Access.

This is NOT a deployed agent — this demo runs locally to show IAM
fine-grained access control on memory operations.

Demonstrates:
- IAM conditions on bedrock-agentcore:actorId
- IAM conditions on bedrock-agentcore:namespace
- One user cannot access another user's memory
"""

# This demo does not use BedrockAgentCoreApp — it's a pure SDK demonstration.
# See deploy.py and invoke.py for the actual flow.
