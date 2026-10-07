# Module 4 — Tool Integration and AgentCore Gateway — Knowledge Check

> Source deck: `ppt/MLAGAC-10-EN-M04-ToolsAndGateway_InstructorDeck_Narrated.pptx`  
> Knowledge check slides 47–51. Each slide shows the rendered slide image followed by its narration script.  
> Back to the module: [`MLAGAC-10-EN-M04-ToolsAndGateway_InstructorDeck.md`](MLAGAC-10-EN-M04-ToolsAndGateway_InstructorDeck.md).

---

## Slide 47 — Knowledge check

![M04 slide 47](images/M04/slide-47.png)

**Narration:**

> Let's check your understanding of tools and Gateway with a short knowledge check.

---

## Slide 48 — Question 1

![M04 slide 48](images/M04/slide-48.png)

**Narration:**

> Here is the first question. A development team is building an agentic AI application that needs to perform complex data analysis on large datasets stored in Amazon S3. The agent must analyze financial data, generate insights, and create visualizations without exposing sensitive financial information. Which tool integration approach best meets these requirements with the least operational overhead? Read the options and choose your answer.

---

## Slide 49 — Question 1: Answer

![M04 slide 49](images/M04/slide-49.png)

**Narration:**

> The correct answer is A: implement AgentCore Code Interpreter with VPC support for secure data processing. Let's review why. Option A is correct, because Code Interpreter lets agents securely write and run code in isolated sandboxes, with VPC support for accessing internal data without exposing it, and it specifically supports large-scale data processing by referencing files in Amazon S3 to process gigabyte-scale data without API limitations, which fits this scenario exactly. Option B, using the Browser to access web-based visualization tools, is incorrect, because the Browser is designed for web workflows, not secure data analysis of S3 data. Option C, a custom MCP server hosted on premises, is incorrect, because hosting on premises adds unnecessary complexity and doesn't leverage AWS's built-in security for sensitive data. And option D, Lambda functions with OpenAPI specifications, is incorrect, because Lambda has execution-time limitations that make it less suitable than Code Interpreter for complex analysis of large datasets.

---

## Slide 50 — Question 2

![M04 slide 50](images/M04/slide-50.png)

**Narration:**

> Here is the second question. A developer is building an application that needs to interact with both local tools and remote services. The agent requires low latency for frequent mathematical calculations but also needs to access shared enterprise data services managed by a different team. Which MCP server hosting approach is most appropriate? Review the options and select your answer.

---

## Slide 51 — Question 2: Answer

![M04 slide 51](images/M04/slide-51.png)

**Narration:**

> The correct answer is C: use a hybrid approach, with local hosting for the calculation tools and remote hosting for the shared data services. Let's review why. Option A, hosting all servers remotely, is incorrect, because it would add unnecessary latency to the frequent mathematical calculations. Option B, hosting all servers locally, is incorrect, because it would limit the ability to share tools across agents and to access the enterprise data services. Option C is correct, because local hosting provides minimal latency, which is ideal for the frequent calculations, while remote hosting enables shared tools across multiple agents, which is necessary for the enterprise data services managed by another team, and it also lets different teams use their preferred technologies. And option D, deploying everything as Lambda functions through Gateway, is incorrect, because Lambda would not provide the lowest latency for frequent calculations and carries execution-time limitations.

---
