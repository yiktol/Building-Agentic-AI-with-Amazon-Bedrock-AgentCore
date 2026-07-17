"""Generate architecture diagrams for Module 05 Memory demos."""

import os
os.chdir(os.path.dirname(os.path.abspath(__file__)))

from diagrams import Diagram, Cluster, Edge
from diagrams.custom import Custom

ICONS = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "..", "..", "aws-icons"))
IC_RUNTIME = os.path.join(ICONS, "aws-agentcore-icons", "AgentCoreRuntime.png")
IC_MEMORY = os.path.join(ICONS, "aws-agentcore-icons", "AgentCoreMemory.png")
IC_IDENTITY = os.path.join(ICONS, "aws-agentcore-icons", "AgentCoreIdentity.png")
IC_AGENTCORE = os.path.join(ICONS, "aws-agentcore-icons", "AgentCore.png")
IC_BEDROCK = os.path.join(ICONS, "Architecture-Service-Icons_04302026", "Arch_Artificial-Intelligence", "48", "Arch_Amazon-Bedrock_48.png")
IC_AGENTCORE_SVC = os.path.join(ICONS, "Architecture-Service-Icons_04302026", "Arch_Artificial-Intelligence", "48", "Arch_Amazon-Bedrock-AgentCore_48.png")
IC_IAM = os.path.join(ICONS, "Architecture-Service-Icons_04302026", "Arch_Security-Identity", "48", "Arch_AWS-IAM-Identity-Center_48.png")
IC_USER = os.path.join(ICONS, "Resource-Icons_04302026", "Res_General-Icons", "Res_48_Light", "Res_Client_48_Light.png")
IC_GEAR = os.path.join(ICONS, "Resource-Icons_04302026", "Res_General-Icons", "Res_48_Light", "Res_Gear_48_Light.png")

GRAPH_ATTR = {"dpi": "300", "fontsize": "11", "fontname": "Helvetica", "bgcolor": "white", "pad": "0.8", "nodesep": "1.0", "ranksep": "1.2", "splines": "curved"}
CLUSTER_ATTR = {"fontsize": "12", "fontname": "Helvetica Bold", "style": "rounded", "bgcolor": "#f8f9fa", "pencolor": "#232f3e", "penwidth": "1.5"}
EDGE_ATTR = {"fontsize": "9", "fontname": "Helvetica"}
C_INVOKE, C_OK, C_DASH, C_MEMORY, C_DENY = "#0073bb", "#1b660f", "#666666", "#8c4fff", "#d13212"


def diagram_01():
    """Demo 1: Short-term memory — events, actors, sessions."""
    with Diagram("", filename="demo-01-architecture", show=False, direction="LR", outformat="png",
                 graph_attr={**GRAPH_ATTR, "label": "Demo 1: Short-Term Memory — Events & Sessions\n", "labelloc": "t", "fontsize": "16"}):
        client = Custom("Developer\nClient", IC_USER)
        with Cluster("AWS", graph_attr={**CLUSTER_ATTR, "bgcolor": "#eef6ff"}):
            with Cluster("AgentCore Memory", graph_attr={**CLUSTER_ATTR, "bgcolor": "#f3e5f5"}):
                stm = Custom("Short-Term Memory\n(Events)", IC_MEMORY)
            with Cluster("Session A (Actor: user-42)", graph_attr={**CLUSTER_ATTR, "bgcolor": "#e8f5e9", "style": "dashed,rounded"}):
                e1 = Custom("Event 1\nUSER msg", IC_GEAR)
                e2 = Custom("Event 2\nASSISTANT msg", IC_GEAR)
                e3 = Custom("Event 3\nUSER msg", IC_GEAR)
        client >> Edge(label="CreateEvent", color=C_INVOKE, style="bold", **EDGE_ATTR) >> stm
        stm >> Edge(label="ListEvents /\nget_last_k_turns", color=C_OK, style="bold", **EDGE_ATTR) >> client
        stm >> Edge(color=C_DASH, style="dashed", **EDGE_ATTR) >> e1
        stm >> Edge(color=C_DASH, style="dashed", **EDGE_ATTR) >> e2
        stm >> Edge(color=C_DASH, style="dashed", **EDGE_ATTR) >> e3


