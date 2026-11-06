"""TODO: connect your Studio 06 system. Harbor 0.25.0 installed-agent API."""

import shlex
from pathlib import Path

from harbor.agents.installed.base import BaseInstalledAgent, with_prompt_template
from harbor.environments.base import BaseEnvironment
from harbor.models.agent.context import AgentContext


class TeamAgent(BaseInstalledAgent):
    @staticmethod
    def name() -> str:
        return "studio-06-team"

    async def install(self, environment: BaseEnvironment) -> None:
        # TODO: upload ONLY your system's source files, not question keys,
        # submission evidence, .env files, or local credentials. For example:
        # await environment.upload_dir(Path(__file__).parent / "system", "/app/system")
        # await self.exec_as_agent(environment,
        #     command="uv pip install --system -r /app/system/requirements.txt")
        raise NotImplementedError("Install your Studio 06 system in this sandbox")

    @with_prompt_template
    async def run(
        self, instruction: str, environment: BaseEnvironment, context: AgentContext,
    ) -> None:
        # TODO: replace this CLI with your system's entry point. The CLI must
        # write /app/answer.md and may write /app/trace.jsonl. self.model_name
        # is the -m model. --agent-env keys reach this process through Harbor;
        # never interpolate keys into the command, Dockerfile, or a config file.
        # Change this command to match the arguments YOUR entry point accepts.
        command = (
            "python /app/system/run.py"
            f" --question {shlex.quote(instruction)}"
            f" --model {shlex.quote(self.model_name or '')}"
            " --output /app/answer.md"
        )
        await self.exec_as_agent(environment, command=command, cwd="/app")
