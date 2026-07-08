"""OGX Memory Demo Agent -- persistent memory via MemoryHub.

Direct-to-vLLM mode: uses standard chat completions with client-side
MCP tool routing. Proves the MemoryHub integration concept works
end-to-end while OGX Responses API tool-call issues are resolved (#316).

MemoryHub is connected as a client-side MCP server. The model calls
register_session and memory tools via vLLM's built-in tool calling.
OpenAIChatServer handles SSE streaming natively.

A /v1/memories endpoint is added for the UI's memory viewer pane.
"""

from __future__ import annotations

import logging
import os

from fipsagents.baseagent import BaseAgent, StepResult, load_config
from memoryhub import MemoryHubClient

log = logging.getLogger(__name__)


class OGXMemoryAgent(BaseAgent):

    async def setup(self) -> None:
        await super().setup()
        # Patch model name: the framework strips 'gemma4/' prefix
        # but OGX registers the model with it. Not needed when going
        # direct to vLLM, but kept for forward compat.
        raw = os.environ.get("OGX_MODEL_NAME", "")
        if raw and hasattr(self, "llm"):
            original = self.llm._base_kwargs
            def patched(**overrides):
                kwargs = original(**overrides)
                kwargs["model"] = raw
                return kwargs
            self.llm._base_kwargs = patched

    def get_tool_schemas(self):
        schemas = super().get_tool_schemas()
        blocked = {"ask_user", "spawn_agent"}
        return [s for s in schemas if s["function"]["name"] not in blocked]

    async def step(self) -> StepResult:
        response = await self.call_model()
        response = await self.run_tool_calls(response)
        return StepResult.done(result=response.content)


if __name__ == "__main__":
    from fipsagents.server import OpenAIChatServer

    config = load_config("agent.yaml")
    server = OpenAIChatServer(
        agent_class=OGXMemoryAgent,
        config_path="agent.yaml",
        title=config.agent.name,
        version=config.agent.version,
    )

    api_key = os.environ.get("MEMORYHUB_API_KEY", "")
    mh_url = os.environ.get("MEMORYHUB_URL", "")

    @server.app.get("/v1/memories")
    async def list_memories(limit: int = 20):
        if not api_key or not mh_url:
            return {"memories": [], "error": "MemoryHub not configured"}
        try:
            async with MemoryHubClient(server_url=mh_url, api_key=api_key) as client:
                result = await client.search(
                    query="preferences decisions context user",
                    max_results=limit,
                    mode="full",
                )
            memories = []
            for m in result.results:
                memories.append({
                    "id": m.id,
                    "content": m.content or m.stub or "",
                    "scope": m.scope or "",
                    "weight": m.weight or 0,
                    "created_at": str(m.created_at) if m.created_at else "",
                    "content_type": m.content_type or "",
                })
            return {"memories": memories, "total": result.total_matching}
        except Exception as e:
            log.warning("Failed to list memories: %s", e)
            return {"memories": [], "error": str(e)}

    server.run(host=config.server.host, port=config.server.port)
