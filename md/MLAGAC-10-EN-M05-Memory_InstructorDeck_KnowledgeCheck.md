# Module 5 — Agentic Memory Implementation — Knowledge Check

> Source deck: `ppt/MLAGAC-10-EN-M05-Memory_InstructorDeck_Narrated.pptx`  
> Knowledge check slides 33–37. Each slide shows the rendered slide image followed by its narration script.  
> Back to the module: [`MLAGAC-10-EN-M05-Memory_InstructorDeck.md`](MLAGAC-10-EN-M05-Memory_InstructorDeck.md).

---

## Slide 33 — Knowledge check

![M05 slide 33](images/M05/slide-33.png)

**Narration:**

> Let's check your understanding of agentic memory with a short knowledge check.

---

## Slide 34 — Question 1

![M05 slide 34](images/M05/slide-34.png)

**Narration:**

> Here is the first question. A development team is building a customer support agent that needs to remember customer preferences across multiple conversations. The agent must recall specific product preferences and previous issues even when customers return days later. Which memory pattern should the team implement? Read the options carefully and select your answer.

---

## Slide 35 — Question 1: Answer

![M05 slide 35](images/M05/slide-35.png)

**Narration:**

> The correct answer is C: the user preference memory strategy with actor-based namespaces. Let's review why. Option A, short-term memory with session checkpointing, is incorrect, because short-term memory only maintains context within a single session and does not persist preferences across conversations over days. Option B, semantic memory with session-based retrieval, is incorrect, because semantic memory focuses on factual, domain-specific knowledge rather than individual user preferences, which makes it less suitable here. Option C is correct, because the user preference strategy is designed specifically to capture and store recurring patterns in user behavior and explicit preferences across multiple sessions, and actor-based namespaces keep each customer's preferences isolated, which is exactly what remembering product preferences across conversations requires. And option D, a custom strategy with a seven-day event expiry, is incorrect, because it stores information only temporarily and doesn't specifically target preferences, and a seven-day limit may be too short for an ongoing customer relationship.

---

## Slide 36 — Question 2

![M05 slide 36](images/M05/slide-36.png)

**Narration:**

> Here is the second question. Which statement correctly describes the relationship between short-term and long-term memory in AgentCore Memory? Review the options and choose your answer.

---

## Slide 37 — Question 2: Answer

![M05 slide 37](images/M05/slide-37.png)

**Narration:**

> The correct answer is C: short-term memory stores raw events, while long-term memory contains processed, structured information. Let's review the others. Option A, which says extraction requires a manual consolidate API, is incorrect, because the extraction from short-term to long-term memory is automatic and asynchronous, and there is no manual consolidate API. Option B, which says long-term memory synchronizes with short-term memory in real time, is incorrect, because extraction is an asynchronous background process, not real-time synchronization. Option C is correct, because short-term memory stores the raw conversation events, while long-term memory holds the processed, structured information that has been extracted and consolidated from those raw events. And option D, which says long-term memory must be configured for each conversation session, is incorrect, because long-term memory is configured at the memory resource level using strategies, not per individual session.

---
