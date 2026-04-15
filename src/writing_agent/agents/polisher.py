"""Polisher agent implementation."""

from __future__ import annotations

from writing_agent.agents.base import BaseAgent
from writing_agent.controller.task import PlanResult, ResearchResult, ReviewResult
from writing_agent.llm.models import DEEPSEEK_CHAT
from writing_agent.llm.prompts.polisher import build_polisher_prompt


class PolisherAgent(BaseAgent):
    """Refine draft quality and apply reviewer feedback when needed."""

    def __init__(self, settings, sqlite_store, vector_store, llm_provider) -> None:
        super().__init__(
            name="polisher",
            role="润色",
            settings=settings,
            sqlite_store=sqlite_store,
            vector_store=vector_store,
            llm_provider=llm_provider,
        )

    def run(
        self,
        draft: str,
        plan: PlanResult,
        research: ResearchResult,
        review: ReviewResult | None,
    ) -> str:
        system_prompt, prompt = build_polisher_prompt(
            draft=draft,
            plan=plan,
            research=research,
            review=review,
        )
        return self.llm_provider.generate(
            prompt=prompt,
            system_prompt=system_prompt,
            model=DEEPSEEK_CHAT,
        )
