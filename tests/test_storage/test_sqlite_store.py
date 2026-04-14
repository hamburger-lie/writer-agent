from __future__ import annotations

import sqlite3
from pathlib import Path

from writing_agent.storage.sqlite_store import SQLiteStore


def test_initialize_schema_creates_all_tables(tmp_path: Path) -> None:
    store = SQLiteStore(tmp_path / "planner.db")

    store.initialize_schema()

    with sqlite3.connect(tmp_path / "planner.db") as conn:
        tables = {
            row[0]
            for row in conn.execute(
                "SELECT name FROM sqlite_master WHERE type='table' AND name NOT LIKE 'sqlite_%'"
            )
        }

    assert {"rules", "task_history", "reflections", "metadata"} <= tables


def test_metadata_upsert_round_trip(tmp_path: Path) -> None:
    store = SQLiteStore(tmp_path / "planner.db")
    store.initialize_schema()

    store.upsert_metadata("agent_name", "planner")

    assert store.get_metadata("agent_name") == "planner"


def test_add_rule_and_list_active_rules(tmp_path: Path) -> None:
    store = SQLiteStore(tmp_path / "planner.db")
    store.initialize_schema()

    store.add_rule(
        rule_text="Always cite sources.",
        source="human",
        confidence=0.9,
        category="style",
    )

    rows = store.list_active_rules()

    assert len(rows) == 1
    assert rows[0]["rule_text"] == "Always cite sources."
