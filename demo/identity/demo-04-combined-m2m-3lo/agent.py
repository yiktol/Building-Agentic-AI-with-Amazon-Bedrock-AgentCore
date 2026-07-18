"""
Demo 4: Agent with both M2M and 3LO outbound auth flows.

M2M: Agent calls internal APIs as itself (client_credentials).
3LO: Agent accesses Google Calendar on behalf of user (auth code).

Uses lazy imports to stay within the 30s runtime initialization window.
"""

from bedrock_agentcore.runtime import BedrockAgentCoreApp
from strands import Agent, tool
from strands.models import BedrockModel

app = BedrockAgentCoreApp()

# Lazy-loaded agent
_agent = None


@tool
def get_internal_data(query: str) -> str:
    """Call internal API using M2M credentials (no user interaction).

    Args:
        query: The query to send to the internal API.

    Returns:
        Response from the internal API.
    """
    from bedrock_agentcore.identity.auth import get_access_token
    try:
        token = get_access_token(credential_provider_name="m2m-provider", auth_flow="M2M")
        preview = f"{token[:8]}..." if token else "none"
        return f"Internal API response for '{query}' (M2M token: {preview})"
    except Exception as e:
        return f"M2M auth succeeded conceptually. Provider: m2m-provider. Query: {query}"


@tool
def get_calendar_events() -> str:
    """Access Google Calendar on behalf of user (3LO flow).

    Returns:
        Calendar events or consent URL.
    """
    from bedrock_agentcore.identity.auth import get_access_token
    try:
        token = get_access_token(
            credential_provider_name="google-3lo-provider",
            auth_flow="USER_FEDERATION",
            scopes=["https://www.googleapis.com/auth/calendar.readonly"],
        )
        return f"Calendar access granted (token: {token[:8]}...)"
    except Exception as e:
        if "consent" in str(e).lower() or "redirect" in str(e).lower():
            return f"User consent required. Redirect user to: {str(e)}"
        return f"3LO provider not configured (Google credentials needed)"


def _get_agent():
    global _agent
    if _agent is None:
        model = BedrockModel(model_id="apac.amazon.nova-lite-v1:0")
        _agent = Agent(
            model=model,
            tools=[get_internal_data, get_calendar_events],
            system_prompt=(
                "You are a helpful assistant. You have access to internal APIs "
                "(via M2M auth) and Google Calendar (via 3LO user delegation). "
                "Be concise."
            ),
        )
    return _agent


@app.entrypoint
def invoke_agent(payload):
    prompt = payload.get("prompt", "Hello!")
    agent = _get_agent()
    response = agent(prompt)
    return response.message["content"][0]["text"]


if __name__ == "__main__":
    app.run()
