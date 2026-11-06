"""Deliberately wrong answer for the verifier's negative check. No API call."""

from harbor.agents.installed.base import BaseInstalledAgent
from harbor.environments.base import BaseEnvironment
from harbor.models.agent.context import AgentContext


class WrongAnswerAgent(BaseInstalledAgent):
    @staticmethod
    def name() -> str:
        return "deliberately-wrong"

    async def install(self, environment: BaseEnvironment) -> None:
        pass

    async def run(
        self, instruction: str, environment: BaseEnvironment, context: AgentContext,
    ) -> None:
        await self.exec_as_agent(
            environment,
            command="printf '%s\\n' 'I do not know the answer. This is the negative check.' > /app/answer.md",
            cwd="/app",
        )
