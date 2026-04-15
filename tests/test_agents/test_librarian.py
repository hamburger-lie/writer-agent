from __future__ import annotations

from pathlib import Path

from writing_agent.agents.librarian import LibrarianAgent
from writing_agent.controller.task import PlanResult, ResearchFinding, ResearchResult, ResearchSource
from writing_agent.storage.shared_knowledge_store import SharedKnowledgeStore


def _build_plan() -> PlanResult:
    return PlanResult(
        topic="AI writing trends",
        audience="content strategists",
        goal="explain the landscape",
        title="AI Writing Trends in 2026",
        outline=["Overview", "Adoption"],
        key_points=["Enterprise adoption"],
        constraints=["Professional tone"],
        research_questions=["What use cases are growing fastest?"],
    )


def _build_research() -> ResearchResult:
    return ResearchResult(
        topic="AI writing trends",
        search_queries=["ai writing trends 2026"],
        sources=[
            ResearchSource(
                title="Example Report",
                url="https://example.com/report",
                snippet="Broad adoption",
                fetched_at="2026-04-14T00:00:00+00:00",
            )
        ],
        findings=[
            ResearchFinding(
                claim="AI tools are mainstream.",
                evidence="Enterprise adoption is broad.",
                source_url="https://example.com/report",
            )
        ],
        key_takeaways=["AI is mainstream."],
        open_questions=["Which teams are moving fastest?"],
    )


def test_librarian_ingests_findings_into_shared_store(tmp_path: Path) -> None:
    store = SharedKnowledgeStore(tmp_path / "library.db")
    store.initialize_schema()
    librarian = LibrarianAgent(shared_store=store)

    librarian.ingest_research(_build_plan(), _build_research())

    facts = store.list_facts()
    assert len(facts) == 1
    assert facts[0].source_url == "https://example.com/report"


def test_librarian_finds_relevant_facts(tmp_path: Path) -> None:
    store = SharedKnowledgeStore(tmp_path / "library.db")
    store.initialize_schema()
    librarian = LibrarianAgent(shared_store=store)
    librarian.ingest_research(_build_plan(), _build_research())

    facts = librarian.find_relevant_facts(
        topic="AI writing trends",
        title="AI Writing Trends in 2026",
        key_points=["enterprise adoption"],
        limit=5,
    )

    assert len(facts) == 1
