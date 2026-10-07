# Module 5 — Agentic Memory Implementation

> Source deck: `ppt/MLAGAC-10-EN-M05-Memory_InstructorDeck_Narrated.pptx`  
> 39 slides total. Each slide below shows the rendered slide image followed by its narration script.  
> Knowledge check questions are in a separate file: [`MLAGAC-10-EN-M05-Memory_InstructorDeck_KnowledgeCheck.md`](MLAGAC-10-EN-M05-Memory_InstructorDeck_KnowledgeCheck.md).

---

## Slide 1 — Agentic Memory Implementation

![M05 slide 1](images/M05/slide-01.png)

**Narration:**

> Welcome to Agentic Memory Implementation. Memory is what transforms a stateless chatbot into an intelligent assistant that remembers you. In this module we'll explore the core concepts of agentic memory, dig into how AgentCore Memory provides both short-term and long-term memory, and look at how to secure that memory so that each user's data stays isolated and protected.

---

## Slide 2 — Agenda

![M05 slide 2](images/M05/slide-02.png)

**Narration:**

> Here is our agenda. We'll start with the core concepts of agentic memory, then move into AgentCore Memory itself, and finish with securing AgentCore Memory. By the end of this module you will be able to implement agentic memory patterns for different use cases, configure AgentCore Memory operations for context-aware development, and optimize memory performance for production workloads.

---

## Slide 3 — Agentic memory core components

![M05 slide 3](images/M05/slide-03.png)

**Narration:**

> Let's begin with the core concepts of agentic memory.

---

## Slide 4 — Remember me?

![M05 slide 4](images/M05/slide-04.png)

**Narration:**

> Consider a simple frustration: remember me? Imagine asking an assistant how to switch apps on your iPhone. It asks which model you have, you say the iPhone 16, and it helps you. Then, two days later, you ask how to take a screenshot, and it asks again which model you have. That loss of context makes the experience feel robotic and impersonal. The reason this happens is fundamental to how agents think. Agents reason by sending requests to a language model, and each request is isolated; the model does not automatically have access to its previous responses. To create continuity, you must provide memories to the model with each new request, reminding it of the conversation so far. Memory lets an agent reference earlier statements, build on previous responses, and provide personalized help, turning disconnected question-and-answer pairs into natural, flowing conversation. Without memory, agents become inefficient tools that force you to repeat yourself.

---

## Slide 5 — How agents use memory

![M05 slide 5](images/M05/slide-05.png)

**Narration:**

> Agents use memory for three distinct purposes that work together. The first is contextual intelligence, which elevates the accuracy and relevance of responses through contextual understanding and pattern recognition, keeping track of what you just discussed and the ongoing task within the current session. The second is user preferences, which personalizes interactions by remembering your stated preferences and inferring patterns from your behavior across multiple sessions. The third is knowledge retention, which enables sophisticated problem-solving through persistent memory and continuous learning, building an understanding of important facts, entities, and relationships over time. To make this concrete, a customer support agent might remember your current order number as contextual intelligence, know that you prefer detailed technical explanations as a user preference, and recall that your company has five hundred employees across three locations as retained knowledge. Together, these three purposes create agents that understand both the immediate moment and the long-term relationship.

---

## Slide 6 — Memory types

![M05 slide 6](images/M05/slide-06.png)

**Narration:**

> Agent memory operates on two complementary levels that mirror human memory. Short-term memory maintains raw data, including the ongoing conversation context, the current session attributes, and the agent's state through checkpointing, and it lets you retrieve messages exactly as they occurred. It answers the question, what did we just discuss, and it keeps context intact even if the system restarts or you return later to continue the same conversation. Long-term memory maintains processed information, including user preferences, session summaries, and learned facts and concepts, and it enables customization of the agent's behavior over time. It answers a different question: who is this user, and what have we learned about them. This dual approach gives you both immediate conversational continuity and an intelligence that evolves with every interaction.

---

## Slide 7 — Short-term memory

![M05 slide 7](images/M05/slide-07.png)

**Narration:**

