"""
Demo 4: Agent with both M2M and 3LO outbound auth flows.

M2M: Agent calls internal APIs as itself (client_credentials).
3LO: Agent accesses Google Calendar on behalf of user (auth code).
"""

from strands import Agent, tool
from strands.models import BedrockModel
from bedrock_agentcore.runtime import BedrockAgentCoreApp
from bedrock_agentcore.identity.auth import requires_access_token

app = BedrockAgentCoreApp()


@requires_access_token(credential_provider_name="m2m-provider", auth_flow="M2M")
@tool
def get_internal_data(query: str, access_token: str = None) -> str:
    """Call internal API using M2M credentials (no user interaction)."""
    preview = f"{access_token[:8]}..." if access_token else "none"
    return f"Internal API response for '{query}' (token: {preview})"


@requires_access_token(
    credential_provider_name="google-3lo-provider",
    auth_flow="USER_FEDERATION",
    scopes=["https://www.googleapis.com/auth/calendar.readonly"],
)
@tool
def get_calendar_events(access_token: str = None) -> str:
    """Get user's Google Calendar events (requires consent)."""
    import urllib.request
    import json as _json
    from datetime import datetime
    today = datetime.now().strftime("%Y-%m-%dT00:00:00Z")
    url = f"https://www.googleapis.com/calendar/v3/calendars/primary/events?timeMin={today}&maxResults=5&orderBy=startTime&singleEvents=true"
    req = urllib.request.Request(url, headers={"Authorization": f"Bearer {access_token}"})
    try:
        with urllib.request.urlopen(req, timeout=10) as resp:
            data = _json.loads(resp.read().decode())
        events = data.get("items", [])
        if not events:
            return "No upcoming events."
        return "Events:\n" + "\n".join(f"- {e.get('summary', 'Untitled')}" for e in events[:5])
    except Exception as e:
        return f"Calendar error: {e}"


model = BedrockModel(model_id="global.anthropic.claude-haiku-4-5-20251001-v1:0")
agent = Agent(model=model, tools=[get_internal_data, get_calendar_events],
              system_prompt="You have two tools: get_internal_data (M2M) and get_calendar_events (user consent). Use appropriately.")


@app.entrypoint
def invoke_agent(payload):
    response = agent(payload.get("prompt", "Hello!"))
    return response.message["content"][0]["text"]


if __name__ == "__main__":
    app.run()
