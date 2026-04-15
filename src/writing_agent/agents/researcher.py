"""Researcher agent implementation."""

from __future__ import annotations

from datetime import UTC, datetime

from writing_agent.agents.base import BaseAgent
from writing_agent.controller.task import PlanResult, ResearchResult
from writing_agent.llm.models import DEEPSEEK_CHAT
from writing_agent.llm.prompts.researcher import (
    build_research_query_prompt,
    build_research_summary_prompt,
)


class ResearcherAgent(BaseAgent):
    """Run real search and scraping, then summarize into structured research."""

    def __init__(
        self,
        settings,
        sqlite_store,
        vector_store,
        llm_provider,
        search_client,
        scraper,
        librarian=None,
    ) -> None:
        super().__init__(
            name="researcher",
            role="调研",
            settings=settings,
            sqlite_store=sqlite_store,
            vector_store=vector_store,
            llm_provider=llm_provider,
        )
        self.search_client = search_client
        self.scraper = scraper
        self.librarian = librarian

    def _dedupe_results(self, results):
        seen: set[str] = set()
        deduped = []
        for item in results:
            if item.url in seen:
                continue
            seen.add(item.url)
            deduped.append(item)
        return deduped

    def run(self, plan: PlanResult) -> ResearchResult:
        query_system_prompt, query_prompt = build_research_query_prompt(plan)
        query_payload = self.llm_provider.generate_json(
            prompt=query_prompt,
            system_prompt=query_system_prompt,
            model=DEEPSEEK_CHAT,
        )
        search_queries = query_payload.get("queries", [])
        if not search_queries:
            raise RuntimeError("Researcher generated no search queries.")

        search_results = []
        for query in search_queries:
            search_results.extend(self.search_client.search(query))
        deduped_results = self._dedupe_results(search_results)
        urls = [item.url for item in deduped_results[: self.settings.max_research_urls]]
        if not urls:
            raise RuntimeError("Researcher found no URLs to scrape.")

        scraped_pages = self.scraper.scrape_many(urls)
        successful_pages = [item for item in scraped_pages if item.success and item.markdown.strip()]
        if len(successful_pages) < 2:
            raise RuntimeError("Not enough successful research sources.")

        summary_system_prompt, summary_prompt = build_research_summary_prompt(
            plan=plan,
            search_queries=search_queries,
            search_results=deduped_results,
            scraped_pages=successful_pages,
        )
        summary_payload = self.llm_provider.generate_json(
            prompt=summary_prompt,
            system_prompt=summary_system_prompt,
            model=DEEPSEEK_CHAT,
        )
        research = ResearchResult.model_validate(summary_payload)

        if len(research.findings) < 1:
            raise RuntimeError("Research summary did not contain any findings.")

        if self.librarian is not None:
            self.librarian.ingest_research(plan, research)

        return research
