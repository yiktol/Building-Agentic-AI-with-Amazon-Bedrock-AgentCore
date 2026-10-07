# Module 6 — Production Monitoring and Observability — Knowledge Check

> Source deck: `ppt/MLAGAC-10-EN-M06-DeploymentObservablity_InstructorDeck_Narrated.pptx`  
> Knowledge check slides 32–36. Each slide shows the rendered slide image followed by its narration script.  
> Back to the module: [`MLAGAC-10-EN-M06-DeploymentObservablity_InstructorDeck.md`](MLAGAC-10-EN-M06-DeploymentObservablity_InstructorDeck.md).

---

## Slide 32 — Knowledge check

![M06 slide 32](images/M06/slide-32.png)

**Narration:**

> Let's check your understanding of monitoring and observability with a short knowledge check.

---

## Slide 33 — Question 1

![M06 slide 33](images/M06/slide-33.png)

**Narration:**

> Here is the first question. A development team has deployed an agentic AI application using Amazon Bedrock AgentCore. They need to monitor the agent's performance and troubleshoot issues in production, and they want to understand the complete flow of user interactions, including which tools are called and how the agent makes decisions. Which approach should they implement? Read the options carefully and select your answer.

---

## Slide 34 — Question 1: Answer

![M06 slide 34](images/M06/slide-34.png)

**Narration:**

> The correct answer is B: configure AgentCore Observability with OpenTelemetry instrumentation to capture sessions, traces, and spans. Let's review why. Option A, enabling X-Ray tracing and setting up custom CloudWatch metrics for each component, is incorrect, because while X-Ray provides distributed tracing, it isn't purpose-built for the hierarchical session, trace, and span structure that agents need. Option B is correct, because AgentCore Observability with OpenTelemetry instrumentation provides comprehensive monitoring through CloudWatch and captures the full hierarchy of sessions, traces, spans, and sub-spans, giving visibility into reasoning steps, tool invocations, and model interactions, which is exactly what's needed to understand decision-making and troubleshoot. Option C, custom logging to Amazon S3, is incorrect, because it would require significant development effort and wouldn't provide structured visibility into decision-making. And option D, CloudWatch Synthetics canaries, is incorrect, because canaries test availability and performance but don't provide detailed visibility into agent reasoning and tool invocations.

---

## Slide 35 — Question 2

![M06 slide 35](images/M06/slide-35.png)

**Narration:**

> Here is the second question. Which view in the CloudWatch generative AI observability dashboard provides information about individual agent metrics, AgentCore Runtime metrics, and a list of sessions? Review the options and choose your answer.

---

## Slide 36 — Question 2: Answer

![M06 slide 36](images/M06/slide-36.png)

**Narration:**

> The correct answer is B: the Agent detail view. Let's review why. Option A, the Agents view, is incorrect, because it provides an overview of all agents rather than detailed metrics for an individual agent. Option B is correct, because the Agent detail view, which you reach by selecting an individual agent from the Agents view, provides that agent's individual metrics, its AgentCore Runtime metrics, and a list of its sessions, including metrics like session and trace counts, foundation model token usage, system and client errors, errors and latency by span, throttles, and authentication metrics. Option C, the Session detail view, is incorrect, because it shows details about a specific session, not individual agent metrics. And option D, the Trace detail view, is incorrect, because it shows information about specific traces, not individual agent metrics.

---