> Let's see short-term memory in action with our iPhone example, but this time with memory working. You ask how to switch apps, the assistant asks your model, you say iPhone 16, and it helps. Then when you ask how to take a screenshot, the assistant already knows you have an iPhone 16 and simply helps you directly, within that same conversation. Three qualities define good short-term memory. It stays present in your conversation, not just recalling words but following your train of thought. It understands your immediate needs, recognizing what you're trying to accomplish right now. And it picks up exactly where you left off, with no awkward restarts or repetition.

---

## Slide 8 — Long-term memory: user preferences

![M05 slide 8](images/M05/slide-08.png)

**Narration:**

> Now let's look at long-term memory, starting with user preferences. Imagine you tell the assistant that you like a particular brand of headphones; it stores that as a memory. In a later conversation you mention you prefer white, open-ear headphones, and that you get a twenty-five percent corporate discount. The agent stores these preferences too. Then, when you say it's time to replace your old headphones, the agent checks its user preferences memory, sees that you like that brand in white with an open-ear design, and factors in your discount, so it can proactively suggest white, open-ear replacement options within your budget and even some premium models your discount brings into reach. The user preferences memory, holding facts like your preferred brand, color, and style, is built up and updated over time, which is what makes the interaction feel personalized.

---

## Slide 9 — Long-term memory: Semantic

![M05 slide 9](images/M05/slide-09.png)

**Narration:**

> A second kind of long-term memory is semantic memory, which stores facts and knowledge. For this example, assume facts have already been extracted and stored. Suppose you say you want to return the headphones you bought last week because you found them one hundred dollars cheaper elsewhere. The agent checks its semantic memory, which holds facts like the product's price of about three hundred fifty dollars, the thirty-day return policy, the fourteen-day price-match window, alternative models in a similar price range, and customer satisfaction protocols. Using those facts, the agent can respond helpfully: it can offer a one-hundred-dollar price-match adjustment within the fourteen-day window, or a full refund if you return the item within the thirty-day window. So an agent uses semantic long-term memory to look up the specific facts that relate to your request.

---

## Slide 10 — Long-term memory: Summary

![M05 slide 10](images/M05/slide-10.png)

**Narration:**

> A third long-term memory strategy is the session summary. Here's how it works. The agent takes the current session's short-term memory, which contains the specifics of the latest interaction, and sends it to a language model to produce a concise summary, which it then stores in long-term memory. For example, after a conversation the stored summary might read: the user bought new white, open-ear headphones to replace their old ones, found a cheaper price later, and received a one-hundred-dollar adjustment. Later, when you return and say your headphones broke, the agent checks that summary, immediately recognizes which product you bought, and responds with empathy and context, asking what issue you're experiencing. Session summaries give the agent a compact, meaningful memory of each past interaction without storing every single message.

---

## Slide 11 — Agentic memory current challenges

![M05 slide 11](images/M05/slide-11.png)

**Narration:**

> It's important to be honest about the current challenges in agentic memory, because they shape how you design and secure your systems. There are six to keep in mind: storage scalability, memory refresh, integration complexity, privacy and security, retrieval accuracy, and observability. Memory introduces new security and operational concerns. Memory poisoning occurs when a malicious actor embeds false information in conversations to corrupt the agent's knowledge base, and prompt injection attacks try to manipulate how the system processes and stores information. Data leakage is a risk when sensitive information from one user becomes accessible to another through a shared memory system. Performance becomes a challenge as memory stores grow and retrieval speed matters more for the user experience. And compliance demands complete traceability of how an agent made decisions based on stored memories. AgentCore Memory addresses these through built-in security controls, automatic memory isolation between users, monitoring for suspicious patterns, and comprehensive audit trails, so you can focus on building intelligent experiences rather than managing security and performance infrastructure.

---

## Slide 12 — AgentCore Memory

![M05 slide 12](images/M05/slide-12.png)

**Narration:**

> With those concepts in mind, let's look at AgentCore Memory, the managed service that provides these capabilities.

---

## Slide 13 — AgentCore Memory

![M05 slide 13](images/M05/slide-13.png)

**Narration:**

