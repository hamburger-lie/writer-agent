from __future__ import annotations

from pathlib import Path
from unittest.mock import Mock

from writing_agent.controller.task import ReflectionContext
from writing_agent.reflection.auto_reflect import AutoReflectionEngine
from writing_agent.storage.sqlite_store import SQLiteStore


def test_auto_reflection_persists_lessons_and_promotes_repeated_rule(tmp_path: Path) -> None:
    store = SQLiteStore(tmp_path / "reviewer.db")
    store.initialize_schema()
    provider = Mock()
    provider.generate_json.return_value = {
        "summary": "Review loop exposed a recurring evidence gap.",
        "lessons": [
            {
                "reflection_text": "Strengthen evidence support before review.",
                "category": "evidence",
                "confidence": 0.9,
            }
        ],
    }
    engine = AutoReflectionEngine(llm_provider=provider, sqlite_store=store, promotion_threshold=3)
    context = ReflectionContext(
        task_id="task-1",
        topic="AI writing trends",
        status="completed",
        current_stage="reviewer",
        plan_title="AI Writing Trends in 2026",
        review_decision="fail",
        review_summary="Evidence is thin.",
        error_message=None,
    )

    engine.reflect(context)
    engine.reflect(context.model_copy(update={"task_id": "task-2"}))
    result = engine.reflect(context.model_copy(update={"task_id": "task-3"}))

    rows = store.list_reflections()
    rules = store.list_active_rules()

    assert result.lessons[0].reflection_text == "Strengthen evidence support before review."
    assert rows[0]["times_seen"] == 3
    assert rows[0]["promoted_to_rule"] == 1
    assert rules[0]["rule_text"] == "Strengthen evidence support before review."
