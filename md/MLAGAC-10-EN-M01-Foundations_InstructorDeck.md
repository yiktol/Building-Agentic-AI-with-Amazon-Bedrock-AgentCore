# Module 1 — Foundations of Agentic AI Patterns

> Source deck: `ppt/MLAGAC-10-EN-M01-Foundations_InstructorDeck_Narrated.pptx`  
> 27 slides total. Each slide below shows the rendered slide image followed by its narration script.  
> Knowledge check questions are in a separate file: [`MLAGAC-10-EN-M01-Foundations_InstructorDeck_KnowledgeCheck.md`](MLAGAC-10-EN-M01-Foundations_InstructorDeck_KnowledgeCheck.md).

---

## Slide 1 — Foundations of Agentic AI Patterns

![M01 slide 1](images/M01/slide-01.png)

**Narration:**

> Welcome to Foundations of Agentic AI Patterns, the first module in Building Agentic AI with Amazon Bedrock AgentCore. In this module we lay the groundwork for everything that follows. We will explore what makes an AI system agentic, break down the components that every agent is built from, and introduce the Amazon Bedrock AgentCore services that help you take agents from an idea to production.

---

## Slide 2 — Agenda

![M01 slide 2](images/M01/slide-02.png)

**Narration:**

> Here is what we will cover. First, the fundamental building blocks of an agent. Then, an introduction to Amazon Bedrock AgentCore and the services it provides. By the end of this module you will be able to define the characteristics of agentic AI and distinguish it from traditional AI systems, identify the core components of an agent and how they interact, and describe how Bedrock AgentCore services map to and support those components.

---

## Slide 3 — Agent building blocks

![M01 slide 3](images/M01/slide-03.png)

**Narration:**

> Let's begin with the building blocks of an agent. To understand what AgentCore gives you, it helps to first understand what an agent actually is and the pieces it is made of.

---

## Slide 4 — Comparing traditional AI to agentic AI systems

![M01 slide 4](images/M01/slide-04.png)

**Narration:**

> Let's compare traditional AI to agentic AI. A traditional generative AI application processes an input and produces an output in a single pass. It is powerful, but it is passive. Agentic AI represents a shift from passive to active systems. Instead of just responding, an agent works toward a goal. It makes independent decisions, understands context and changing conditions, and adapts over time by learning from experience. Think of the difference between static printed directions and a GPS that reroutes you when traffic appears. An agent can reason about its actions, plan multiple steps ahead, and change its strategy based on feedback from its environment. This autonomous, cyclical decision-making is what lets agentic systems handle dynamic, unpredictable situations without constant human intervention.

---

## Slide 5 — Components of an agent

![M01 slide 5](images/M01/slide-05.png)

**Narration:**

> Every agent is built from five essential components that work together. First, the framework and agent code. This is the orchestration layer that manages the agent's behavior, coordinates the other components, and drives the overall workflow. Second, the large language model, which serves as the reasoning engine that processes information, makes decisions, and generates responses. Third, memory. Short-term memory holds the context of the current conversation, while long-term memory stores knowledge and lessons learned across past interactions. Fourth, tool integrations, which let the agent reach out to external systems, APIs, and services to take real-world actions. And fifth, inter-agent communication, which allows multiple agents to collaborate, share information, and coordinate on complex tasks. These components form an integrated system where each part depends on and strengthens the others. As we build on this foundation, keep two cross-cutting concerns in mind: security, which includes protecting data in memory, securing tool access, and defending against prompt injection; and observability, which means logging the agent's decisions, tracking tool usage, and monitoring performance. Because agents behave in dynamic and non-deterministic ways, they demand observability approaches that can trace reasoning, not just record outputs.

---

## Slide 6 — Discussion Point

![M01 slide 6](images/M01/slide-06.png)

**Narration:**

> Let's pause for a discussion. What makes an agentic system different from traditional AI? Take a moment to think it through. Agentic AI can autonomously make decisions, take actions, and pursue goals with minimal human intervention, often using tools and reasoning to complete complex tasks. Traditional AI, by contrast, tends to follow predefined rules or learned patterns without independent, goal-directed behavior. The key distinction is autonomy: agentic systems plan, reason, use external tools, and adapt based on feedback, while traditional systems execute predetermined logic.

---

## Slide 7 — Amazon Bedrock AgentCore introduction

![M01 slide 7](images/M01/slide-07.png)

**Narration:**

> Now that we understand what an agent is, let's introduce Amazon Bedrock AgentCore and see how it supports each of these components in production.

---

## Slide 8 — Prototype-to-production chasm

![M01 slide 8](images/M01/slide-08.png)

**Narration:**

> Let's talk about a challenge almost every team hits: the prototype-to-production chasm. It is relatively easy to get a basic agent working for a demo. Getting that same agent into production is where the real work begins. Many of us have built a compelling prototype and then struggled to deploy it reliably at scale. That gap, between a proof of concept and an enterprise-ready deployment, is defined by hard problems: scalability, security, performance, and complex state management. Amazon Bedrock AgentCore was purpose-built by AWS to bridge exactly this gap, providing the enterprise-grade capabilities that turn promising prototypes into real business value.