> Traditional AI agents operate without memory of previous interactions, treating every conversation as brand new. AgentCore Memory solves this by providing fully managed memory capabilities that enable context-aware conversations. The service maintains short-term context during active sessions and extracts meaningful insights for long-term retention across sessions. This managed approach eliminates the need to build complex memory infrastructure yourself, while giving your agents both immediate conversational context and cumulative intelligence that grows over time. In short, it turns stateless agents into agents that remember.

---

## Slide 14 — AgentCore Memory: building blocks for AI agents

![M05 slide 14](images/M05/slide-14.png)

**Narration:**

> Let's survey the building blocks that AgentCore Memory gives you, organized into four areas. The first is core infrastructure: a serverless architecture with minimal setup, built-in encryption to protect sensitive conversation data, flexible namespaces for organizing and sharing memory across users and applications, and flexible time-to-live settings to control how long memory persists and balance cost against retention. The second is memory management: support for both short-term and long-term memory, built-in memory consolidation, a single API to store multiple messages as one interaction through checkpointing, and list and delete APIs. The third is memory extraction: built-in or custom extraction strategies covering user preferences, semantic memory, and session summaries, with automatic extraction running in the background. And the fourth is memory retrieval: multiple retrieval patterns including semantic search, which finds relevant memories by meaning rather than exact match, and filtering, which narrows results by timeframe, user, or session. Observability features also provide insight into memory operations through CloudWatch metrics, logs, and tracing.

---

## Slide 15 — AgentCore Memory high level overview

![M05 slide 15](images/M05/slide-15.png)

**Narration:**

> Here's a high-level overview of how AgentCore Memory fits together. There are two interconnected systems. Short-term memory captures the immediate conversation flow within a single session; every interaction between the user and the agent becomes an event, which you create with the create-event operation, specifying session and actor IDs for organization. This raw event data is the material that feeds the long-term memory pipeline. Your configured memory strategy then automatically extracts meaningful insights from those events, in the background, asynchronously, so live interactions are never interrupted. The resulting long-term memory records become retrievable through semantic search, so when you query past interactions, the system finds relevant memories across many sessions. You organize these memories with namespaces, using a hierarchical structure with forward slashes, which lets you control granularity from global access down to session-specific isolation and keep different users' data separate. During a conversation, the agent draws on both memory types: short-term for immediate context and long-term for historical insight. Together they turn stateless interactions into meaningful, context-aware conversations that improve over time. Remember too that the infrastructure is serverless with minimal setup, with built-in encryption, flexible namespaces, and flexible time-to-live.

---

## Slide 16 — AgentCore Memory: Short-term memory key concepts

![M05 slide 16](images/M05/slide-16.png)

**Narration:**

> Let's define the three foundational concepts of short-term memory: events, actors, and sessions. Events are the records of interactions and conversations between users and the agent. They can include conversational messages, which may come from the user, a tool, or the agent, as well as agent checkpoints, and you can store them one at a time or in batches. You create events with the create-event operation, and each event is immutable and timestamped, giving you a permanent record of what happened. Actors are identifiers for users, or for an agent-and-user combination, and they track who the memory belongs to, which helps separate and organize memories by user and maintain privacy. You specify an actor ID when creating events, and you use it to retrieve a specific conversation history. Sessions represent a single conversation or interaction period; each session has a unique session ID, and it groups related messages and events so the agent can understand conversational boundaries and maintain context. You can retrieve all events within a session to reconstruct the complete conversation flow.

---

## Slide 17 — Short-term memory

![M05 slide 17](images/M05/slide-17.png)

**Narration:**

> Here's how to create a memory resource configured for short-term memory only. This is useful for tracking the flow of a current conversation, such as a customer support interaction, and in this configuration it creates only short-term memory, not long-term memory. In the code, you import the MemoryClient from the bedrock_agentcore memory module and initialize it with your region. You then call create_memory, giving it a name, a description, and, importantly, an event expiry of seven days. That expiry setting controls how long your conversation data persists; after seven days, the system automatically removes the stored events, which helps you manage storage costs while keeping recent context. Because this configuration has no long-term strategy, you won't get persistent insights or user preferences from it. Instead, you get immediate conversational context that supports the current interaction.

