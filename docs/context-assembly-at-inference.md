# Context Assembly at Inference Time

At inference time, every piece of context an agent has access to -- memories, RAG results, web search, configuration files, tool outputs, conversation history -- collapses into a single JSON payload sent to the LLM. The model doesn't know where any token came from. Provenance only exists if the developer chose to tag it.

This document shows what that assembly looks like concretely, using small examples from real systems. The [agent integration explainer](how-agents-use-memoryhub.md) covers the conceptual "why"; this covers the mechanical "what."

## Sources feeding the context window

Before the LLM sees anything, the harness (Claude Code, LangGraph, CrewAI, a custom Python script) assembles the API request from multiple sources. Here is a representative set for an agent working on an order-processing service.

### CLAUDE.md -- project conventions (loaded every session)

```text
# Project conventions
- Use FastAPI for new Python services
- Use Podman, not Docker; Containerfile, not Dockerfile
- Red Hat UBI base images only
- pytest with 80%+ coverage target
```

### MemoryHub -- experiential context (loaded by SessionStart hook)

```text
<memoryhub-context project="order-service">
- The team decided to use pgvector over Pinecone because PostgreSQL
  was already in the stack (2026-03-15)
- srampal prefers API key auth over OAuth for local development
- Deploy scripts must run in main conversation context, never
  sub-agents -- a sub-agent destroyed the prod database on 2026-05-19
</memoryhub-context>
```

### RAG -- reference documentation (tool call mid-conversation)

```text
<rag_result source="internal-docs/api-reference.md" score="0.92">
POST /api/v2/orders
Content-Type: application/json

Request body:
  customer_id (string, required): The customer UUID
  items (array, required): Line items with sku and quantity
  shipping_method (string): "standard" | "express" | "overnight"

Returns: 201 Created with order_id in response body.
</rag_result>
```

### Web search -- current information (tool call mid-conversation)

```text
<web_search query="FastAPI lifespan event handler 2026">
Result 1: FastAPI Lifespan Events (fastapi.tiangolo.com)
  Use the lifespan parameter on the FastAPI app to define startup and
  shutdown logic. The older @app.on_event("startup") decorator is
  deprecated as of 0.109.
</web_search>
```

### AGENTS.md -- agent role definition (loaded by harness at startup)

```text
# Agent: order-processor
Role: Process incoming customer orders
Tools: database_query, send_email, inventory_check
Constraints: Never modify pricing without human approval
Escalation: Orders over $10,000 require manager review
```

### Conversation history -- what happened so far in this session

```text
User: Can you add a bulk order endpoint that accepts a CSV upload?

Agent: I'll design that. Let me check the existing order creation
endpoint first to match the patterns.

[Tool call: rag_search("order creation endpoint API reference")]
[Tool result: the RAG block shown above]

[Tool call: web_search("FastAPI lifespan event handler 2026")]
[Tool result: the web search block shown above]
```

## How the harness assembles the API request

The harness takes all of the above and builds a single JSON object for the LLM's API. Here is what that looks like, abbreviated but structurally accurate. This is the actual shape of the data that crosses the wire to the model:

```json
{
  "model": "claude-sonnet-4-6",
  "max_tokens": 8096,
  "system": [
    {
      "type": "text",
      "text": "You are a helpful coding assistant.\n\n# Project conventions\n- Use FastAPI for new Python services\n- Use Podman, not Docker; Containerfile, not Dockerfile\n- Red Hat UBI base images only\n- pytest with 80%+ coverage target\n\n# Agent: order-processor\nRole: Process incoming customer orders\nTools: database_query, send_email, inventory_check\nConstraints: Never modify pricing without human approval\nEscalation: Orders over $10,000 require manager review"
    },
    {
      "type": "text",
      "text": "<memoryhub-context project=\"order-service\">\n- The team decided to use pgvector over Pinecone because PostgreSQL was already in the stack (2026-03-15)\n- srampal prefers API key auth over OAuth for local development\n- Deploy scripts must run in main conversation context, never sub-agents\n</memoryhub-context>"
    }
  ],
  "tools": [
    {
      "name": "rag_search",
      "description": "Search internal documentation",
      "input_schema": { "type": "object", "properties": { "query": { "type": "string" } } }
    },
    {
      "name": "memory",
      "description": "Read and write agent memories via MemoryHub",
      "input_schema": { "type": "object", "properties": { "action": { "type": "string" } } }
    },
    {
      "name": "web_search",
      "description": "Search the web for current information",
      "input_schema": { "type": "object", "properties": { "query": { "type": "string" } } }
    }
  ],
  "messages": [
    {
      "role": "user",
      "content": "Can you add a bulk order endpoint that accepts a CSV upload?"
    },
    {
      "role": "assistant",
      "content": [
        { "type": "text", "text": "I'll design that. Let me check the existing order creation endpoint first to match the patterns." },
        { "type": "tool_use", "id": "call_1", "name": "rag_search", "input": { "query": "order creation endpoint API reference" } }
      ]
    },
    {
      "role": "user",
      "content": [
        {
          "type": "tool_result",
          "tool_use_id": "call_1",
          "content": "<rag_result source=\"internal-docs/api-reference.md\" score=\"0.92\">\nPOST /api/v2/orders\nContent-Type: application/json\n\nRequest body:\n  customer_id (string, required)\n  items (array, required)\n  shipping_method (string): \"standard\" | \"express\" | \"overnight\"\n\nReturns: 201 Created with order_id\n</rag_result>"
        }
      ]
    },
    {
      "role": "assistant",
      "content": [
        { "type": "text", "text": "Good, I see the pattern. Let me check how to handle the lifespan for background CSV processing." },
        { "type": "tool_use", "id": "call_2", "name": "web_search", "input": { "query": "FastAPI lifespan event handler 2026" } }
      ]
    },
    {
      "role": "user",
      "content": [
        {
          "type": "tool_result",
          "tool_use_id": "call_2",
          "content": "<web_search query=\"FastAPI lifespan event handler 2026\">\nResult 1: Use the lifespan parameter on the FastAPI app.\nThe older @app.on_event(\"startup\") decorator is deprecated as of 0.109.\n</web_search>"
        }
      ]
    }
  ]
}
```

