"""
Demo 2: LangGraph + Amazon Bedrock on AgentCore Runtime

This agent demonstrates:
- Framework agnosticism — same AgentCore deployment, different framework
- LangGraph explicit state graph (nodes, edges, conditional routing)
- Tool calling with LangChain tools
"""

from langgraph.graph import StateGraph, MessagesState
from langgraph.prebuilt import ToolNode, tools_condition
from langchain_core.tools import tool
from langchain_core.messages import HumanMessage, SystemMessage
from bedrock_agentcore.runtime import BedrockAgentCoreApp
import operator
import math


app = BedrockAgentCoreApp()


# ── Tools ────────────────────────────────────────────────────────────────────

@tool
def calculator(expression: str) -> str:
    """Evaluate a mathematical expression.

    Args:
        expression: A math expression (e.g., "2 + 3 * 4", "sqrt(16)", "sin(pi/2)")

    Returns:
        The result of the calculation as a string.
    """
    try:
        safe_dict = {
            "__builtins__": {},
            "abs": abs, "round": round, "min": min, "max": max,
            "pow": pow, "sqrt": math.sqrt, "sin": math.sin,
            "cos": math.cos, "tan": math.tan, "log": math.log,
            "log10": math.log10, "exp": math.exp,
            "pi": math.pi, "e": math.e,
            "ceil": math.ceil, "floor": math.floor,
        }
        result = eval(expression, safe_dict)  # noqa: S307
        return str(result)
    except ZeroDivisionError:
        return "Error: Division by zero"
    except Exception as e:
        return f"Error: {str(e)}"


@tool
def get_weather(city: str) -> str:
    """Get weather for a city.

    Args:
        city: City name.

    Returns:
        Weather description.
    """
    weather_data = {
        "seattle": "rainy, 55°F",
        "miami": "sunny, 85°F",
        "new york": "cloudy, 62°F",
    }
    return weather_data.get(city.lower(), f"sunny, 72°F in {city}")


# ── LangGraph Agent ──────────────────────────────────────────────────────────

def create_agent():
    """Create a LangGraph ReAct agent with state graph."""
    from langchain_aws import ChatBedrock

    llm = ChatBedrock(
        model_id="global.anthropic.claude-haiku-4-5-20251001-v1:0",
        model_kwargs={"temperature": 0.1},
    )

    tools = [calculator, get_weather]
    llm_with_tools = llm.bind_tools(tools)

    system_message = (
        "You are a helpful assistant that can perform calculations "
        "and check the weather. Be concise."
    )

    def chatbot(state: MessagesState):
        messages = state["messages"]
        if not messages or not isinstance(messages[0], SystemMessage):
            messages = [SystemMessage(content=system_message)] + messages
        response = llm_with_tools.invoke(messages)
        return {"messages": [response]}

    # Build the state graph
    graph_builder = StateGraph(MessagesState)
    graph_builder.add_node("chatbot", chatbot)
    graph_builder.add_node("tools", ToolNode(tools))
    graph_builder.add_conditional_edges("chatbot", tools_condition)
    graph_builder.add_edge("tools", "chatbot")
    graph_builder.set_entry_point("chatbot")

    return graph_builder.compile()


agent = create_agent()


# ── AgentCore Entrypoint ─────────────────────────────────────────────────────

@app.entrypoint
def invoke_agent(payload: dict) -> str:
    """Handle POST /invocations — identical interface to Demo 1."""
    prompt = payload.get("prompt", "Hello!")
    print(f"[LangGraph Agent] Received: {prompt}")

    result = agent.invoke({"messages": [HumanMessage(content=prompt)]})
    return result["messages"][-1].content


if __name__ == "__main__":
    app.run()
