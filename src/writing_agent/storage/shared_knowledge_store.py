"""Shared fact storage for cross-run knowledge reuse."""

from __future__ import annotations

import hashlib
import sqlite3
from datetime import UTC, datetime
from pathlib import Path

from writing_agent.controller.task import SharedFact


CREATE_SHARED_FACTS_TABLE = """
CREATE TABLE IF NOT EXISTS shared_facts (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    topic TEXT NOT NULL,
    title TEXT NOT NULL,
    claim TEXT NOT NULL,
    evidence TEXT NOT NULL,
    source_url TEXT NOT NULL,
    source_title TEXT NOT NULL,
    source_snippet TEXT NOT NULL,
    takeaway TEXT NOT NULL,
    content_hash TEXT NOT NULL UNIQUE,
    created_at TEXT NOT NULL,
    updated_at TEXT NOT NULL
)
"""


class SharedKnowledgeStore:
    """SQLite-backed shared fact library."""

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
            conn.execute(CREATE_SHARED_FACTS_TABLE)
            conn.commit()

    def upsert_fact(self, fact: SharedFact) -> None:
        now = datetime.now(UTC).isoformat()
        content_hash = self._build_hash(fact)
        with self._connect() as conn:
            conn.execute(
                """
                INSERT INTO shared_facts(
                    topic,
                    title,
                    claim,
                    evidence,
                    source_url,
                    source_title,
                    source_snippet,
                    takeaway,
                    content_hash,
                    created_at,
                    updated_at
                )
                VALUES(?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                ON CONFLICT(content_hash) DO UPDATE SET
                    topic = excluded.topic,
                    title = excluded.title,
                    claim = excluded.claim,
                    evidence = excluded.evidence,
                    source_url = excluded.source_url,
                    source_title = excluded.source_title,
                    source_snippet = excluded.source_snippet,
                    takeaway = excluded.takeaway,
                    updated_at = excluded.updated_at
                """,
                (
                    fact.topic,
                    fact.title,
                    fact.claim,
                    fact.evidence,
                    fact.source_url,
                    fact.source_title,
                    fact.source_snippet,
                    fact.takeaway,
                    content_hash,
                    now,
                    now,
                ),
            )
            conn.commit()

    def list_facts(self) -> list[SharedFact]:
        with self._connect() as conn:
            rows = conn.execute(
                """
                SELECT topic, title, claim, evidence, source_url, source_title, source_snippet, takeaway
                FROM shared_facts
                ORDER BY updated_at DESC
                """
            ).fetchall()
        return [SharedFact.model_validate(dict(row)) for row in rows]

    def search(self, terms: list[str], limit: int = 5) -> list[SharedFact]:
        cleaned_terms = [term.strip().lower() for term in terms if term and term.strip()]
        if not cleaned_terms:
            return []

        conditions = []
        params: list[str | int] = []
        for term in cleaned_terms:
            like = f"%{term}%"
            conditions.append(
                "(lower(topic) LIKE ? OR lower(title) LIKE ? OR lower(claim) LIKE ? "
                "OR lower(evidence) LIKE ? OR lower(source_title) LIKE ? OR lower(takeaway) LIKE ?)"
            )
            params.extend([like, like, like, like, like, like])
        params.append(limit)

        query = f"""
            SELECT topic, title, claim, evidence, source_url, source_title, source_snippet, takeaway
            FROM shared_facts
            WHERE {" OR ".join(conditions)}
            ORDER BY updated_at DESC
            LIMIT ?
        """
        with self._connect() as conn:
            rows = conn.execute(query, tuple(params)).fetchall()
        return [SharedFact.model_validate(dict(row)) for row in rows]

    @staticmethod
    def _build_hash(fact: SharedFact) -> str:
        normalized = "||".join(
            [
                fact.claim.strip().lower(),
                fact.evidence.strip().lower(),
                fact.source_url.strip().lower(),
            ]
        )
        return hashlib.sha256(normalized.encode("utf-8")).hexdigest()
