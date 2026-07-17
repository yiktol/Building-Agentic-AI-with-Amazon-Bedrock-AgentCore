"""
Demo 3: Agent with OAuth 3LO outbound auth (GitHub).

Uses @requires_access_token for user-delegated GitHub access.
First call returns consent URL; after consent, token is cached.
"""

from strands import Agent, tool
from strands.models import BedrockModel
from bedrock_agentcore.runtime import BedrockAgentCoreApp
from bedrock_agentcore.identity.auth import requires_access_token

app = BedrockAgentCoreApp()


@requires_access_token(
    credential_provider_name="github-provider",
    auth_flow="USER_FEDERATION",
    scopes=["repo", "read:user"],
)
@tool
def list_github_repos(access_token: str = None) -> str:
    """List user's private GitHub repos using delegated access."""
    import urllib.request
    import json as _json
    req = urllib.request.Request(
        "https://api.github.com/user/repos?type=private&per_page=5",
        headers={"Authorization": f"Bearer {access_token}", "Accept": "application/vnd.github.v3+json"},
    )
    with urllib.request.urlopen(req) as resp:
        repos = _json.loads(resp.read().decode())
    names = [r["full_name"] for r in repos[:5]]
    return f"Private repos: {', '.join(names) if names else 'none found'}"


model = BedrockModel(model_id="global.anthropic.claude-haiku-4-5-20251001-v1:0")
agent = Agent(model=model, tools=[list_github_repos],
              system_prompt="You help users with their GitHub repos.")


@app.entrypoint
def invoke_agent(payload):
    response = agent(payload.get("prompt", "Hello!"))
    return response.message["content"][0]["text"]


if __name__ == "__main__":
    app.run()
