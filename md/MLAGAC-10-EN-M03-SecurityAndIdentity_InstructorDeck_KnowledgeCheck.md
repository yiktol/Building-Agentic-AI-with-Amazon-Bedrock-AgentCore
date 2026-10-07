# Module 3 — Security and Identity Management — Knowledge Check

> Source deck: `ppt/MLAGAC-10-EN-M03-SecurityAndIdentity_InstructorDeck_Narrated.pptx`  
> Knowledge check slides 23–27. Each slide shows the rendered slide image followed by its narration script.  
> Back to the module: [`MLAGAC-10-EN-M03-SecurityAndIdentity_InstructorDeck.md`](MLAGAC-10-EN-M03-SecurityAndIdentity_InstructorDeck.md).

---

## Slide 23 — Knowledge check

![M03 slide 23](images/M03/slide-23.png)

**Narration:**

> Let's check your understanding of security and identity with a short knowledge check.

---

## Slide 24 — Question 1

![M03 slide 24](images/M03/slide-24.png)

**Narration:**

> Here is the first question. A financial services company is implementing an AI agent that must access customer financial data across multiple internal systems. The security team requires that the agent maintain proper authentication context throughout its execution and provide detailed audit trails. Which AgentCore Identity configuration would best meet these requirements? Read the options carefully and select your answer before we continue.

---

## Slide 25 — Question 1: Answer

![M03 slide 25](images/M03/slide-25.png)

**Narration:**

> The correct answer is D: deploy the agent with Amazon Cognito authentication and configure a service-linked role for AgentCore Runtime. Let's review the others. Option A, an API key credential provider with custom logging middleware, is incorrect, because API keys suit system-to-system communication but do not inherently maintain authentication context throughout execution or provide the detailed audit trails that financial compliance demands. Option B, basic authentication with credentials in environment variables, is incorrect, because that approach is insecure and provides neither the context nor the audit capabilities required. Option C, a workload identity with OAuth 2.0 client credentials but with audit logging disabled, is incorrect, because disabling audit logging directly violates the requirement for detailed audit trails. Option D is correct, because Cognito authentication combined with the AgentCore Runtime service-linked role maintains proper authentication context throughout execution and automatically manages workload identity permissions while ensuring the comprehensive audit trails that financial services require.

---

## Slide 26 — Question 2

![M03 slide 26](images/M03/slide-26.png)

**Narration:**

> Here is the second question. A company is developing an agent that will access multiple third-party services, including Salesforce, ServiceNow, and internal databases. The security team wants the agent to maintain proper security boundaries between different authentication systems and to support both user-delegated access and machine-to-machine authentication. Which AgentCore Identity feature best addresses these requirements? Review the options and choose your answer.

---

## Slide 27 — Question 2: Answer

![M03 slide 27](images/M03/slide-27.png)

**Narration:**

> The correct answer is A: a workload identity with multiple credential providers. Let's review why. Option A is correct, because workload identities serve as stable digital anchors that persist across environments and authentication schemes. They support multiple credential types simultaneously, such as IAM roles, OAuth 2.0 tokens, and API keys, and they abstract the complexity of managing those mechanisms behind a unified interface, which lets the agent maintain proper security boundaries while supporting both user-delegated and machine-to-machine authentication. Option B, a single shared API key, is incorrect, because sharing one key across all services violates the security boundaries between systems and cannot support user-delegated access. Option C, direct IAM role assumption for all external services, is incorrect, because IAM roles are specific to AWS and cannot authenticate directly with external services like Salesforce or ServiceNow. And option D, manual token management in agent code, is incorrect, because it increases security risk and complexity and ignores the centralized credential management that Identity provides.

---
