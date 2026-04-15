"""Planner agent implementation."""

from __future__ import annotations

from writing_agent.agents.base import BaseAgent
from writing_agent.controller.task import PlanResult
from writing_agent.llm.models import DEEPSEEK_REASONER
from writing_agent.llm.prompts.planner import build_planner_prompt


class PlannerAgent(BaseAgent):
    """Generate a structured article plan from a topic."""

    def __init__(self, settings, sqlite_store, vector_store, llm_provider) -> None:
        super().__init__(
            name="planner",
            role="策划",
            settings=settings,
            sqlite_store=sqlite_store,
            vector_store=vector_store,
            llm_provider=llm_provider,
        )

    def run(self, topic: str) -> PlanResult:
        system_prompt, prompt = build_planner_prompt(topic)
        payload = self.llm_provider.generate_json(
            prompt=prompt,
            system_prompt=system_prompt,
            model=DEEPSEEK_REASONER,
        )
        normalized_payload = dict(payload)
        if isinstance(normalized_payload.get("constraints"), str):
            normalized_payload["constraints"] = [normalized_payload["constraints"]]
        return PlanResult.model_validate(normalized_payload)
