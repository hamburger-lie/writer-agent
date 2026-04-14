"""Writer agent implementation."""

from __future__ import annotations

from writing_agent.agents.base import BaseAgent
from writing_agent.controller.task import PlanResult
from writing_agent.llm.models import DEEPSEEK_CHAT
from writing_agent.llm.prompts.writer import build_writer_prompt


class WriterAgent(BaseAgent):
    """Generate a Markdown draft from a structured plan."""

    def __init__(self, settings, sqlite_store, vector_store, llm_provider) -> None:
        super().__init__(
            name="writer",
            role="主笔",
            settings=settings,
            sqlite_store=sqlite_store,
            vector_store=vector_store,
            llm_provider=llm_provider,
        )

    def run(self, plan: PlanResult) -> str:
        system_prompt, prompt = build_writer_prompt(plan)
        return self.llm_provider.generate(
            prompt=prompt,
            system_prompt=system_prompt,
            model=DEEPSEEK_CHAT,
        )