## What to notice

**Everything is tokens.** The system prompt block contains CLAUDE.md text, AGENTS.md text, and MemoryHub memories, concatenated together. The model sees one continuous system prompt. There is no API field for "this part came from MemoryHub" versus "this part came from CLAUDE.md."

**Tags are a developer convention, not a model feature.** The `<memoryhub-context>`, `<rag_result>`, and `<web_search>` tags are just strings the developer chose to wrap around content. The model can read them and reason about provenance if instructed to, but the tags have no special meaning at the API level. You could rename `<memoryhub-context>` to `<team-knowledge>` and the model would treat it identically.

**Tool results are conversation turns.** When the agent calls a tool, the result comes back as a message in the conversation history. The RAG result and web search result above aren't in the system prompt -- they're in the message array, interleaved with the agent's reasoning. The model processes them in sequence, exactly like user messages.

**The system prompt is the premium real estate.** Content in the system prompt is seen on every turn of the conversation. CLAUDE.md goes here because it applies to every turn. MemoryHub context goes here (via the hook) because it's pre-loaded general context. Tool results go in the message array because they're responses to specific questions at specific points in the conversation.

**You can visualize the assembly as a funnel:**

```
  CLAUDE.md          AGENTS.md         MemoryHub hook
  (static,           (static,          (dynamic,
   every session)     if harness        semantic search
                      loads it)         at session start)
       \                |                /
        \               |               /
         v              v              v
    +------------------------------------+
    |         system prompt block        |  <-- seen on every turn
    +------------------------------------+

    +------------------------------------+
    |    tool definitions (JSON schema)  |  <-- available to call
    +------------------------------------+

    +------------------------------------+
    |        conversation messages       |  <-- grows each turn
    |                                    |
    |  user: "Add a bulk order endpoint" |
    |  assistant: "Let me check..."      |
    |  tool_result: <rag_result>...</>   |  <-- RAG retrieval
    |  assistant: "I see the pattern..." |
    |  tool_result: <web_search>...</>   |  <-- web search
    |  ...                               |
    +------------------------------------+
              |
              v
    +------------------------------------+
    |     single JSON API request        |  <-- this is all the
    |     to the LLM endpoint            |      model ever sees
    +------------------------------------+
```

The model receives one JSON object. It doesn't see "MemoryHub" or "RAG" or "CLAUDE.md" as concepts -- it sees tokens in specific positions (system prompt, tool schemas, conversation turns) and processes them according to the attention pattern. Provenance is invisible unless the developer made it visible by wrapping content in descriptive tags.

## Implications for system design

This assembly model has practical consequences for how you build agent systems:

**Put stable, universal context in the system prompt.** Project conventions, agent role definitions, and pre-loaded memories belong here. They're seen on every turn and benefit from prompt caching (same prefix across turns means the cache hits).

**Put dynamic, query-specific context in tool results.** RAG retrievals, web searches, database lookups, and API calls belong here. They appear at the point in the conversation where they're relevant and don't consume system prompt space on turns where they're not needed.

**Tag content if the agent needs to reason about source.** If the agent should treat MemoryHub memories differently from RAG results (for example, memories can be updated but RAG content is read-only), wrap them in descriptive tags. If source doesn't matter for the agent's behavior, skip the tags and save tokens.

**Every token competes for the same context window.** A 200K context window sounds large until you fill it with a 50-page API reference from RAG, 500 lines of conversation history, and a verbose system prompt. Memory, RAG, and configuration all draw from the same budget. MemoryHub's compact output format (content only, no metadata) is a deliberate response to this constraint -- every token in the context window should earn its place.
