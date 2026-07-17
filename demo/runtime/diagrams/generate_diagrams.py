"""
Generate high-resolution architecture diagrams for Module 02 demos.

Uses the `diagrams` library with custom AWS AgentCore icons from aws-icons/.
Produces 300 DPI PNG files with curved edges for a polished visual.

Usage:
    cd demo/runtime/diagrams
    python generate_diagrams.py
"""

import os

os.chdir(os.path.dirname(os.path.abspath(__file__)))

from diagrams import Diagram, Cluster, Edge
from diagrams.custom import Custom

# ── Icon Paths ────────────────────────────────────────────────────────────────

ICONS = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "..", "..", "aws-icons"))

# AgentCore custom icons
IC_RUNTIME = os.path.join(ICONS, "aws-agentcore-icons", "AgentCoreRuntime.png")
IC_AGENTCORE = os.path.join(ICONS, "aws-agentcore-icons", "AgentCore.png")
IC_OBSERVABILITY = os.path.join(ICONS, "aws-agentcore-icons", "AgentCoreObservability.png")

# AWS service icons (48px)
IC_BEDROCK = os.path.join(ICONS, "Architecture-Service-Icons_04302026", "Arch_Artificial-Intelligence", "48", "Arch_Amazon-Bedrock_48.png")
IC_AGENTCORE_SVC = os.path.join(ICONS, "Architecture-Service-Icons_04302026", "Arch_Artificial-Intelligence", "48", "Arch_Amazon-Bedrock-AgentCore_48.png")
IC_S3 = os.path.join(ICONS, "Architecture-Service-Icons_04302026", "Arch_Storage", "48", "Arch_Amazon-Simple-Storage-Service_48.png")
IC_CLOUDWATCH = os.path.join(ICONS, "Architecture-Service-Icons_04302026", "Arch_Management-Tools", "48", "Arch_Amazon-CloudWatch_48.png")
IC_IAM = os.path.join(ICONS, "Architecture-Service-Icons_04302026", "Arch_Security-Identity", "48", "Arch_AWS-IAM-Identity-Center_48.png")

# Resource icons
IC_USER = os.path.join(ICONS, "Resource-Icons_04302026", "Res_General-Icons", "Res_48_Light", "Res_Client_48_Light.png")
IC_ROLE = os.path.join(ICONS, "Resource-Icons_04302026", "Res_Security-Identity", "Res_AWS-Identity-Access-Management_Role_48.png")
IC_LOGS = os.path.join(ICONS, "Resource-Icons_04302026", "Res_Management-Governance", "Res_Amazon-CloudWatch_Logs_48.png")
IC_GEAR = os.path.join(ICONS, "Resource-Icons_04302026", "Res_General-Icons", "Res_48_Light", "Res_Gear_48_Light.png")
IC_SERVER = os.path.join(ICONS, "Resource-Icons_04302026", "Res_General-Icons", "Res_48_Light", "Res_Server_48_Light.png")

# ── Diagram Styling ──────────────────────────────────────────────────────────

# High resolution, clean styling
GRAPH_ATTR = {
    "dpi": "300",
    "fontsize": "11",
    "fontname": "Helvetica",
    "bgcolor": "white",
    "pad": "0.8",
    "nodesep": "1.0",
    "ranksep": "1.2",
    "splines": "curved",
}

CLUSTER_ATTR = {
    "fontsize": "12",
    "fontname": "Helvetica Bold",
    "style": "rounded",
    "bgcolor": "#f8f9fa",
    "pencolor": "#232f3e",
    "penwidth": "1.5",
}

EDGE_ATTR = {
    "fontsize": "9",
    "fontname": "Helvetica",
}

# Edge colors
COLOR_PRIMARY = "#232f3e"
COLOR_INVOKE = "#0073bb"
COLOR_RESPONSE = "#1b660f"
COLOR_DASHED = "#666666"
COLOR_STREAM = "#e47911"