def diagram_02():
    """Demo 2: Long-term memory — strategies and extraction."""
    with Diagram("", filename="demo-02-architecture", show=False, direction="LR", outformat="png",
                 graph_attr={**GRAPH_ATTR, "label": "Demo 2: Long-Term Memory — Strategy Extraction\n", "labelloc": "t", "fontsize": "16"}):
        client = Custom("Developer\nClient", IC_USER)
        with Cluster("AgentCore Memory", graph_attr={**CLUSTER_ATTR, "bgcolor": "#eef6ff"}):
            with Cluster("Short-Term", graph_attr={**CLUSTER_ATTR, "bgcolor": "#fff3e0"}):
                events = Custom("Raw Events\n(conversation)", IC_GEAR)
            with Cluster("Extraction Pipeline (async)", graph_attr={**CLUSTER_ATTR, "bgcolor": "#f3e5f5", "style": "dashed,rounded"}):
                strategy = Custom("Semantic\nStrategy", IC_MEMORY)
            with Cluster("Long-Term", graph_attr={**CLUSTER_ATTR, "bgcolor": "#e8f5e9"}):
                records = Custom("Memory Records\n(structured facts)", IC_MEMORY)
        bedrock = Custom("Amazon Bedrock\n(embedding + LLM)", IC_BEDROCK)
        client >> Edge(label="CreateEvent", color=C_INVOKE, style="bold", **EDGE_ATTR) >> events
        events >> Edge(label="every K turns", color=C_MEMORY, style="bold", **EDGE_ATTR) >> strategy
        strategy >> Edge(label="extract", color=C_MEMORY, **EDGE_ATTR) >> records
        strategy >> Edge(label="InvokeModel", color=C_DASH, style="dashed", **EDGE_ATTR) >> bedrock
        client >> Edge(label="RetrieveMemoryRecords\n(semantic search)", color=C_OK, style="bold", **EDGE_ATTR) >> records


def diagram_03():
    """Demo 3: Strands agent with memory as tool."""
    with Diagram("", filename="demo-03-architecture", show=False, direction="LR", outformat="png",
                 graph_attr={**GRAPH_ATTR, "label": "Demo 3: Strands Agent — Memory as Tool\n", "labelloc": "t", "fontsize": "16"}):
        user = Custom("User", IC_USER)
        with Cluster("AgentCore Runtime (microVM)", graph_attr={**CLUSTER_ATTR, "bgcolor": "#e8f5e9"}):
            agent = Custom("Strands Agent\n+ MemoryToolProvider", IC_RUNTIME)
        with Cluster("AgentCore Memory", graph_attr={**CLUSTER_ATTR, "bgcolor": "#f3e5f5"}):
            stm = Custom("Short-Term\nEvents", IC_MEMORY)
            ltm = Custom("Long-Term\nRecords", IC_MEMORY)
        bedrock = Custom("Amazon Bedrock\nClaude", IC_BEDROCK)
        user >> Edge(label="invoke", color=C_INVOKE, style="bold", **EDGE_ATTR) >> agent
        agent >> Edge(label="LLM decides:\nsave / recall", color=C_MEMORY, style="bold", **EDGE_ATTR) >> stm
        agent >> Edge(label="retrieve_memories", color=C_MEMORY, style="bold", **EDGE_ATTR) >> ltm
        agent >> Edge(label="InvokeModel", color=C_DASH, **EDGE_ATTR) >> bedrock
        agent >> Edge(label="response", color=C_OK, style="bold", **EDGE_ATTR) >> user