---

## Slide 18 — Short-term memory: Create and retrieve events

![M05 slide 18](images/M05/slide-18.png)

**Narration:**

> Now let's see how to create and retrieve events in short-term memory. The create-event call stores agent interactions instantly; here you provide the memory ID, the actor ID, and the session ID, along with a list of messages. In the example, the messages capture a user reporting trouble with an order, the assistant acknowledging and offering to look it up, and a tool call to look up the order, each tagged with its role. To read data back, the get-event operation retrieves a specific conversation event by its event ID, and the list-events operation loads all events for a given memory ID, actor ID, and session ID. So create-event writes, get-event fetches one, and list-events fetches the whole conversation.

---

## Slide 19 — Long-term memory – Memory management

![M05 slide 19](images/M05/slide-19.png)

**Narration:**

> Let's look at long-term memory management and how data flows through it. Your agent captures each conversation turn as an event in short-term memory, storing the immediate context. AgentCore Memory then uses memory strategies to automatically extract meaningful insights from those raw events, analyzing patterns to identify important information like user preferences, key facts, and session summaries. This processing happens asynchronously in the background while your agent keeps operating, so there's no interruption to the live conversation. You can configure different extraction strategies based on your needs: built-in strategies handle common patterns, while custom strategies let you define logic specific to your use case. The transformation from temporary to permanent storage happens automatically once you define trigger conditions, such as a message count or a time interval, which keeps the transition seamless for your users. In the diagram, raw events flow from the agent into short-term memory, then a strategy processes them into retrievable long-term memory records.

---

## Slide 20 — AgentCore Memory: Long-term memory strategies

![M05 slide 20](images/M05/slide-20.png)

**Narration:**

> AgentCore Memory offers several long-term memory strategies that determine how information flows from conversations into persistent storage. Let's define each one. The summaries strategy creates condensed representations of interaction content and outcomes. The user preferences strategy stores and learns recurring patterns in user behavior, interaction styles, and choices. The semantic strategy maintains knowledge of facts and domain-specific information, including technical concepts and their relationships. The episodic strategy captures meaningful slices of user and system interactions, helping the agent understand how context has evolved over time. And the custom strategy lets you override the prompts and choose the language model, tailoring extraction and consolidation to your specific domain. Multiple strategies can operate at the same time, and you must configure at least one strategy for long-term extraction to occur. Choose the strategy, or combination of strategies, that matches what your application needs to remember.

---

## Slide 21 — Customizing memory strategies

![M05 slide 21](images/M05/slide-21.png)

**Narration:**

> When the built-in strategies aren't quite right, you can customize memory strategies in two ways. The first is to use a built-in strategy with overrides, which extends the default strategies while keeping the AgentCore-managed extraction pipeline. This lets you modify the prompts and select specific foundation models, giving you control over granularity and model selection while still benefiting from the managed pipeline. The second is to use a self-managed strategy, which gives you complete ownership of the memory pipeline. With this approach you define custom extraction and consolidation algorithms, use any model or prompts you want, and define your own memory record schemas, which provides maximum flexibility for specialized use cases. In short, overrides give you tuning within the managed pipeline, while self-managed gives you full control for the most demanding scenarios.

---

## Slide 22 — Moving from short-term to long-term memory

![M05 slide 22](images/M05/slide-22.png)

**Narration:**

> Let's trace the full journey from short-term to long-term memory. After conversations are stored in short-term memory, a background process transforms that raw data into structured, persistent knowledge. The trigger fires every so many messages, or after a period of inactivity, which keeps extraction efficient. When it fires, a language model analyzes the content to extract meaningful insights, retrieves similar existing memories, and then decides whether to add a new memory, update an existing one, or skip, which handles deduplication and consolidation automatically. All of this runs asynchronously, so response times during the conversation stay fast while cumulative intelligence builds over time. A couple of practical notes: provisioning a memory resource takes roughly two to five minutes to activate, after which extraction runs continuously in the background, and memory records support configurable retention periods of up to three hundred sixty-five days.

---