def diagram_01_strands_bedrock():
    """Demo 1: Strands + Bedrock — full deployment architecture."""
    with Diagram(
        "",
        filename="demo-01-architecture",
        show=False,
        direction="LR",
        outformat="png",
        graph_attr={**GRAPH_ATTR, "label": "Demo 1: Strands Agent on AgentCore Runtime\n", "labelloc": "t", "fontsize": "16"},
    ):
        client = Custom("Developer\nClient (boto3)", IC_USER)

        with Cluster("AWS Cloud", graph_attr={**CLUSTER_ATTR, "bgcolor": "#eef6ff"}):
            with Cluster("Deployment Artifacts", graph_attr={**CLUSTER_ATTR, "bgcolor": "#fff8e1"}):
                s3 = Custom("Amazon S3\ncode.zip", IC_S3)
                iam = Custom("IAM Role\n(Execution)", IC_ROLE)

            with Cluster("AgentCore Runtime\n(Graviton microVM)", graph_attr={**CLUSTER_ATTR, "bgcolor": "#e8f5e9", "pencolor": "#1b660f"}):
                runtime = Custom("Strands Agent\n@app.entrypoint", IC_RUNTIME)

            bedrock = Custom("Amazon Bedrock\nClaude Haiku", IC_BEDROCK)
            cw = Custom("CloudWatch\nLogs & Traces", IC_LOGS)

        # Edges with curved styling
        client >> Edge(label="invoke_agent_runtime()", color=COLOR_INVOKE, style="bold", **EDGE_ATTR) >> runtime
        runtime >> Edge(label="JSON response", color=COLOR_RESPONSE, style="bold", **EDGE_ATTR) >> client
        runtime >> Edge(label="InvokeModel", color=COLOR_PRIMARY, **EDGE_ATTR) >> bedrock
        runtime >> Edge(label="logs/traces", color=COLOR_DASHED, style="dashed", **EDGE_ATTR) >> cw
        s3 >> Edge(label="deploy", color=COLOR_DASHED, style="dashed", **EDGE_ATTR) >> runtime
        iam >> Edge(label="assume role", color=COLOR_DASHED, style="dashed", **EDGE_ATTR) >> runtime


def diagram_02_langgraph():
    """Demo 2: LangGraph — framework agnosticism."""
    with Diagram(
        "",
        filename="demo-02-architecture",
        show=False,
        direction="LR",
        outformat="png",
        graph_attr={**GRAPH_ATTR, "label": "Demo 2: Framework Agnosticism — Same API, Different Framework\n", "labelloc": "t", "fontsize": "16"},
    ):
        client = Custom("Developer\nClient (boto3)", IC_USER)

        with Cluster("AgentCore Runtime — Identical Deployment API", graph_attr={**CLUSTER_ATTR, "bgcolor": "#eef6ff"}):
            with Cluster("Option A: Strands SDK", graph_attr={**CLUSTER_ATTR, "bgcolor": "#e8f5e9"}):
                strands = Custom("Strands Agent\nAutomatic Loop", IC_RUNTIME)

            with Cluster("Option B: LangGraph", graph_attr={**CLUSTER_ATTR, "bgcolor": "#fff3e0"}):
                langgraph = Custom("LangGraph Agent\nStateGraph", IC_RUNTIME)

        bedrock = Custom("Amazon Bedrock\nClaude", IC_BEDROCK)

        with Cluster("Same Deployment Flow", graph_attr={**CLUSTER_ATTR, "bgcolor": "#f3e5f5", "style": "dashed,rounded"}):
            s3 = Custom("S3 Upload\n(code.zip)", IC_S3)
            iam = Custom("IAM Role", IC_ROLE)

        client >> Edge(label="Same: invoke_agent_runtime()", color=COLOR_INVOKE, style="bold", **EDGE_ATTR) >> strands
        client >> Edge(label="Same: invoke_agent_runtime()", color=COLOR_INVOKE, style="bold", **EDGE_ATTR) >> langgraph
        strands >> Edge(color=COLOR_PRIMARY, **EDGE_ATTR) >> bedrock
        langgraph >> Edge(color=COLOR_PRIMARY, **EDGE_ATTR) >> bedrock
        s3 >> Edge(color=COLOR_DASHED, style="dashed") >> strands
        s3 >> Edge(color=COLOR_DASHED, style="dashed") >> langgraph


def diagram_03_sessions():
    """Demo 3: Session isolation with dedicated microVMs."""
    with Diagram(
        "",
        filename="demo-03-architecture",
        show=False,
        direction="LR",
        outformat="png",
        graph_attr={**GRAPH_ATTR, "label": "Demo 3: Session Isolation — Dedicated microVMs\n", "labelloc": "t", "fontsize": "16"},
    ):
        client = Custom("Client\n(boto3)", IC_USER)

        with Cluster("AgentCore Runtime", graph_attr={**CLUSTER_ATTR, "bgcolor": "#eef6ff"}):
            with Cluster("Session A — microVM 1\n(CPU + Memory + Filesystem)", graph_attr={**CLUSTER_ATTR, "bgcolor": "#e8f5e9", "pencolor": "#1b660f"}):
                vm1 = Custom("Agent State A\nConversation A", IC_RUNTIME)

            with Cluster("Session B — microVM 2\n(CPU + Memory + Filesystem)", graph_attr={**CLUSTER_ATTR, "bgcolor": "#fff3e0", "pencolor": "#e47911"}):
                vm2 = Custom("Agent State B\nConversation B", IC_RUNTIME)

        bedrock = Custom("Amazon Bedrock\nClaude", IC_BEDROCK)

        client >> Edge(label="runtimeSessionId = A", color="#1b660f", style="bold", **EDGE_ATTR) >> vm1
        client >> Edge(label="runtimeSessionId = B", color="#e47911", style="bold", **EDGE_ATTR) >> vm2
        vm1 >> Edge(color=COLOR_PRIMARY, **EDGE_ATTR) >> bedrock
        vm2 >> Edge(color=COLOR_PRIMARY, **EDGE_ATTR) >> bedrock


