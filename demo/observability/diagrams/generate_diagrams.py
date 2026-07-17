"""Generate architecture diagrams for Module 06 Observability & Evaluations demos."""

import os
os.chdir(os.path.dirname(os.path.abspath(__file__)))

from diagrams import Diagram, Cluster, Edge
from diagrams.custom import Custom

ICONS = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "..", "..", "aws-icons"))
IC_RUNTIME = os.path.join(ICONS, "aws-agentcore-icons", "AgentCoreRuntime.png")
IC_OBSERVABILITY = os.path.join(ICONS, "aws-agentcore-icons", "AgentCoreObservability.png")
IC_AGENTCORE = os.path.join(ICONS, "aws-agentcore-icons", "AgentCore.png")
IC_BEDROCK = os.path.join(ICONS, "Architecture-Service-Icons_04302026", "Arch_Artificial-Intelligence", "48", "Arch_Amazon-Bedrock_48.png")
IC_CLOUDWATCH = os.path.join(ICONS, "Architecture-Service-Icons_04302026", "Arch_Management-Tools", "48", "Arch_Amazon-CloudWatch_48.png")
IC_USER = os.path.join(ICONS, "Resource-Icons_04302026", "Res_General-Icons", "Res_48_Light", "Res_Client_48_Light.png")
IC_GEAR = os.path.join(ICONS, "Resource-Icons_04302026", "Res_General-Icons", "Res_48_Light", "Res_Gear_48_Light.png")

GRAPH_ATTR = {"dpi": "300", "fontsize": "11", "fontname": "Helvetica", "bgcolor": "white", "pad": "0.8", "nodesep": "1.0", "ranksep": "1.2", "splines": "curved"}
CLUSTER_ATTR = {"fontsize": "12", "fontname": "Helvetica Bold", "style": "rounded", "bgcolor": "#f8f9fa", "pencolor": "#232f3e", "penwidth": "1.5"}
EDGE_ATTR = {"fontsize": "9", "fontname": "Helvetica"}
C_INVOKE, C_OK, C_DASH, C_TRACE, C_EVAL = "#0073bb", "#1b660f", "#666666", "#e47911", "#8c4fff"


def diagram_01():
    """Demo 1: Agent with OTel instrumentation → CloudWatch."""
    with Diagram("", filename="demo-01-architecture", show=False, direction="LR", outformat="png",
                 graph_attr={**GRAPH_ATTR, "label": "Demo 1: Observability Setup — OTel to CloudWatch\n", "labelloc": "t", "fontsize": "16"}):
        client = Custom("Developer\nClient", IC_USER)
        with Cluster("AgentCore Runtime (microVM)", graph_attr={**CLUSTER_ATTR, "bgcolor": "#e8f5e9"}):
            agent = Custom("HR Agent\n+ ADOT SDK", IC_RUNTIME)
        with Cluster("Amazon CloudWatch", graph_attr={**CLUSTER_ATTR, "bgcolor": "#fff3e0"}):
            metrics = Custom("Metrics\n(latency, errors)", IC_CLOUDWATCH)
            traces = Custom("GenAI Observability\n(sessions, traces, spans)", IC_OBSERVABILITY)
            logs = Custom("Logs\n(OTel spans)", IC_CLOUDWATCH)
        bedrock = Custom("Amazon Bedrock\nNova Lite", IC_BEDROCK)
        client >> Edge(label="invoke", color=C_INVOKE, style="bold", **EDGE_ATTR) >> agent
        agent >> Edge(label="InvokeModel", color=C_DASH, **EDGE_ATTR) >> bedrock
        agent >> Edge(label="metrics", color=C_TRACE, **EDGE_ATTR) >> metrics
        agent >> Edge(label="traces", color=C_TRACE, style="bold", **EDGE_ATTR) >> traces
        agent >> Edge(label="logs", color=C_TRACE, **EDGE_ATTR) >> logs


def diagram_02():
    """Demo 2: Custom spans for tool-level visibility."""
    with Diagram("", filename="demo-02-architecture", show=False, direction="LR", outformat="png",
                 graph_attr={**GRAPH_ATTR, "label": "Demo 2: Custom Spans — Tool-Level Tracing\n", "labelloc": "t", "fontsize": "16"}):
        with Cluster("Agent with Custom Spans", graph_attr={**CLUSTER_ATTR, "bgcolor": "#e8f5e9"}):
            session_span = Custom("Session Span\n(custom parent)", IC_RUNTIME)
            with Cluster("Child Spans", graph_attr={**CLUSTER_ATTR, "bgcolor": "#fff3e0", "style": "dashed,rounded"}):
                model = Custom("model_call\n(ADOT auto)", IC_GEAR)
                search = Custom("web_search\n(custom attrs)", IC_GEAR)
                weather = Custom("get_weather\n(custom attrs)", IC_GEAR)
        cw = Custom("CloudWatch\nGenAI Observability", IC_OBSERVABILITY)
        session_span >> Edge(color=C_DASH, style="dashed", **EDGE_ATTR) >> model
        session_span >> Edge(color=C_DASH, style="dashed", **EDGE_ATTR) >> search
        session_span >> Edge(color=C_DASH, style="dashed", **EDGE_ATTR) >> weather
        session_span >> Edge(label="export spans", color=C_TRACE, style="bold", **EDGE_ATTR) >> cw


