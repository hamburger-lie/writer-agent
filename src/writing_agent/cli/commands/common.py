"""Shared helpers for single-stage CLI commands."""

from __future__ import annotations

import json
from pathlib import Path

from writing_agent.controller.task import PlanResult, ResearchResult


def load_or_build_context(input_file: Path) -> tuple[PlanResult, ResearchResult]:
    """Load sibling plan/research artifacts when present, otherwise synthesize minimal context."""

    plan_path = input_file.parent / "plan.json"
    research_path = input_file.parent / "research.json"

    if plan_path.exists():
        plan = PlanResult.model_validate(json.loads(plan_path.read_text(encoding="utf-8")))
    else:
        title = input_file.stem.replace("_", " ").replace("-", " ").strip() or "Draft"
        plan = PlanResult(
            topic=title,
            audience="general readers",
            goal="review and improve the supplied draft",
            title=title,
            outline=["Introduction", "Body", "Conclusion"],
            key_points=[],
            constraints=[],
            research_questions=[],
        )

    if research_path.exists():
        research = ResearchResult.model_validate(json.loads(research_path.read_text(encoding="utf-8")))
    else:
        research = ResearchResult(
            topic=plan.topic,
            search_queries=[],
            sources=[],
            findings=[],
            key_takeaways=[],
            open_questions=[],
        )

    return plan, research
