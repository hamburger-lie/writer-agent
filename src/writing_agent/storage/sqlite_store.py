"""Per-agent SQLite operations for rules, history, reflections, and metadata."""

from __future__ import annotations

import json
import sqlite3
from datetime import UTC, datetime
from pathlib import Path

from writing_agent.storage import schema


class SQLiteStore:
    """Thin wrapper around an agent-specific SQLite database."""

    def __init__(self, db_path: Path) -> None:
        self.db_path = db_path

    def _connect(self) -> sqlite3.Connection:
        self.db_path.parent.mkdir(parents=True, exist_ok=True)
        conn = sqlite3.connect(self.db_path)
        conn.row_factory = sqlite3.Row
        conn.execute("PRAGMA journal_mode=WAL;")
        return conn

    def initialize_schema(self) -> None:
        with self._connect() as conn:
            conn.execute(schema.CREATE_RULES_TABLE)
            conn.execute(schema.CREATE_TASK_HISTORY_TABLE)
            conn.execute(schema.CREATE_REFLECTIONS_TABLE)
            conn.execute(schema.CREATE_METADATA_TABLE)
            conn.commit()

    def upsert_metadata(self, key: str, value: str) -> None:
        now = datetime.now(UTC).isoformat()
        with self._connect() as conn:
            conn.execute(
                """
                INSERT INTO metadata(key, value, updated_at)
                VALUES(?, ?, ?)
                ON CONFLICT(key) DO UPDATE SET
                    value = excluded.value,
                    updated_at = excluded.updated_at
                """,
                (key, value, now),
            )
            conn.commit()

    def get_metadata(self, key: str) -> str | None:
        with self._connect() as conn:
            row = conn.execute("SELECT value FROM metadata WHERE key = ?", (key,)).fetchone()
        return None if row is None else str(row["value"])

    def list_active_rules(self) -> list[sqlite3.Row]:
        with self._connect() as conn:
            return list(
                conn.execute("SELECT * FROM rules WHERE is_active = 1 ORDER BY created_at DESC").fetchall()
            )

    def add_rule(self, rule_text: str, source: str, confidence: float, category: str | None) -> int:
        now = datetime.now(UTC).isoformat()
        with self._connect() as conn:
            cursor = conn.execute(
                """
                INSERT INTO rules(rule_text, source, confidence, category, created_at, updated_at, is_active)
                VALUES(?, ?, ?, ?, ?, ?, 1)
                """,
                (rule_text, source, confidence, category, now, now),
            )
            conn.commit()
        return int(cursor.lastrowid)

    def add_task_history(
        self,
        task_id: str,
        task_type: str,
        status: str,
        input_summary: str | None = None,
        output_summary: str | None = None,
        duration_ms: int | None = None,
        token_usage: dict[str, int] | None = None,
    ) -> int:
        with self._connect() as conn:
            cursor = conn.execute(
                """
                INSERT INTO task_history(
                    task_id,
                    task_type,
                    input_summary,
                    output_summary,
                    status,
                    duration_ms,
                    token_usage_json,
                    created_at
                )
                VALUES(?, ?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    task_id,
                    task_type,
                    input_summary,
                    output_summary,
                    status,
                    duration_ms,
                    json.dumps(token_usage or {}),
                    datetime.now(UTC).isoformat(),
                ),
            )
            conn.commit()
        return int(cursor.lastrowid)

    def add_reflection(
        self,
        reflection_text: str,
        task_id: str | None = None,
        trigger_context: str | None = None,
        times_seen: int = 1,
        promoted_to_rule: bool = False,
    ) -> int:
        with self._connect() as conn:
            cursor = conn.execute(
                """
                INSERT INTO reflections(
                    task_id,
                    reflection_text,
                    trigger_context,
                    times_seen,
                    promoted_to_rule,
                    created_at
                )
                VALUES(?, ?, ?, ?, ?, ?)
                """,
                (
                    task_id,
                    reflection_text,
                    trigger_context,
                    times_seen,
                    int(promoted_to_rule),
                    datetime.now(UTC).isoformat(),
                ),
            )
            conn.commit()
        return int(cursor.lastrowid)