def diagram_03():
    """Demo 3: CloudWatch dashboard views."""
    with Diagram("", filename="demo-03-architecture", show=False, direction="TB", outformat="png",
                 graph_attr={**GRAPH_ATTR, "label": "Demo 3: CloudWatch GenAI Observability Views\n", "labelloc": "t", "fontsize": "16"}):
        agents = Custom("Agents View\n(all agents)", IC_OBSERVABILITY)
        detail = Custom("Agent Detail\n(metrics + sessions)", IC_OBSERVABILITY)
        session = Custom("Session Detail\n(traces list)", IC_OBSERVABILITY)
        trace = Custom("Trace Detail\n(spans timeline)", IC_OBSERVABILITY)
        span = Custom("Span Details\n(attributes + events)", IC_GEAR)
        agents >> Edge(label="click agent", color=C_INVOKE, style="bold", **EDGE_ATTR) >> detail
        detail >> Edge(label="click session", color=C_INVOKE, style="bold", **EDGE_ATTR) >> session
        session >> Edge(label="click trace", color=C_INVOKE, style="bold", **EDGE_ATTR) >> trace
        trace >> Edge(label="click span", color=C_INVOKE, style="bold", **EDGE_ATTR) >> span


def diagram_04():
    """Demo 4: On-demand evaluation."""
    with Diagram("", filename="demo-04-architecture", show=False, direction="LR", outformat="png",
                 graph_attr={**GRAPH_ATTR, "label": "Demo 4: On-Demand Evaluation (LLM-as-Judge)\n", "labelloc": "t", "fontsize": "16"}):
        client = Custom("Evaluation\nScript", IC_USER)
        with Cluster("CloudWatch", graph_attr={**CLUSTER_ATTR, "bgcolor": "#fff3e0"}):
            spans = Custom("Recorded\nSpans/Traces", IC_OBSERVABILITY)
        with Cluster("AgentCore Evaluations", graph_attr={**CLUSTER_ATTR, "bgcolor": "#f3e5f5"}):
            evaluators = Custom("Built-in Evaluators\n(LLM-as-Judge)", IC_AGENTCORE)
        results = Custom("Scores\n+ Explanations", IC_GEAR)
        client >> Edge(label="EvaluationClient.run()", color=C_EVAL, style="bold", **EDGE_ATTR) >> evaluators
        spans >> Edge(label="session spans", color=C_DASH, **EDGE_ATTR) >> evaluators
        evaluators >> Edge(label="scores", color=C_OK, style="bold", **EDGE_ATTR) >> results


def diagram_05():
    """Demo 5: Online evaluation (continuous monitoring)."""
    with Diagram("", filename="demo-05-architecture", show=False, direction="LR", outformat="png",
                 graph_attr={**GRAPH_ATTR, "label": "Demo 5: Online Evaluation — Continuous Monitoring\n", "labelloc": "t", "fontsize": "16"}):
        user = Custom("Users\n(live traffic)", IC_USER)
        with Cluster("AgentCore Runtime", graph_attr={**CLUSTER_ATTR, "bgcolor": "#e8f5e9"}):
            agent = Custom("HR Agent", IC_RUNTIME)
        with Cluster("CloudWatch", graph_attr={**CLUSTER_ATTR, "bgcolor": "#fff3e0"}):
            traces = Custom("Live Traces", IC_OBSERVABILITY)
        with Cluster("Online Eval Config\n(100% sampling)", graph_attr={**CLUSTER_ATTR, "bgcolor": "#f3e5f5"}):
            eval_svc = Custom("Auto Evaluation\nGoalSuccessRate\nHelpfulness\nCorrectness", IC_AGENTCORE)
        dashboard = Custom("Evaluation\nDashboard", IC_CLOUDWATCH)
        user >> Edge(label="invoke", color=C_INVOKE, style="bold", **EDGE_ATTR) >> agent
        agent >> Edge(label="spans", color=C_TRACE, **EDGE_ATTR) >> traces
        traces >> Edge(label="sample", color=C_EVAL, style="bold", **EDGE_ATTR) >> eval_svc
        eval_svc >> Edge(label="scores over time", color=C_OK, style="bold", **EDGE_ATTR) >> dashboard


if __name__ == "__main__":
    print("Generating Module 06 Observability diagrams (300 DPI)...\n")
    diagram_01(); print("  ✓ demo-01-architecture.png — OTel instrumentation")
    diagram_02(); print("  ✓ demo-02-architecture.png — Custom spans")
    diagram_03(); print("  ✓ demo-03-architecture.png — CloudWatch views")
    diagram_04(); print("  ✓ demo-04-architecture.png — On-demand evaluation")
    diagram_05(); print("  ✓ demo-05-architecture.png — Online evaluation")
    print("\n✓ Done.")
