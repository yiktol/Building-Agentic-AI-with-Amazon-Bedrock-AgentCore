"""Generate architecture diagrams for Module 03 Identity demos."""

import os
os.chdir(os.path.dirname(os.path.abspath(__file__)))

from diagrams import Diagram, Cluster, Edge
from diagrams.custom import Custom

ICONS = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "..", "..", "aws-icons"))
IC_RUNTIME = os.path.join(ICONS, "aws-agentcore-icons", "AgentCoreRuntime.png")
IC_IDENTITY = os.path.join(ICONS, "aws-agentcore-icons", "AgentCoreIdentity.png")
IC_BEDROCK = os.path.join(ICONS, "Architecture-Service-Icons_04302026", "Arch_Artificial-Intelligence", "48", "Arch_Amazon-Bedrock_48.png")
IC_COGNITO = os.path.join(ICONS, "Architecture-Service-Icons_04302026", "Arch_Security-Identity", "48", "Arch_AWS-IAM-Identity-Center_48.png")
IC_USER = os.path.join(ICONS, "Resource-Icons_04302026", "Res_General-Icons", "Res_48_Light", "Res_Client_48_Light.png")

GRAPH_ATTR = {"dpi": "300", "fontsize": "11", "fontname": "Helvetica", "bgcolor": "white", "pad": "0.8", "nodesep": "1.0", "ranksep": "1.2", "splines": "curved"}
CLUSTER_ATTR = {"fontsize": "12", "fontname": "Helvetica Bold", "style": "rounded", "bgcolor": "#f8f9fa", "pencolor": "#232f3e", "penwidth": "1.5"}
EDGE_ATTR = {"fontsize": "9", "fontname": "Helvetica"}
C_INVOKE, C_OK, C_DASH, C_DENY, C_AUTH = "#0073bb", "#1b660f", "#666666", "#d13212", "#8c4fff"


def diagram_01():
    with Diagram("", filename="demo-01-architecture", show=False, direction="LR", outformat="png",
                 graph_attr={**GRAPH_ATTR, "label": "Demo 1: Inbound Auth — Cognito JWT\n", "labelloc": "t", "fontsize": "16"}):
        client = Custom("Client", IC_USER)
        with Cluster("AWS", graph_attr={**CLUSTER_ATTR, "bgcolor": "#eef6ff"}):
            cognito = Custom("Cognito\nUser Pool", IC_COGNITO)
            with Cluster("AgentCore Runtime", graph_attr={**CLUSTER_ATTR, "bgcolor": "#e8f5e9"}):
                auth = Custom("JWT\nAuthorizer", IC_IDENTITY)
                agent = Custom("Agent", IC_RUNTIME)
            bedrock = Custom("Bedrock", IC_BEDROCK)
        client >> Edge(label="Bearer <JWT>", color=C_AUTH, style="bold", **EDGE_ATTR) >> auth
        auth >> Edge(label="JWKS", color=C_DASH, style="dashed", **EDGE_ATTR) >> cognito
        auth >> Edge(label="✓ forward", color=C_OK, style="bold", **EDGE_ATTR) >> agent
        agent >> Edge(color=C_INVOKE, **EDGE_ATTR) >> bedrock


def diagram_02():
    with Diagram("", filename="demo-02-architecture", show=False, direction="LR", outformat="png",
                 graph_attr={**GRAPH_ATTR, "label": "Demo 2: Outbound Auth — API Key Vault\n", "labelloc": "t", "fontsize": "16"}):
        client = Custom("Client", IC_USER)
        with Cluster("AgentCore Runtime", graph_attr={**CLUSTER_ATTR, "bgcolor": "#e8f5e9"}):
            agent = Custom("Agent\n@requires_api_key", IC_RUNTIME)
        with Cluster("AgentCore Identity", graph_attr={**CLUSTER_ATTR, "bgcolor": "#f3e5f5"}):
            vault = Custom("Token Vault\n(Secrets Mgr)", IC_IDENTITY)
        external = Custom("External API", IC_BEDROCK)
        client >> Edge(label="invoke", color=C_INVOKE, style="bold", **EDGE_ATTR) >> agent
        agent >> Edge(label="GetResourceApiKey", color=C_AUTH, style="bold", **EDGE_ATTR) >> vault
        vault >> Edge(label="key", color=C_OK, **EDGE_ATTR) >> agent
        agent >> Edge(label="Bearer <key>", color=C_INVOKE, **EDGE_ATTR) >> external


