"""Human edit reflection helpers."""

from __future__ import annotations

from dataclasses import dataclass
from difflib import unified_diff

from pydantic import BaseModel

from writing_agent.llm.prompts.reflection import build_human_reflection_prompt
from writing_agent.storage.sqlite_store import SQLiteStore


class HumanRule(BaseModel):
    """One reusable rule extracted from a human edit."""

    rule_text: str
    category: str
    confidence: float


class HumanReflectionResult(BaseModel):
    """Structured human reflection output."""

    summary: str
    rules: list[HumanRule]


@dataclass(slots=True)
class HumanReflectionEngine:
    """Generate and persist reusable rules from user edits."""

    llm_provider: object
    sqlite_store: SQLiteStore
    default_confidence: float = 0.7

    def reflect(self, *, task_id: str, original_text: str, edited_text: str) -> HumanReflectionResult:
        diff_text = "\n".join(
            unified_diff(
                original_text.splitlines(),
                edited_text.splitlines(),
                fromfile="original",
                tofile="edited",
                lineterm="",
            )
        )
        system_prompt, prompt = build_human_reflection_prompt(
            task_id=task_id,
            original_text=original_text,
            edited_text=edited_text,
            diff_text=diff_text,
        )
        payload = self.llm_provider.generate_json(prompt=prompt, system_prompt=system_prompt)
        result = HumanReflectionResult.model_validate(payload)

        for rule in result.rules:
            confidence = rule.confidence if rule.confidence > 0 else self.default_confidence
            self.sqlite_store.add_rule(
                rule_text=rule.rule_text,
                source="human",
                confidence=confidence,
                category=rule.category,
            )
            self.sqlite_store.add_reflection(
                reflection_text=rule.rule_text,
                task_id=task_id,
                trigger_context="human_edit",
                promoted_to_rule=True,
            )

        return result
