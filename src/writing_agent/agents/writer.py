"""Writer agent implementation."""

from __future__ import annotations

from writing_agent.agents.base import BaseAgent
from writing_agent.controller.task import PlanResult, ResearchResult
from writing_agent.llm.models import DEEPSEEK_CHAT
from writing_agent.llm.prompts.writer import build_writer_prompt


class WriterAgent(BaseAgent):
    """Generate a Markdown draft from a structured plan."""

    def __init__(self, settings, sqlite_store, vector_store, llm_provider, librarian=None) -> None:
        super().__init__(
            name="writer",
            role="主笔",
            settings=settings,
            sqlite_store=sqlite_store,
            vector_store=vector_store,
            llm_provider=llm_provider,
        )
        self.librarian = librarian

    def run(self, plan: PlanResult, research: ResearchResult) -> str:
        shared_facts = []
        if self.librarian is not None:
            shared_facts = self.librarian.find_relevant_facts(
                topic=plan.topic,
                title=plan.title,
                key_points=plan.key_points,
                limit=5,
            )
        system_prompt, prompt = build_writer_prompt(plan, research, shared_facts=shared_facts)
        return self.llm_provider.generate(
            prompt=prompt,
            system_prompt=system_prompt,
            model=DEEPSEEK_CHAT,
        )
