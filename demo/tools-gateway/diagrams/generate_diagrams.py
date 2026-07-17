"""Generate architecture diagrams for Module 04 Tools & Gateway demos."""

import os
os.chdir(os.path.dirname(os.path.abspath(__file__)))

from diagrams import Diagram, Cluster, Edge
from diagrams.custom import Custom

ICONS = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "..", "..", "aws-icons"))
IC_RUNTIME = os.path.join(ICONS, "aws-agentcore-icons", "AgentCoreRuntime.png")
IC_GATEWAY = os.path.join(ICONS, "aws-agentcore-icons", "AgentCoreGateway.png")
IC_AGENTCORE = os.path.join(ICONS, "aws-agentcore-icons", "AgentCore.png")
IC_BEDROCK = os.path.join(ICONS, "Architecture-Service-Icons_04302026", "Arch_Artificial-Intelligence", "48", "Arch_Amazon-Bedrock_48.png")
IC_LAMBDA = os.path.join(ICONS, "Architecture-Service-Icons_04302026", "Arch_Compute", "48", "Arch_AWS-Lambda_48.png")
IC_USER = os.path.join(ICONS, "Resource-Icons_04302026", "Res_General-Icons", "Res_48_Light", "Res_Client_48_Light.png")
IC_GEAR = os.path.join(ICONS, "Resource-Icons_04302026", "Res_General-Icons", "Res_48_Light", "Res_Gear_48_Light.png")

GRAPH_ATTR = {"dpi": "300", "fontsize": "11", "fontname": "Helvetica", "bgcolor": "white", "pad": "0.8", "nodesep": "1.0", "ranksep": "1.2", "splines": "curved"}
CLUSTER_ATTR = {"fontsize": "12", "fontname": "Helvetica Bold", "style": "rounded", "bgcolor": "#f8f9fa", "pencolor": "#232f3e", "penwidth": "1.5"}
EDGE_ATTR = {"fontsize": "9", "fontname": "Helvetica"}
C_INVOKE, C_OK, C_DASH, C_MCP, C_DENY = "#0073bb", "#1b660f", "#666666", "#8c4fff", "#d13212"


def diagram_01():
    with Diagram("", filename="demo-01-architecture", show=False, direction="LR", outformat="png",
                 graph_attr={**GRAPH_ATTR, "label": "Demo 1: MCP Server on AgentCore Runtime\n", "labelloc": "t", "fontsize": "16"}):
        client = Custom("MCP Client\n(boto3)", IC_USER)
        with Cluster("AgentCore Runtime (microVM)", graph_attr={**CLUSTER_ATTR, "bgcolor": "#e8f5e9"}):
            mcp = Custom("FastMCP Server\nport 8000 /mcp", IC_RUNTIME)
        with Cluster("MCP Tools", graph_attr={**CLUSTER_ATTR, "bgcolor": "#fff3e0"}):
            t1 = Custom("add_numbers", IC_GEAR)
            t2 = Custom("multiply", IC_GEAR)
            t3 = Custom("get_weather", IC_GEAR)
            t4 = Custom("greet", IC_GEAR)
        client >> Edge(label="JSON-RPC 2.0\ntools/list, tools/call", color=C_MCP, style="bold", **EDGE_ATTR) >> mcp
        mcp >> Edge(color=C_OK, **EDGE_ATTR) >> t1
        mcp >> Edge(color=C_OK, **EDGE_ATTR) >> t2
        mcp >> Edge(color=C_OK, **EDGE_ATTR) >> t3
        mcp >> Edge(color=C_OK, **EDGE_ATTR) >> t4


def diagram_02():
    with Diagram("", filename="demo-02-architecture", show=False, direction="LR", outformat="png",
                 graph_attr={**GRAPH_ATTR, "label": "Demo 2: AgentCore Code Interpreter\n", "labelloc": "t", "fontsize": "16"}):
        user = Custom("Agent /\nDeveloper", IC_USER)
        with Cluster("AgentCore Code Interpreter\n(Managed Sandbox)", graph_attr={**CLUSTER_ATTR, "bgcolor": "#e8f5e9"}):
            ci = Custom("Python 3.12\nRuntime", IC_RUNTIME)
            with Cluster("Session (isolated)", graph_attr={**CLUSTER_ATTR, "bgcolor": "#fff3e0", "style": "dashed,rounded"}):
                shell = Custom("Shell", IC_GEAR)
                fs = Custom("Filesystem", IC_GEAR)
        user >> Edge(label="executeCode\nwriteFiles\nexecuteCommand", color=C_INVOKE, style="bold", **EDGE_ATTR) >> ci
        ci >> Edge(color=C_OK, **EDGE_ATTR) >> shell
        ci >> Edge(color=C_OK, **EDGE_ATTR) >> fs
        ci >> Edge(label="stdout/stderr\nresult", color=C_OK, style="bold", **EDGE_ATTR) >> user