---

## Slide 9 — Introducing Amazon Bedrock AgentCore

![M01 slide 9](images/M01/slide-09.png)

**Narration:**

> So what is Amazon Bedrock AgentCore? It is a set of services that address the challenges of moving agents from prototypes into scalable, secure, and observable production systems. At a high level, AgentCore gives you a purpose-built agent runtime and identity management, simplified tool discovery and integration, both short-term and long-term memory, end-to-end visibility to trace, debug, and monitor your agents, and fully managed browser and code interpretation capabilities. Together these let you focus on your agent's logic instead of building and operating infrastructure.

---

## Slide 10 — AgentCore for production-ready agents

![M01 slide 10](images/M01/slide-10.png)

**Narration:**

> Here is the AgentCore stack for building production-ready agents. The important thing to understand is its flexibility. AgentCore works with any large language model and any agent framework, and its components can be used independently or combined like building blocks. The services include Runtime, which provides the execution environment; Gateway, for tool integration; Browser, for web interaction; Code Interpreter, for secure code execution; Identity, for security; Memory, for context management; Observability, for monitoring; and Evaluations, for assessing quality. As we go through the course, think about which of these services your own use case would need. You can learn more about each one in the Amazon Bedrock AgentCore Developer Guide.

---

## Slide 11 — Container-based and direct code deployments

![M01 slide 11](images/M01/slide-11.png)

**Narration:**

> Let's start with AgentCore Runtime. Runtime is a specialized, serverless execution environment designed specifically for AI agent workloads. Traditional serverless platforms are optimized for short-lived functions, but agents often need to run complex, multi-step processes that take much longer. Runtime provides fast cold starts for responsive interactions, true session isolation so that each user's context stays completely separate and secure, and support for multimodal payloads so agents can work with many data types. Because it is framework-agnostic, you can use any open-source framework such as LangGraph, Strands, or CrewAI. Automatic scaling and built-in security address the realities of enterprise deployment, so you deploy your agent and let the platform handle the rest.

---

## Slide 12 — AgentCore Identity

![M01 slide 12](images/M01/slide-12.png)

**Narration:**

> Next, AgentCore Identity. Security is not an afterthought for agents; it is fundamental. Agents frequently access sensitive data and perform actions on behalf of users, so you need strong identity controls from day one. AgentCore Identity provides security and access management built specifically for AI agents in enterprise environments. It manages secure agent identities, enforces least-privilege delegated access, and integrates with your existing identity providers so you don't have to migrate users. It includes a secure token vault that reduces consent fatigue, comprehensive audit trails for compliance, and a zero-trust posture that verifies every access request. Identity handles two directions of authentication. Inbound authentication verifies who the user is and whether they are allowed to interact with the agent. Outbound authentication establishes the agent's own identity and its authorization to access external resources on the user's behalf.

---

## Slide 13 — AgentCore Gateway

![M01 slide 13](images/M01/slide-13.png)

**Narration:**

> AgentCore Gateway tackles one of the most time-consuming parts of agent development: integrating with external tools and APIs. Traditionally, each tool means custom code, its own authentication scheme, and its own error handling, which adds up to weeks of work and ongoing maintenance. Gateway solves this systematically. It automates tool discovery and registration, transforms existing APIs, Lambda functions, and services into agent-compatible tools, and handles protocol translation between different systems. It also provides built-in error handling, retry logic, and security integration, exposing everything to your agent through consistent, standardized tool calls. You can even target an MCP server through Gateway. The real value is that Gateway abstracts away integration complexity while preserving the security and reliability that enterprises require.

---

## Slide 14 — AgentCore built-in tools

![M01 slide 14](images/M01/slide-14.png)

**Narration:**

> AgentCore also provides two powerful built-in tools. The first is AgentCore Browser, a fully managed, cloud-based browser runtime that lets agents interact with websites securely and at scale. It supports web automation such as navigation, form interaction, content extraction, and screenshot capture, all inside isolated environments. Consider an agent that logs in to vendor websites to download invoices for expense reporting, or one that monitors competitor sites for pricing changes. The managed service handles the scaling and the security isolation that would be difficult and risky to build yourself. The second built-in tool is AgentCore Code Interpreter, which lets agents securely write and run code in isolated sandbox environments. It supports languages including Python, TypeScript, and JavaScript with common libraries preinstalled, and it is ideal for large-scale data processing, data analysis and visualization, mathematical modeling, and file processing and transformation.

---

## Slide 15 — AgentCore Policy

![M01 slide 15](images/M01/slide-15.png)

**Narration:**

