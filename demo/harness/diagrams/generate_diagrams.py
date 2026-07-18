"""Generate architecture diagrams for Module 07 Harness demos.

Requires: pip install diagrams
"""

from diagrams import Diagram, Cluster, Edge
from diagrams.aws.ml import Sagemaker
from diagrams.aws.compute import Lambda
from diagrams.aws.security import IAM
from diagrams.aws.management import Cloudformation
from diagrams.custom import Custom
from diagrams.onprem.client import User


GRAPH_ATTR = {
    "fontsize": "14",
    "bgcolor": "white",
    "dpi": "300",
    "pad": "0.5",
}


def demo_01():
    """Demo 1: Getting Started — Create, Invoke, Cleanup."""
    with Diagram(
        "Demo 01: Getting Started",
        filename="demo-01-architecture",
        show=False,
        direction="LR",
        graph_attr=GRAPH_ATTR,
    ):
        user = User("Developer")

        with Cluster("AWS Account"):
            iam = IAM("Execution Role")
            with Cluster("AgentCore Harness"):
                harness = Sagemaker("Harness\n(Managed Agent Loop)")
                model = Sagemaker("Claude Haiku 4.5")

        user >> Edge(label="create_harness") >> harness
        user >> Edge(label="invoke_harness") >> harness
        harness >> Edge(label="InvokeModel") >> model
        iam >> Edge(style="dashed") >> harness


def demo_02():
    """Demo 2: Execute Command — Direct shell on microVM."""
    with Diagram(
        "Demo 02: Execute Command",
        filename="demo-02-architecture",
        show=False,
        direction="LR",
        graph_attr=GRAPH_ATTR,
    ):
        user = User("Developer")

        with Cluster("AWS Account"):
            with Cluster("AgentCore Harness"):
                harness = Sagemaker("Harness")
                vm = Lambda("MicroVM\n(Sandbox)")
                model = Sagemaker("Claude Haiku 4.5")

        user >> Edge(label="invoke_harness\n(agent loop)") >> harness
        user >> Edge(label="ExecuteCommand\n(direct shell)", style="bold") >> vm
        harness >> model
        harness >> vm


def demo_03():
    """Demo 3: File Operations — Agent writes/reads files."""
    with Diagram(
        "Demo 03: File Operations",
        filename="demo-03-architecture",
        show=False,
        direction="LR",
        graph_attr=GRAPH_ATTR,
    ):
        user = User("Developer")

        with Cluster("AWS Account"):
            with Cluster("AgentCore Harness"):
                harness = Sagemaker("Harness")
                tools = Lambda("Built-in Tools\n(file_operations, shell)")
                vm = Lambda("MicroVM\nFilesystem")
                model = Sagemaker("Claude Haiku 4.5")

        user >> Edge(label="invoke_harness") >> harness
        harness >> Edge(label="tool_use") >> tools
        tools >> vm
        harness >> model
        user >> Edge(label="ExecuteCommand\n(verify)", style="dashed") >> vm


def demo_04():
    """Demo 4: Model Switching — Per-invocation model selection."""
    with Diagram(
        "Demo 04: Model Switching",
        filename="demo-04-architecture",
        show=False,
        direction="LR",
        graph_attr=GRAPH_ATTR,
    ):
        user = User("Developer")

        with Cluster("AWS Account"):
            with Cluster("AgentCore Harness"):
                harness = Sagemaker("Harness\n(same session)")
                vm = Lambda("Shared MicroVM\nFilesystem")

            with Cluster("Bedrock Models"):
                haiku = Sagemaker("Claude Haiku 4.5")
                sonnet = Sagemaker("Claude Sonnet 4.5")

        user >> Edge(label="invoke (model=haiku)") >> harness
        user >> Edge(label="invoke (model=sonnet)") >> harness
        harness >> haiku
        harness >> sonnet
        harness >> vm


def demo_05():
    """Demo 5: Interactive Chat — Persistent session state."""
    with Diagram(
        "Demo 05: Interactive Chat",
        filename="demo-05-architecture",
        show=False,
        direction="LR",
        graph_attr=GRAPH_ATTR,
    ):
        user = User("Developer")

        with Cluster("AWS Account"):
            with Cluster("AgentCore Harness"):
                harness = Sagemaker("Harness")
                session = Lambda("Session State\n(persists across turns)")
                tools = Lambda("Built-in Tools")
                model = Sagemaker("Claude Haiku 4.5")

        user >> Edge(label="Turn 1, 2, 3...\n(same session_id)") >> harness
        harness >> model
        harness >> tools
        harness >> session
        user >> Edge(label="exec <cmd>", style="dashed") >> session


if __name__ == "__main__":
    print("Generating Demo 01 diagram...")
    demo_01()
    print("Generating Demo 02 diagram...")
    demo_02()
    print("Generating Demo 03 diagram...")
    demo_03()
    print("Generating Demo 04 diagram...")
    demo_04()
    print("Generating Demo 05 diagram...")
    demo_05()
    print("✓ All diagrams generated.")