def diagram_03():
    with Diagram("", filename="demo-03-architecture", show=False, direction="LR", outformat="png",
                 graph_attr={**GRAPH_ATTR, "label": "Demo 3: AgentCore Gateway — Lambda Targets\n", "labelloc": "t", "fontsize": "16"}):
        client = Custom("Agent /\nMCP Client", IC_USER)
        with Cluster("AgentCore Gateway", graph_attr={**CLUSTER_ATTR, "bgcolor": "#eef6ff"}):
            gw = Custom("Gateway\n/mcp endpoint", IC_GATEWAY)
        with Cluster("Lambda Targets", graph_attr={**CLUSTER_ATTR, "bgcolor": "#fff3e0"}):
            l1 = Custom("OrderService\nget_order\nlist_orders", IC_LAMBDA)
            l2 = Custom("WeatherService\nget_weather", IC_LAMBDA)
            l3 = Custom("CalculatorService\ncalculate", IC_LAMBDA)
        client >> Edge(label="tools/list\ntools/call", color=C_MCP, style="bold", **EDGE_ATTR) >> gw
        gw >> Edge(label="invoke", color=C_INVOKE, **EDGE_ATTR) >> l1
        gw >> Edge(label="invoke", color=C_INVOKE, **EDGE_ATTR) >> l2
        gw >> Edge(label="invoke", color=C_INVOKE, **EDGE_ATTR) >> l3


def diagram_04():
    with Diagram("", filename="demo-04-architecture", show=False, direction="LR", outformat="png",
                 graph_attr={**GRAPH_ATTR, "label": "Demo 4: Gateway Semantic Search\n", "labelloc": "t", "fontsize": "16"}):
        agent = Custom("Agent", IC_USER)
        with Cluster("AgentCore Gateway (300+ tools)", graph_attr={**CLUSTER_ATTR, "bgcolor": "#eef6ff"}):
            gw = Custom("Gateway\n+ Search Index", IC_GATEWAY)
            with Cluster("All Targets", graph_attr={**CLUSTER_ATTR, "bgcolor": "#f8f9fa", "style": "dashed,rounded"}):
                tools = Custom("300+ tools\nacross targets", IC_GEAR)
        results = Custom("Top 10\nRelevant Tools", IC_AGENTCORE)
        agent >> Edge(label="search: \"find order info\"", color=C_MCP, style="bold", **EDGE_ATTR) >> gw
        gw >> Edge(color=C_DASH, style="dashed", **EDGE_ATTR) >> tools
        gw >> Edge(label="returns top matches", color=C_OK, style="bold", **EDGE_ATTR) >> results
        results >> Edge(color=C_OK, **EDGE_ATTR) >> agent


def diagram_05():
    with Diagram("", filename="demo-05-architecture", show=False, direction="LR", outformat="png",
                 graph_attr={**GRAPH_ATTR, "label": "Demo 5: Cedar Policy Enforcement\n", "labelloc": "t", "fontsize": "16"}):
        agent = Custom("Agent", IC_USER)
        with Cluster("AgentCore Gateway", graph_attr={**CLUSTER_ATTR, "bgcolor": "#eef6ff"}):
            gw = Custom("Gateway", IC_GATEWAY)
            with Cluster("Policy Engine\n(ENFORCE mode)", graph_attr={**CLUSTER_ATTR, "bgcolor": "#fce4ec", "pencolor": "#d13212"}):
                policy = Custom("Cedar Policies\npermit / forbid", IC_AGENTCORE)
        with Cluster("Lambda Targets", graph_attr={**CLUSTER_ATTR, "bgcolor": "#e8f5e9"}):
            allowed = Custom("WeatherService\n✓ PERMITTED", IC_LAMBDA)
        with Cluster("Blocked", graph_attr={**CLUSTER_ATTR, "bgcolor": "#ffebee", "style": "dashed,rounded"}):
            denied = Custom("OrderService\n✗ DENIED", IC_LAMBDA)
        agent >> Edge(label="tools/call", color=C_MCP, style="bold", **EDGE_ATTR) >> gw
        gw >> Edge(label="evaluate", color=C_DASH, **EDGE_ATTR) >> policy
        policy >> Edge(label="permit", color=C_OK, style="bold", **EDGE_ATTR) >> allowed
        policy >> Edge(label="forbid", color=C_DENY, style="bold", **EDGE_ATTR) >> denied


if __name__ == "__main__":
    print("Generating Module 04 diagrams (300 DPI)...\n")
    diagram_01(); print("  ✓ demo-01-architecture.png — MCP Server")
    diagram_02(); print("  ✓ demo-02-architecture.png — Code Interpreter")
    diagram_03(); print("  ✓ demo-03-architecture.png — Gateway Lambda")
    diagram_04(); print("  ✓ demo-04-architecture.png — Gateway Search")
    diagram_05(); print("  ✓ demo-05-architecture.png — Cedar Policy")
    print("\n✓ Done.")
