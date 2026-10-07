# Module 2 — AgentCore Runtime and Framework Integration — Knowledge Check

> Source deck: `ppt/MLAGAC-10-EN-M02-Runtime_InstructorDeck_Narrated.pptx`  
> Knowledge check slides 27–31. Each slide shows the rendered slide image followed by its narration script.  
> Back to the module: [`MLAGAC-10-EN-M02-Runtime_InstructorDeck.md`](MLAGAC-10-EN-M02-Runtime_InstructorDeck.md).

---

## Slide 27 — Knowledge check

![M02 slide 27](images/M02/slide-27.png)

**Narration:**

> Let's check your understanding of AgentCore Runtime with a short knowledge check.

---

## Slide 28 — Question 1

![M02 slide 28](images/M02/slide-28.png)

**Narration:**

> Here is the first question. What is the primary security benefit of AgentCore Runtime's session isolation approach? Read each option carefully and select your answer before we reveal it.

---

## Slide 29 — Question 1: Answer

![M02 slide 29](images/M02/slide-29.png)

**Narration:**

> The correct answer is B: it runs each session in a completely isolated microVM with separate compute, memory, and filesystem. Let's review the others. Option A, encrypting all data with a key management service, is incorrect, because encryption is not described as the primary security benefit of session isolation. Option B is correct, because, as we discussed, each session runs in its own isolated microVM, and this physical isolation ensures that no session can access the files, state, or objects of another session, preventing data leakage. Option C, automatic termination after eight hours, is incorrect, because while sessions do have an eight-hour maximum, that is a resource management feature rather than the core security benefit of isolation. And option D, requiring multi-factor authentication, is incorrect, because that is not a feature of Runtime's session isolation.

---

## Slide 30 — Question 2

![M02 slide 30](images/M02/slide-30.png)

**Narration:**

> Here is the second question. A development team is creating an AI agent that needs to perform long-running data analysis tasks that can take up to several hours. The team wants users to receive immediate responses while the analysis runs in the background, and they need the agent to maintain its state throughout the process. Which AgentCore Runtime feature should the team implement? Review the options and choose your answer.

---

## Slide 31 — Question 2: Answer

![M02 slide 31](images/M02/slide-31.png)

**Narration:**

> The correct answer is C: container-based deployment with asynchronous task processing. Let's review why. Option A, direct code deployment with custom timeouts, is incorrect, because direct code deployment is about the deployment method, not about handling long-running background work. Option B, multiple agent instances with load balancing, is incorrect, because adding instances increases capacity but does not provide background processing with immediate user responses. Option C is correct, because Runtime supports asynchronous and long-running jobs, using methods like add_async_task so the agent can immediately acknowledge the request and continue working in the background for up to eight hours while maintaining session state, which is exactly what long-running data analysis requires. And option D, streaming responses, is incorrect, because streaming alone does not address the need for background processing of long-running tasks.

---