## Slide 23 — Saving Conversations and Retrieval

![M05 slide 23](images/M05/slide-23.png)

**Narration:**

> Let's look at the code for saving conversations and retrieving memories. The create-event operation saves events to short-term memory; here you provide the memory ID, an actor ID, a session ID, and the messages from the conversation. Saving events is what triggers the asynchronous extraction of long-term memory every so many turns, so you don't call a separate extraction API. To read insights back, the retrieve-memories operation performs a semantic search over the stored long-term memory; you provide the memory ID, a namespace that scopes the search, and a natural-language query such as, what happened with my order issue. The system returns the relevant memory records from previous interactions. This dual-operation approach gives your agent both immediate context awareness, through the events, and historical knowledge, through semantic retrieval, so when a user returns with a related question, the agent can surface the relevant past experience.

---

## Slide 24 — Organizing long-term memory: Namespaces

![M05 slide 24](images/M05/slide-24.png)

**Narration:**

> Namespaces are how you organize long-term memory. A namespace logically groups and organizes memories using a hierarchical format with forward slashes, much like a file-system path. Namespaces can include variables such as actor ID, strategy ID, and session ID, which get substituted at runtime, and they are required when you define memory strategies. For example, a pattern like slash summaries, slash actor ID, slash session ID organizes session summaries by user and session, while a pattern like slash users, slash actor ID, slash preferences organizes user preferences. The actor ID identifies the participant, the session ID tracks a specific conversation thread, and the strategy ID categorizes memory by extraction strategy. Good namespace design enables efficient categorization, filtering, and retrieval, and it's essential for supporting multi-tenant applications and access control, which we'll see when we discuss security.

---

## Slide 25 — Strands Agents example using tools (1of 2)

![M05 slide 25](images/M05/slide-25.png)

**Narration:**

> Let's walk through a Strands Agents example that uses memory as a tool; this is the first of two steps. In this approach, you integrate AgentCore Memory as a tool within the Strands framework, which gives your agent explicit memory capabilities, so it actively reads from and writes to memory during conversations rather than relying only on passive background storage. Step one is to define a memory resource. You create a MemoryClient for your region, then call create-memory-and-wait, which establishes a memory container and waits for it to be ready. Here you configure a user preference strategy with a namespace pattern of slash users, slash actor ID, which creates an isolated memory space for each user and prevents data from mixing between conversations. The user preference strategy will automatically identify and retain personal details, such as dietary restrictions or location preferences, in those per-user namespaces.

---

## Slide 26 — Strands Agents example using tools (2 of 2)

![M05 slide 26](images/M05/slide-26.png)

**Narration:**

> Here's step two of the tool-based example: adding memory to the agent. You use the AgentCore Memory tool provider from the Strands tools package. You configure it with the memory ID, an actor ID, a session ID, a namespace, and the region. You then create the agent, passing in the tools exposed by that provider. Now, as the agent runs, it can invoke memory tools: in the example, the user says they're vegetarian, then that they're in the mood for Italian cuisine, and later asks whether the agent remembers their preferences, at which point the agent retrieves the stored preferences. The tool-based approach lets the agent make deliberate decisions about when to access memory, querying to recall preferences, writing new information as it learns, and updating records when preferences change, which is a more active form of memory management than passive background processing.

---

## Slide 27 — Strands Agents example using hooks (1 of 2)

![M05 slide 27](images/M05/slide-27.png)

**Narration:**

> There's a second integration pattern using Strands hooks, and this is the first of its two steps. Hooks let you run memory operations automatically when specific events occur during an agent session, rather than exposing memory as a tool the agent chooses to call. Step one, as before, is to define a memory resource. You create a MemoryClient for your region, then call create-memory-and-wait, this time configuring a semantic strategy with a namespace pattern of slash users, slash actor ID. The semantic strategy will extract facts and domain knowledge from the conversation into those per-user namespaces.

---

## Slide 28 — Strands Agents example using hooks (1 of 2)

![M05 slide 28](images/M05/slide-28.png)

**Narration:**