def diagram_04_async():
    """Demo 4: Async agents with background tasks."""
    with Diagram(
        "",
        filename="demo-04-architecture",
        show=False,
        direction="LR",
        outformat="png",
        graph_attr={**GRAPH_ATTR, "label": "Demo 4: Async Agent — Background Task Processing\n", "labelloc": "t", "fontsize": "16"},
    ):
        client = Custom("Client\n(boto3)", IC_USER)

        with Cluster("AgentCore Runtime microVM\nMax Lifetime: 8 hours", graph_attr={**CLUSTER_ATTR, "bgcolor": "#eef6ff"}):
            with Cluster("Main Thread", graph_attr={**CLUSTER_ATTR, "bgcolor": "#e8f5e9"}):
                agent = Custom("Agent\n@app.entrypoint", IC_RUNTIME)

            with Cluster("Background Thread", graph_attr={**CLUSTER_ATTR, "bgcolor": "#fff3e0", "style": "dashed,rounded"}):
                task = Custom("Async Task\n(report gen)", IC_GEAR)

        bedrock = Custom("Amazon Bedrock\nClaude", IC_BEDROCK)

        client >> Edge(label="1. Request", color=COLOR_INVOKE, style="bold", **EDGE_ATTR) >> agent
        agent >> Edge(label="2. Immediate response\n   + Task ID", color=COLOR_RESPONSE, style="bold", **EDGE_ATTR) >> client
        agent >> Edge(label="add_async_task()", color=COLOR_STREAM, style="bold", **EDGE_ATTR) >> task
        task >> Edge(label="complete_async_task()", color=COLOR_DASHED, style="dashed", **EDGE_ATTR) >> agent
        agent >> Edge(color=COLOR_PRIMARY, **EDGE_ATTR) >> bedrock


def diagram_05_streaming():
    """Demo 5: Streaming responses via SSE."""
    with Diagram(
        "",
        filename="demo-05-architecture",
        show=False,
        direction="LR",
        outformat="png",
        graph_attr={**GRAPH_ATTR, "label": "Demo 5: Streaming Responses (Server-Sent Events)\n", "labelloc": "t", "fontsize": "16"},
    ):
        client = Custom("Client\n(boto3)", IC_USER)

        with Cluster("AgentCore Runtime microVM", graph_attr={**CLUSTER_ATTR, "bgcolor": "#eef6ff"}):
            runtime = Custom("Agent\n(same code!)", IC_RUNTIME)

        bedrock = Custom("Amazon Bedrock\nClaude", IC_BEDROCK)

        client >> Edge(
            label="accept: text/event-stream",
            color=COLOR_INVOKE, style="bold", **EDGE_ATTR,
        ) >> runtime

        runtime >> Edge(
            label="data: token1\\ldata: token2\\ldata: token3\\l...",
            color=COLOR_STREAM, style="bold", **EDGE_ATTR,
        ) >> client

        runtime >> Edge(
            label="InvokeModelWith\nResponseStream",
            color=COLOR_PRIMARY, **EDGE_ATTR,
        ) >> bedrock


# ── Main ─────────────────────────────────────────────────────────────────────

if __name__ == "__main__":
    print("Generating high-resolution architecture diagrams (300 DPI)...\n")

    diagram_01_strands_bedrock()
    print("  ✓ demo-01-architecture.png — Strands + Bedrock deployment")

    diagram_02_langgraph()
    print("  ✓ demo-02-architecture.png — Framework agnosticism")

    diagram_03_sessions()
    print("  ✓ demo-03-architecture.png — Session isolation")

    diagram_04_async()
    print("  ✓ demo-04-architecture.png — Async background tasks")

    diagram_05_streaming()
    print("  ✓ demo-05-architecture.png — SSE streaming")

    print("\n✓ All diagrams generated in demo/runtime/diagrams/")
    print("  Resolution: 300 DPI | Edges: curved | Format: PNG")
