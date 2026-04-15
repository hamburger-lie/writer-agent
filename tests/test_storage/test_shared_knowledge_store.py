from __future__ import annotations

from pathlib import Path

from writing_agent.controller.task import SharedFact
from writing_agent.storage.shared_knowledge_store import SharedKnowledgeStore


def test_shared_store_deduplicates_ingested_fact_rows(tmp_path: Path) -> None:
    store = SharedKnowledgeStore(tmp_path / "library.db")
    store.initialize_schema()
    fact = SharedFact(
        topic="AI writing trends",
        title="AI Writing Trends in 2026",
        claim="AI tools are mainstream.",
        evidence="Enterprise adoption is broad.",
        source_url="https://example.com/report",
        source_title="Example Report",
        source_snippet="Broad adoption",
        takeaway="AI is mainstream.",
    )

    store.upsert_fact(fact)
    store.upsert_fact(fact)

    rows = store.list_facts()
    assert len(rows) == 1


def test_shared_store_search_returns_matching_fact(tmp_path: Path) -> None:
    store = SharedKnowledgeStore(tmp_path / "library.db")
    store.initialize_schema()
    store.upsert_fact(
        SharedFact(
            topic="AI writing trends",
            title="AI Writing Trends in 2026",
            claim="AI tools are mainstream.",
            evidence="Enterprise adoption is broad.",
            source_url="https://example.com/report",
            source_title="Example Report",
            source_snippet="Broad adoption",
            takeaway="AI is mainstream.",
        )
    )

    results = store.search(["enterprise", "adoption"], limit=5)

    assert len(results) == 1
    assert results[0].claim == "AI tools are mainstream."
