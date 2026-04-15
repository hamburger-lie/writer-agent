"""Reviewer agent implementation."""

from __future__ import annotations

from writing_agent.agents.base import BaseAgent
from writing_agent.controller.task import PlanResult, ResearchResult, ReviewResult
from writing_agent.llm.models import DEEPSEEK_REASONER
from writing_agent.llm.prompts.reviewer import build_reviewer_prompt


class ReviewerAgent(BaseAgent):
    """Evaluate whether the current draft is ready to be accepted."""

    def __init__(self, settings, sqlite_store, vector_store, llm_provider) -> None:
        super().__init__(
            name="reviewer",
            role="审核",
            settings=settings,
            sqlite_store=sqlite_store,
            vector_store=vector_store,
            llm_provider=llm_provider,
        )

    def run(self, draft: str, plan: PlanResult, research: ResearchResult) -> ReviewResult:
        system_prompt, prompt = build_reviewer_prompt(
            draft=draft,
            plan=plan,
            research=research,
        )
        payload = self.llm_provider.generate_json(
            prompt=prompt,
            system_prompt=system_prompt,
            model=DEEPSEEK_REASONER,
        )
        return ReviewResult.model_validate(payload)
