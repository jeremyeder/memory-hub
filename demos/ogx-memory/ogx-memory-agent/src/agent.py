"""OGX Memory Demo Agent -- persistent memory via MemoryHub.

Uses platform mode: OGX handles MCP tool routing (MemoryHub) and the
inference loop server-side. The agent makes a single call_model_responses()
per turn.
"""

from __future__ import annotations

import os

from fipsagents.baseagent import BaseAgent, StepResult


class OGXMemoryAgent(BaseAgent):
    """Single-turn agent with OGX platform mode and MemoryHub memory."""

    async def setup(self) -> None:
        await super().setup()
        api_key = os.environ.get("MEMORYHUB_API_KEY", "")
        if api_key:
            self.add_message(
                "system",
                f"MemoryHub API key for register_session: {api_key}",
            )

    async def step(self) -> StepResult:
        user_input = self.messages[-1]["content"] if self.messages else ""
        response = await self.call_model_responses(input=user_input)
        return StepResult.done(result=response.content)


if __name__ == "__main__":
    from fipsagents.baseagent import load_config
    from fipsagents.server import OpenAIChatServer

    config = load_config("agent.yaml")
    server = OpenAIChatServer(
        agent_class=OGXMemoryAgent,
        config_path="agent.yaml",
        title=config.agent.name,
        version=config.agent.version,
    )
    server.run(host=config.server.host, port=config.server.port)
