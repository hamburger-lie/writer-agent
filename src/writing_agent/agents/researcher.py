"""Researcher agent implementation."""

from __future__ import annotations

from writing_agent.agents.base import BaseAgent
from writing_agent.controller.task import PlanResult, ResearchFinding, ResearchResult, ResearchSource
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

    def _normalize_summary_payload(self, payload: dict, search_queries, deduped_results) -> dict:
        normalized = dict(payload)

        raw_sources = payload.get("sources", [])
        normalized_sources = []
        if isinstance(raw_sources, list):
            for item in raw_sources:
                if isinstance(item, dict):
                    normalized_sources.append(item)
                    continue
                if isinstance(item, str):
                    match = next((result for result in deduped_results if result.url == item), None)
                    normalized_sources.append(
                        {
                            "title": "" if match is None else match.title,
                            "url": item,
                            "snippet": "" if match is None else match.snippet,
                            "fetched_at": "",
                        }
                    )
        normalized["sources"] = normalized_sources

        raw_findings = payload.get("findings", [])
        normalized_findings = []
        if isinstance(raw_findings, list):
            normalized_findings = raw_findings
        elif isinstance(raw_findings, dict):
            source_url = normalized_sources[0]["url"] if normalized_sources else ""
            for key, value in raw_findings.items():
                if isinstance(value, str):
                    normalized_findings.append(
                        {
                            "claim": key,
                            "evidence": value,
                            "source_url": source_url,
                        }
                    )
                elif isinstance(value, list):
                    for item in value:
                        normalized_findings.append(
                            {
                                "claim": key,
                                "evidence": str(item),
                                "source_url": source_url,
                            }
                        )
        normalized["findings"] = normalized_findings
        normalized["search_queries"] = payload.get("search_queries", search_queries)
        return normalized

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
        research = ResearchResult.model_validate(
            self._normalize_summary_payload(summary_payload, search_queries, deduped_results)
        )

        if len(research.findings) < 1:
            raise RuntimeError("Research summary did not contain any findings.")

        if self.librarian is not None:
            self.librarian.ingest_research(plan, research)

        return research
