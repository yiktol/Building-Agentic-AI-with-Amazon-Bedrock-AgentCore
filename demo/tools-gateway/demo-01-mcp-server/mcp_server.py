"""
Demo 1: MCP Server hosted on AgentCore Runtime.

Exposes tools via Model Context Protocol (stateless streamable-HTTP).
AgentCore Runtime expects: 0.0.0.0:8000/mcp
"""

from mcp.server.fastmcp import FastMCP

mcp = FastMCP("demo-tools", host="0.0.0.0", stateless_http=True, json_response=True)  # nosec B104


@mcp.tool()
def add_numbers(a: float, b: float) -> float:
    """Add two numbers together."""
    return a + b


@mcp.tool()
def multiply_numbers(a: float, b: float) -> float:
    """Multiply two numbers."""
    return a * b


@mcp.tool()
def get_weather(city: str) -> str:
    """Get weather for a city."""
    data = {"seattle": "rainy 55°F", "miami": "sunny 85°F", "tokyo": "clear 68°F"}
    return data.get(city.lower(), f"sunny 72°F in {city}")


@mcp.tool()
def greet(name: str, language: str = "english") -> str:
    """Greet a person in a specified language."""
    greetings = {
        "english": f"Hello, {name}!",
        "spanish": f"¡Hola, {name}!",
        "french": f"Bonjour, {name}!",
    }
    return greetings.get(language.lower(), f"Hello, {name}!")


if __name__ == "__main__":
    mcp.run(transport="streamable-http")