> AgentCore Policy gives you real-time authorization control over your agents by intercepting every tool call before it executes. You define authorization rules using Cedar, the AWS policy language that offers mathematical verification together with a human-readable syntax. You can even author policies in natural language, which are then converted into Cedar and checked against your gateway schemas to catch rules that are overly permissive or overly restrictive. When an agent requests a tool through AgentCore Gateway, the policy engine evaluates that call against your Cedar policies. You control which tools an agent can invoke based on input parameters, OAuth claims, and contextual conditions. Evaluation follows default-deny semantics, meaning you must explicitly permit an action, and any forbid policy always overrides a permit, so security restrictions can't be bypassed by conflicting rules. You manage policies as AWS resources, track their status, and receive detailed evaluation logs showing exactly why each request was allowed or denied.

---

## Slide 16 — AgentCore Memory

![M01 slide 16](images/M01/slide-16.png)

**Narration:**

> AgentCore Memory provides the context management that intelligent agent behavior depends on. It is helpful to compare it to human memory. Short-term memory is like working memory, holding the ongoing conversation and current session state. Long-term memory is like the facts and experiences you've accumulated over time, storing user preferences and important information so they persist across sessions and can even be shared between agents. This matters because language models have limited context windows, so external memory is essential for production agents. Building effective memory systems is hard, involving retrieval accuracy, relevance ranking, and storage efficiency. AgentCore Memory abstracts that complexity, giving you reliable retrieval so you can focus on agent logic while delivering coherent, personalized experiences that improve over time.

---

## Slide 17 — AgentCore Observability

![M01 slide 17](images/M01/slide-17.png)

**Narration:**

> AgentCore Observability gives you complete visibility into the agent lifecycle, which is essential, not optional, for production systems. Without proper monitoring you are effectively blind when something goes wrong, and agents are complex systems with many moving parts. Observability provides end-to-end tracing that follows the agent's decision-making, performance monitoring for latency and resource use, and detailed error detection and analysis. It is built on OpenTelemetry, so it is compatible with the observability tools you already use. You can integrate logs, metrics, and traces with Amazon CloudWatch, Datadog, Arize Phoenix, LangSmith, and Langfuse. Note that agents require instrumentation with the AWS Distro for OpenTelemetry. With unified dashboards, real-time alerting, historical trend analysis, and workflow visualizations, you can resolve issues faster, detect problems proactively, optimize performance with data, and meet compliance reporting requirements.

---

## Slide 18 — AgentCore Evaluations

![M01 slide 18](images/M01/slide-18.png)

**Narration:**

> The final service we'll introduce is AgentCore Evaluations, which provides quality assessment for production agents. It uses automated tools built on an LLM-as-a-judge approach, with both built-in and custom evaluators that measure quality across multiple dimensions. Let's define a few key terms. Evaluators are components that analyze an agent's traces and produce quantitative scores against specific criteria; AgentCore offers built-in evaluators that come pre-configured with optimized models and prompts, as well as custom evaluators that you define with your own instructions and scoring. Evaluation types come in two forms: online evaluation, which continuously monitors live production traffic with sampling and filtering, and on-demand evaluation, which targets specific interactions by analyzing chosen spans or traces. And evaluations can run at three levels: the tool-call level for individual tool invocations, the trace level for complete execution flows, and the session level for an entire user interaction.

---

## Slide 19 — Example agent: Customer service agent

![M01 slide 19](images/M01/slide-19.png)

**Narration:**

> To make these services concrete, here is the example we'll use throughout the course: a customer service agent. This agent is defined using the Strands Agents SDK and hosted on AgentCore Runtime. It has access to three tools hosted in that same runtime: one to get product information, one to get the return policy, and one to get technical support. It also uses a web search tool exposed through AgentCore Gateway using the Model Context Protocol. And it uses AgentCore Memory to recall customer preferences, behaviors, and facts from previous interactions. We will return to this example repeatedly as we explore each service in depth.

---

## Slide 20 — Your agent

![M01 slide 20](images/M01/slide-20.png)

**Narration:**

> Now let's turn it back to you and your own agent. As you think about what you want to build with agentic AI, consider how each AgentCore service could help you accomplish your goals. Which capabilities would you need from Runtime, from Memory, from Gateway, from Policy, from Identity, from the built-in Browser and Code Interpreter tools, from Observability, and from Evaluations? Keep your own use case in mind as we move through the rest of the course.

---

## Slide 26 — Module summary

![M01 slide 26](images/M01/slide-26.png)

**Narration:**

> Let's recap this module. You should now be able to define the characteristics of agentic AI and differentiate it from traditional AI systems, identify the core components of an agent and how they interact, and describe how Bedrock AgentCore services support agentic AI. These foundations will anchor everything we build in the modules ahead.

---

## Slide 27 — Questions?

![M01 slide 27](images/M01/slide-27.png)

**Narration:**

> That brings us to the end of this module. Take a moment to reflect on the concepts we've covered and how they apply to your own work. Agentic AI is a rapidly evolving field, and AWS provides many resources to support your continued growth, including the AWS documentation for detailed service information and best practices, AWS Training and Certification for building skills, and AWS Support for technical assistance. If any questions come up as you apply these ideas, this is a great time to ask.

---
