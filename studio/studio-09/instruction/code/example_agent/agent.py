"""Install the small setup-check agent inside Harbor's Docker sandbox."""

import json
import shlex
from pathlib import Path

from harbor.agents.installed.base import BaseInstalledAgent, with_prompt_template
from harbor.environments.base import BaseEnvironment
from harbor.models.agent.context import AgentContext


class ExampleAgent(BaseInstalledAgent):
    @staticmethod
    def name() -> str:
        return "setup-check-research"

    async def install(self, environment: BaseEnvironment) -> None:
        await environment.upload_file(Path(__file__).with_name("research.py"), "/installed-agent/research.py")
        # The task image already has openai installed for the verifier.
        await self.exec_as_agent(environment, command="python -c 'import openai'")

    @with_prompt_template
    async def run(
        self, instruction: str, environment: BaseEnvironment, context: AgentContext,
    ) -> None:
        model = (self.model_name or "gpt-5.6-luna").removeprefix("openai/")
        await self.exec_as_agent(
            environment,
            command=f"python /installed-agent/research.py --model {shlex.quote(model)} --question {shlex.quote(instruction)}",
            cwd="/app",
        )
        usage_path = self.logs_dir / "usage.json"
        await environment.download_file("/app/usage.json", usage_path)
        usage = json.loads(usage_path.read_text())["openai"]
        context.n_input_tokens = usage["input_tokens"]
        context.n_cache_tokens = usage.get("input_tokens_details", {}).get("cached_tokens", 0)
        context.n_output_tokens = usage["output_tokens"]
