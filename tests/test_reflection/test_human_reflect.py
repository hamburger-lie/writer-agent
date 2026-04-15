from __future__ import annotations

from pathlib import Path
from unittest.mock import Mock

from writing_agent.reflection.human_reflect import HumanReflectionEngine
from writing_agent.storage.sqlite_store import SQLiteStore


def test_human_reflection_adds_human_rules_and_reflections(tmp_path: Path) -> None:
    store = SQLiteStore(tmp_path / "writer.db")
    store.initialize_schema()
    provider = Mock()
    provider.generate_json.return_value = {
        "summary": "The user prefers tighter claims and fewer filler phrases.",
        "rules": [
            {
                "rule_text": "Prefer tighter, more direct claims over filler transitions.",
                "category": "style",
                "confidence": 0.8,
            }
        ],
    }
    engine = HumanReflectionEngine(llm_provider=provider, sqlite_store=store)

    result = engine.reflect(
        task_id="task-123",
        original_text="# Draft\n\nThis is a very important trend.",
        edited_text="# Draft\n\nThis trend matters.",
    )

    rules = store.list_active_rules()
    reflections = store.list_reflections()

    assert result.rules[0].rule_text == "Prefer tighter, more direct claims over filler transitions."
    assert rules[0]["source"] == "human"
    assert reflections[0]["trigger_context"] == "human_edit"
