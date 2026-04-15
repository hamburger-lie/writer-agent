"""Shared fact librarian service."""

from __future__ import annotations

from writing_agent.controller.task import PlanResult, ResearchResult, SharedFact
from writing_agent.storage.shared_knowledge_store import SharedKnowledgeStore


class LibrarianAgent:
    """Manage ingestion and retrieval for the shared fact library."""

    def __init__(self, shared_store: SharedKnowledgeStore) -> None:
        self.shared_store = shared_store

    def ingest_research(self, plan: PlanResult, research: ResearchResult) -> None:
        sources_by_url = {source.url: source for source in research.sources}

        for index, finding in enumerate(research.findings):
            source = sources_by_url.get(finding.source_url)
            if source is None:
                continue
            takeaway = research.key_takeaways[min(index, len(research.key_takeaways) - 1)] if research.key_takeaways else ""
            self.shared_store.upsert_fact(
                SharedFact(
                    topic=research.topic,
                    title=plan.title,
                    claim=finding.claim,
                    evidence=finding.evidence,
                    source_url=finding.source_url,
                    source_title=source.title,
                    source_snippet=source.snippet,
                    takeaway=takeaway,
                )
            )

    def find_relevant_facts(
        self,
        topic: str,
        title: str,
        key_points: list[str],
        limit: int = 5,
    ) -> list[SharedFact]:
        search_terms = [topic, title, *key_points]
        return self.shared_store.search(search_terms, limit=limit)