def diagram_03():
    with Diagram("", filename="demo-03-architecture", show=False, direction="LR", outformat="png",
                 graph_attr={**GRAPH_ATTR, "label": "Demo 3: Outbound Auth — GitHub 3LO\n", "labelloc": "t", "fontsize": "16"}):
        user = Custom("User", IC_USER)
        with Cluster("AgentCore Runtime", graph_attr={**CLUSTER_ATTR, "bgcolor": "#e8f5e9"}):
            agent = Custom("Agent\n@requires_access_token", IC_RUNTIME)
        with Cluster("AgentCore Identity", graph_attr={**CLUSTER_ATTR, "bgcolor": "#f3e5f5"}):
            oauth = Custom("GitHub OAuth2\nProvider", IC_IDENTITY)
        github = Custom("GitHub API", IC_BEDROCK)
        user >> Edge(label="1. invoke", color=C_INVOKE, style="bold", **EDGE_ATTR) >> agent
        agent >> Edge(label="2. token?", color=C_AUTH, **EDGE_ATTR) >> oauth
        oauth >> Edge(label="3. consent URL", color=C_DASH, style="dashed", **EDGE_ATTR) >> user
        oauth >> Edge(label="5. cached token", color=C_OK, style="bold", **EDGE_ATTR) >> agent
        agent >> Edge(label="6. Bearer <token>", color=C_INVOKE, **EDGE_ATTR) >> github


def diagram_04():
    with Diagram("", filename="demo-04-architecture", show=False, direction="LR", outformat="png",
                 graph_attr={**GRAPH_ATTR, "label": "Demo 4: Combined M2M + 3LO Outbound Auth\n", "labelloc": "t", "fontsize": "16"}):
        user = Custom("User", IC_USER)
        with Cluster("AWS", graph_attr={**CLUSTER_ATTR, "bgcolor": "#eef6ff"}):
            cognito = Custom("Cognito\n(inbound JWT +\nM2M token)", IC_COGNITO)
            with Cluster("AgentCore Runtime", graph_attr={**CLUSTER_ATTR, "bgcolor": "#e8f5e9"}):
                agent = Custom("Agent\n(M2M + 3LO tools)", IC_RUNTIME)
            with Cluster("AgentCore Identity", graph_attr={**CLUSTER_ATTR, "bgcolor": "#f3e5f5"}):
                m2m = Custom("M2M Provider\n(client_credentials)", IC_IDENTITY)
                tlo = Custom("Google 3LO\n(auth_code)", IC_IDENTITY)
        internal = Custom("Internal API", IC_BEDROCK)
        google = Custom("Google\nCalendar", IC_BEDROCK)
        user >> Edge(label="Bearer <Cognito JWT>", color=C_AUTH, style="bold", **EDGE_ATTR) >> agent
        agent >> Edge(label="auth_flow=M2M", color=C_INVOKE, style="bold", **EDGE_ATTR) >> m2m
        m2m >> Edge(label="client_credentials", color=C_DASH, style="dashed", **EDGE_ATTR) >> cognito
        m2m >> Edge(label="token", color=C_OK, **EDGE_ATTR) >> agent
        agent >> Edge(color=C_INVOKE, **EDGE_ATTR) >> internal
        agent >> Edge(label="auth_flow=USER_FEDERATION", color=C_AUTH, **EDGE_ATTR) >> tlo
        tlo >> Edge(label="user token", color=C_OK, **EDGE_ATTR) >> agent
        agent >> Edge(color=C_INVOKE, **EDGE_ATTR) >> google


def diagram_05():
    with Diagram("", filename="demo-05-architecture", show=False, direction="LR", outformat="png",
                 graph_attr={**GRAPH_ATTR, "label": "Demo 5: Workload Identity\n", "labelloc": "t", "fontsize": "16"}):
        dev = Custom("Developer", IC_USER)
        with Cluster("AWS", graph_attr={**CLUSTER_ATTR, "bgcolor": "#eef6ff"}):
            with Cluster("AgentCore Runtime", graph_attr={**CLUSTER_ATTR, "bgcolor": "#e8f5e9"}):
                agent = Custom("Agent", IC_RUNTIME)
            with Cluster("Identity Directory", graph_attr={**CLUSTER_ATTR, "bgcolor": "#f3e5f5"}):
                wid = Custom("Workload\nIdentity\n(auto-created)", IC_IDENTITY)
            iam = Custom("IAM Policy\n(uses identity ARN)", IC_COGNITO)
            s3 = Custom("S3 / DynamoDB\n(protected)", IC_BEDROCK)
        dev >> Edge(label="deploy agent", color=C_INVOKE, style="bold", **EDGE_ATTR) >> agent
        agent >> Edge(label="creates", color=C_OK, style="bold", **EDGE_ATTR) >> wid
        wid >> Edge(label="ARN in Condition", color=C_AUTH, style="dashed", **EDGE_ATTR) >> iam
        iam >> Edge(label="grants access", color=C_OK, **EDGE_ATTR) >> s3
        agent >> Edge(label="GetWorkloadAccessToken", color=C_AUTH, **EDGE_ATTR) >> wid


if __name__ == "__main__":
    print("Generating Module 03 diagrams (300 DPI)...\n")
    diagram_01(); print("  ✓ demo-01-architecture.png")
    diagram_02(); print("  ✓ demo-02-architecture.png")
    diagram_03(); print("  ✓ demo-03-architecture.png")
    diagram_04(); print("  ✓ demo-04-architecture.png")
    diagram_05(); print("  ✓ demo-05-architecture.png")
    print("\n✓ Done.")
