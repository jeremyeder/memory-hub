# OGX Memory Demo Agent

A demo agent showing persistent cross-session memory via MemoryHub and OGX.
Built on the fipsagents BaseAgent framework with platform mode enabled.

## Architecture

- **Inference**: OGX (LlamaStack) on OpenShift, using on-cluster vLLM
- **Memory**: MemoryHub MCP server, registered as an OGX connector
- **Agent**: fipsagents BaseAgent in platform mode (OGX handles tool routing)

The agent has zero memory-handling code. OGX discovers MemoryHub's MCP tools
and routes tool calls automatically. The system prompt instructs the agent
when to read and write memories.

## Environment Variables

```bash
# Required
OPENAI_API_KEY=not-required    # OpenAI SDK requires non-empty value
MEMORYHUB_API_KEY=mh-dev-...   # MemoryHub API key

# Defaults point at the mcp-rhoai cluster (override for other environments)
OGX_ENDPOINT=http://ogx-ogx.apps.cluster-n7pd5.n7pd5.sandbox5167.opentlc.com
MODEL_ENDPOINT=http://ogx-ogx.apps.cluster-n7pd5.n7pd5.sandbox5167.opentlc.com/v1
MODEL_NAME=vllm/RedHatAI/gpt-oss-20b
```

## Build and Run

```bash
make install
OPENAI_API_KEY=not-required make run-local
```

## Testing the Memory Flow

1. Start the agent, gateway, and UI
2. Tell the agent your preferences: "I always use Podman, not Docker"
3. End the session
4. Start a new session and ask: "Help me containerize a Python app"
5. Verify the agent recalls Podman preference without being told
