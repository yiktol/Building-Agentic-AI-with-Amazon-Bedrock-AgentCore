# Module 04: Tools & Gateway — Instructor Demos

Five demonstrations covering MCP servers, Code Interpreter, AgentCore Gateway, and Cedar Policy.

## Demo Overview

| # | Demo | Key Concepts | Dependencies |
|---|------|--------------|--------------|
| 1 | [MCP Server](demo-01-mcp-server/) | FastMCP, serverProtocol=MCP, JSON-RPC 2.0 | CFN stack |
| 2 | [Code Interpreter](demo-02-code-interpreter/) | Built-in tool, sandbox, executeCode | None (managed) |
| 3 | [Gateway — Lambda](demo-03-gateway-lambda/) | Gateway, targets, tools/list, tools/call | CFN stack |
| 4 | [Gateway — Search](demo-04-gateway-search/) | Semantic search, x_amz_bedrock_agentcore_search | Demo 3 |
| 5 | [Cedar Policy](demo-05-cedar-policy/) | Policy engine, ENFORCE, permit/forbid | Demo 3 |

## Prerequisites

### Deploy CloudFormation Stack (REQUIRED for Demos 1, 3-5)

```bash
cd cloudformation
./deploy-stack.sh              # creates S3, IAM, Lambda functions
```

### Software

```bash
python3 -m venv venv
source venv/bin/activate
pip install boto3 bedrock-agentcore mcp uv
```

---

## Demo Instructions

### Demo 1: MCP Server (Create + Host + Invoke)

**What to show the audience:**
- Creating an MCP server with `FastMCP` and `@mcp.tool()` decorators
- Deploying with `serverProtocol: MCP` (port 8000, `/mcp` endpoint)
- JSON-RPC 2.0 protocol: `initialize` → `tools/list` → `tools/call`
- Difference from HTTP agents: protocol and port, not the deployment flow

```bash
cd demo-01-mcp-server
cat mcp_server.py              # Show FastMCP server code
python local_test.py           # Test locally (JSON-RPC over HTTP)
python deploy.py               # Deploy with serverProtocol=MCP
python invoke.py               # initialize → tools/list → tools/call
python cleanup.py
```

**Talking points:**
- MCP = open standard for LLM ↔ tool communication
- `FastMCP` with `stateless_http=True` for AgentCore compatibility
- Same deployment flow as HTTP agents — only `serverProtocol` changes
- Tools are discovered at runtime via `tools/list` (no hardcoding)
- Stateless streamable-HTTP transport — session isolation via headers

---

### Demo 2: Code Interpreter (Built-in Tool)

**What to show the audience:**
- Agent with `execute_python` tool that calls Code Interpreter
- LLM decides WHEN to write and run code (tool selection)
- Sandboxed Python execution (isolated per session)
- Agent verifies answers through actual code execution

```bash
cd demo-02-code-interpreter
cat agent.py                   # Show agent with execute_python tool
python local_test.py           # Test locally
python deploy.py               # Deploy agent to AgentCore Runtime
python invoke.py               # Agent writes + executes code to answer questions
python cleanup.py
```

**Talking points:**
- Code Interpreter is a built-in managed tool — no infra to manage
- Agent decides when to use it (tool selection by the LLM)
- Isolated sandbox: Python 3.12 + shell + filesystem per session
- Use cases: data analysis, math verification, report generation
- Supports VPC access for private data sources

---

### Demo 3: Gateway with Lambda Targets

**What to show the audience:**
- Creating a gateway as a unified MCP endpoint
- Attaching Lambda functions as tool targets
- Listing tools across all targets via single `tools/list`
- Invoking tools through the gateway (routing handled automatically)

```bash
cd demo-03-gateway-lambda
python deploy.py               # Create gateway + attach 3 Lambda targets
python invoke.py               # List tools + call tools via gateway JSON-RPC
python invoke_agent.py         # Strands agent discovers + uses gateway tools
python cleanup.py
```

**Talking points:**
- Gateway = single MCP endpoint that aggregates multiple backends
- Tool naming: `<TargetName>___<tool_name>` (triple underscore)
- Lambda targets: each function serves one or more tools
- No MCP code in Lambda — just business logic; gateway handles protocol
- Centralized auth, logging, and policy enforcement
- `invoke_agent.py` shows a real agent using gateway tools dynamically

---

### Demo 4: Gateway Semantic Search

**What to show the audience:**
- Problem: `tools/list` returns ALL tools (could be 300+)
- Solution: semantic search returns only relevant tools
- Uses built-in `x_amz_bedrock_agentcore_search` tool
- Natural language query → top matching tools

```bash
cd demo-04-gateway-search
python invoke.py               # Requires Demo 3 deployed
```

**Talking points:**
- Without search: agent sees all 300+ tools → slow, noisy context
- With search: agent describes what it needs → gets top 10 matches
- Built-in tool — no configuration needed on the gateway
- Critical for production: reduces token usage and improves accuracy
- Works across all target types (Lambda, OpenAPI, MCP servers)
- **Note:** Semantic search index takes 5-10 minutes to build after gateway targets are attached. Deploy Demo 3 early and let the index build before showing Demo 4.

---

### Demo 5: Cedar Policy Enforcement

**What to show the audience:**
- Creating a Cedar policy engine
- Attaching to gateway in ENFORCE mode (default-deny)
- Permitted tool call succeeds; denied tool call is blocked
- `tools/list` only shows permitted tools
- A Strands agent chatbot constrained by policy

```bash
cd demo-05-cedar-policy
python deploy.py               # Create policy engine + attach to Demo 3 gateway
python invoke.py               # Test: allowed vs denied (scripted)
python invoke_agent.py         # Interactive chatbot — agent constrained by policy
python cleanup.py              # Remove policy engine
```

**Talking points:**
- ENFORCE mode = default-deny (nothing works without explicit permit)
- Cedar language: `permit(principal, action, resource) when {...}`
- Deterministic, auditable — not probabilistic like LLM guardrails
- Principal tags from JWT claims enable ABAC (attribute-based access)
- Agent receives clear denial message — no silent failures
- `invoke_agent.py` shows a real agent trying to use tools — only weather works
- Agent receives clear denial message — no silent failures
- NL2Cedar: generate policies from plain English descriptions

---

## Recommended Order

1. **Demo 1** (5 min) — MCP protocol fundamentals
2. **Demo 2** (3 min) — Code Interpreter (no setup needed)
3. **Demo 3** (5 min) — Gateway unifies Lambda tools
4. **Demo 4** (3 min) — Semantic search (impressive for large tool catalogs)
5. **Demo 5** (5 min) — Policy enforcement (allow/deny demonstration)

**Total:** ~21 minutes

> **Important:** Run Demo 4 BEFORE Demo 5. Demo 5 attaches a Cedar policy (ENFORCE mode) that restricts tool visibility on the gateway. If Demo 5 is deployed, Demo 4's semantic search only sees 1 tool. Clean up Demo 5 before re-running Demo 4.

---

## Cleanup

```bash
# In reverse order
cd demo-05-cedar-policy && python cleanup.py
cd ../demo-03-gateway-lambda && python cleanup.py
cd ../demo-01-mcp-server && python cleanup.py

# Delete CloudFormation
cd ../cloudformation && ./cleanup-stack.sh
```