> Here's step two of the hooks example: adding memory to the agent with a hook provider. You define a class that implements the Strands hook provider interface. It has a retrieve method that runs when a message is added, fetching relevant memories, and a save method that runs after an invocation completes, storing new memories by calling create-event. You register these callbacks: the retrieve method on the message-added event, and the save method on the after-invocation event. Then you create the agent, passing in your memory hooks. The difference from the tool-based approach is that here memory operations happen automatically at defined points in the session lifecycle, retrieving context when a message arrives and saving memory when the agent finishes responding, without the agent having to decide to call a tool.

---

## Slide 29 — Securing AgentCore memory

![M05 slide 29](images/M05/slide-29.png)

**Narration:**

> Now let's turn to securing AgentCore Memory, which is essential because memory stores sensitive conversational and personal data.

---

## Slide 30 — Memory security

![M05 slide 30](images/M05/slide-30.png)

**Narration:**

> Let's start with the basics of memory security. Memory systems store conversational context, user preferences, and business data across sessions, which creates security challenges beyond those of a traditional application. AWS follows a shared responsibility model: AWS secures the underlying infrastructure, while you implement proper access controls, input validation, and memory isolation. A critical threat to understand is memory poisoning, where an attacker injects false information into conversations to corrupt long-term memory. This can manifest as context pollution, where incorrect information influences future responses, or as a deliberate attack on data integrity targeting stored knowledge. The foundation of memory security is AWS Identity and Access Management, which you use to control access to both short-term and long-term memory. Proper security requires understanding both traditional controls and these AI-specific vulnerabilities that can compromise an agent's behavior.

---

## Slide 31 — Security – Fine-grained access

![M05 slide 31](images/M05/slide-31.png)

**Narration:**

> AgentCore Memory supports fine-grained access control, which enables secure multi-user and multi-session memory management. The key idea is that different memory operations have different IAM actions and different context keys you can use in your policies. For short-term memory, the relevant actions are create-event, delete-event, get-event, and list-events, and the available context keys are the actor ID, for example user A, and the session ID, for example session dash zero zero one. These let you build policies that isolate each user's conversation data. For long-term memory, the relevant actions are retrieve-memory-records, list-memory-records, get-memory-record, and delete-memory-record, and the available context keys are the namespace, such as nm-1, and the strategy ID, such as stid-1. These let you create policies that protect persistent information while allowing appropriate access. By designing IAM policies around these actions and context keys, you get precise control over who can access which memory data.

---

## Slide 32 — Fine-grained access control with actors and namespaces

![M05 slide 32](images/M05/slide-32.png)

**Narration:**

> Let's look at a concrete IAM policy that combines actors and namespaces for fine-grained control. The policy statement here allows a single action, retrieve-memory-records, on a specific memory resource identified by its ARN. The important part is the condition block, which uses a string-equals check on the namespace context key, allowing the action only when the namespace equals summaries slash agent1. Any request targeting a different namespace is denied automatically. You can extend this pattern for different scenarios: create separate policies for different user groups or agent types, or combine multiple conditions, such as pairing an actor ID with a namespace restriction, to build layered controls. The namespace structure helps you organize data logically; for example, summaries slash agent1 for one agent's summaries, and conversations slash user A for a specific user's interactions. You attach these policies to the IAM roles your agents assume, so each agent gets only the memory access it needs, which is the principle of least privilege in action: it protects sensitive data while preserving functionality.

---

## Slide 38 — Module summary

![M05 slide 38](images/M05/slide-38.png)

**Narration:**

> Let's recap this module. You should now be able to implement agentic memory patterns for different use cases, configure AgentCore Memory operations for context-aware development, and optimize memory performance for production workloads. With memory in place, your agents can deliver coherent, personalized experiences that improve with every interaction.

---

## Slide 39 — Questions?

![M05 slide 39](images/M05/slide-39.png)

**Narration:**

> That brings us to the end of this module. Take a moment to reflect on how memory applies to the agent you are building, both the experience it enables and the security it demands. Remember that AWS provides many resources for continued learning, including the AWS documentation, AWS Training and Certification, and AWS Support. If you have questions about the material or how to apply it, now is a great time to ask.

---