def diagram_04():
    """Demo 4: Strands agent with memory hooks."""
    with Diagram("", filename="demo-04-architecture", show=False, direction="LR", outformat="png",
                 graph_attr={**GRAPH_ATTR, "label": "Demo 4: Strands Agent — Memory Hooks\n", "labelloc": "t", "fontsize": "16"}):
        user = Custom("User", IC_USER)
        with Cluster("AgentCore Runtime (microVM)", graph_attr={**CLUSTER_ATTR, "bgcolor": "#e8f5e9"}):
            agent = Custom("Strands Agent\n+ HookProvider", IC_RUNTIME)
            with Cluster("Hooks (automatic)", graph_attr={**CLUSTER_ATTR, "bgcolor": "#fff3e0", "style": "dashed,rounded"}):
                retrieve_hook = Custom("MessageAdded\n→ retrieve()", IC_GEAR)
                save_hook = Custom("AfterInvocation\n→ save()", IC_GEAR)
        with Cluster("AgentCore Memory", graph_attr={**CLUSTER_ATTR, "bgcolor": "#f3e5f5"}):
            memory = Custom("Memory\n(STM + LTM)", IC_MEMORY)
        bedrock = Custom("Amazon Bedrock\nClaude", IC_BEDROCK)
        user >> Edge(label="invoke", color=C_INVOKE, style="bold", **EDGE_ATTR) >> agent
        agent >> Edge(color=C_DASH, style="dashed", **EDGE_ATTR) >> retrieve_hook
        agent >> Edge(color=C_DASH, style="dashed", **EDGE_ATTR) >> save_hook
        retrieve_hook >> Edge(label="retrieve", color=C_MEMORY, style="bold", **EDGE_ATTR) >> memory
        save_hook >> Edge(label="create_event", color=C_MEMORY, style="bold", **EDGE_ATTR) >> memory
        agent >> Edge(label="InvokeModel", color=C_DASH, **EDGE_ATTR) >> bedrock
        agent >> Edge(label="response", color=C_OK, style="bold", **EDGE_ATTR) >> user


def diagram_05():
    """Demo 5: IAM-scoped memory access."""
    with Diagram("", filename="demo-05-architecture", show=False, direction="LR", outformat="png",
                 graph_attr={**GRAPH_ATTR, "label": "Demo 5: IAM-Scoped Memory Access\n", "labelloc": "t", "fontsize": "16"}):
        user_a = Custom("User A", IC_USER)
        user_b = Custom("User B", IC_USER)
        with Cluster("AWS", graph_attr={**CLUSTER_ATTR, "bgcolor": "#eef6ff"}):
            iam = Custom("IAM Policy\nCondition:\nactorId = ${user}", IC_IAM)
            with Cluster("AgentCore Memory", graph_attr={**CLUSTER_ATTR, "bgcolor": "#f3e5f5"}):
                ns_a = Custom("Namespace\n/users/user-A/", IC_MEMORY)
                ns_b = Custom("Namespace\n/users/user-B/", IC_MEMORY)
        user_a >> Edge(label="actorId=A", color=C_OK, style="bold", **EDGE_ATTR) >> iam
        user_b >> Edge(label="actorId=B", color=C_OK, style="bold", **EDGE_ATTR) >> iam
        iam >> Edge(label="✓ allowed", color=C_OK, style="bold", **EDGE_ATTR) >> ns_a
        iam >> Edge(label="✓ allowed", color=C_OK, style="bold", **EDGE_ATTR) >> ns_b
        user_a >> Edge(label="actorId=B", color=C_DENY, style="bold", **EDGE_ATTR) >> ns_b


if __name__ == "__main__":
    print("Generating Module 05 Memory diagrams (300 DPI)...\n")
    diagram_01(); print("  ✓ demo-01-architecture.png — Short-term memory")
    diagram_02(); print("  ✓ demo-02-architecture.png — Long-term memory")
    diagram_03(); print("  ✓ demo-03-architecture.png — Memory as tool")
    diagram_04(); print("  ✓ demo-04-architecture.png — Memory hooks")
    diagram_05(); print("  ✓ demo-05-architecture.png — IAM scoped access")
    print("\n✓ Done.")
