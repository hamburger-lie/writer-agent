"""Automatic post-task reflection helpers."""

from __future__ import annotations

from writing_agent.controller.task import ReflectionContext, ReflectionResult
from writing_agent.llm.prompts.reflection import build_auto_reflection_prompt
from writing_agent.storage.sqlite_store import SQLiteStore


class AutoReflectionEngine:
    """Generate, persist, and promote lessons from full pipeline runs."""

    def __init__(self, llm_provider, sqlite_store: SQLiteStore, promotion_threshold: int = 3) -> None:
        self.llm_provider = llm_provider
        self.sqlite_store = sqlite_store
        self.promotion_threshold = promotion_threshold

    def reflect(self, context: ReflectionContext) -> ReflectionResult:
        system_prompt, prompt = build_auto_reflection_prompt(context)
        payload = self.llm_provider.generate_json(prompt=prompt, system_prompt=system_prompt)
        result = ReflectionResult.model_validate(payload)

        for lesson in result.lessons:
            reflection_id = self.sqlite_store.record_reflection_observation(
                reflection_text=lesson.reflection_text,
                task_id=context.task_id,
                trigger_context=self._build_trigger_context(context),
            )
            row = self.sqlite_store.get_reflection(reflection_id)
            if row is None:
                continue
            if int(row["times_seen"]) < self.promotion_threshold or int(row["promoted_to_rule"]) == 1:
                continue
            self.sqlite_store.add_rule(
                rule_text=lesson.reflection_text,
                source="auto_reflection",
                confidence=lesson.confidence,
                category=lesson.category,
            )
            self.sqlite_store.mark_reflection_promoted(reflection_id)

        return result

    @staticmethod
    def _build_trigger_context(context: ReflectionContext) -> str:
        if context.error_message:
            return f"{context.status}:{context.current_stage}:{context.error_message}"
        if context.review_decision:
            return f"{context.status}:{context.current_stage}:{context.review_decision}"
        return f"{context.status}:{context.current_stage}"
