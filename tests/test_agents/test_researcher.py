from __future__ import annotations

from unittest.mock import Mock

from writing_agent.agents.researcher import ResearcherAgent
from writing_agent.config import Settings
from writing_agent.controller.task import PlanResult, ResearchResult
from writing_agent.tools.web_search import SearchResult
from writing_agent.tools.web_scraper import ScrapeResult


def test_researcher_returns_typed_research_result() -> None:
    llm_provider = Mock()
    llm_provider.generate_json.side_effect = [
        {"queries": ["ai writing trends 2026", "enterprise ai content tools"]},
        {
            "topic": "AI writing trends",
            "search_queries": ["ai writing trends 2026"],
            "sources": [
                {
                    "title": "Example",
                    "url": "https://example.com",
                    "snippet": "Example snippet",
                    "fetched_at": "2026-04-14T00:00:00+00:00",
                }
            ],
            "findings": [
                {
                    "claim": "AI writing tools are mainstream.",
                    "evidence": "The article cites broad enterprise adoption.",
                    "source_url": "https://example.com",
                }
            ],
            "key_takeaways": ["AI tools are mainstream."],
            "open_questions": ["Which teams are adopting fastest?"],
        },
    ]
    search_client = Mock()
    search_client.search.side_effect = [
        [SearchResult(title="Example", url="https://example.com", snippet="Example snippet")],
        [SearchResult(title="Example 2", url="https://example.org", snippet="Example snippet 2")],
    ]
    scraper = Mock()
    scraper.scrape_many.return_value = [
        ScrapeResult(
            url="https://example.com",
            title="Example",
            markdown="# Example",
            success=True,
            error=None,
        ),
        ScrapeResult(
            url="https://example.org",
            title="Example 2",
            markdown="# Example 2",
            success=True,
            error=None,
        ),
    ]

    agent = ResearcherAgent(
        settings=Settings(DEEPSEEK_API_KEY="test-key", SEARCH_ENGINE="serper", SEARCH_API_KEY="search-key"),
        sqlite_store=Mock(),
        vector_store=Mock(),
        llm_provider=llm_provider,
        search_client=search_client,
        scraper=scraper,
    )

    result = agent.run(
        PlanResult(
            topic="AI writing trends",
            audience="content strategists",
            goal="explain the landscape",
            title="AI Writing Trends in 2026",
            outline=["Overview", "Adoption"],
            key_points=["Tools are mainstream"],
            constraints=["Professional tone"],
            research_questions=["What use cases are growing fastest?"],
        )
    )

    assert isinstance(result, ResearchResult)
    assert result.findings[0].claim == "AI writing tools are mainstream."


def test_researcher_ingests_shared_facts_after_success() -> None:
    llm_provider = Mock()
    llm_provider.generate_json.side_effect = [
        {"queries": ["ai writing trends 2026", "enterprise ai content tools"]},
        {
            "topic": "AI writing trends",
            "search_queries": ["ai writing trends 2026"],
            "sources": [
                {
                    "title": "Example",
                    "url": "https://example.com",
                    "snippet": "Example snippet",
                    "fetched_at": "2026-04-14T00:00:00+00:00",
                }
            ],
            "findings": [
                {
                    "claim": "AI writing tools are mainstream.",
                    "evidence": "The article cites broad enterprise adoption.",
                    "source_url": "https://example.com",
                }
            ],
            "key_takeaways": ["AI tools are mainstream."],
            "open_questions": ["Which teams are adopting fastest?"],
        },
    ]
    search_client = Mock()
    search_client.search.side_effect = [
        [SearchResult(title="Example", url="https://example.com", snippet="Example snippet")],
        [SearchResult(title="Example 2", url="https://example.org", snippet="Example snippet 2")],
    ]
    scraper = Mock()
    scraper.scrape_many.return_value = [
        ScrapeResult(
            url="https://example.com",
            title="Example",
            markdown="# Example",
            success=True,
            error=None,
        ),
        ScrapeResult(
            url="https://example.org",
            title="Example 2",
            markdown="# Example 2",
            success=True,
            error=None,
        ),
    ]
    librarian = Mock()

    agent = ResearcherAgent(
        settings=Settings(DEEPSEEK_API_KEY="test-key", SEARCH_ENGINE="serper", SEARCH_API_KEY="search-key"),
        sqlite_store=Mock(),
        vector_store=Mock(),
        llm_provider=llm_provider,
        search_client=search_client,
        scraper=scraper,
        librarian=librarian,
    )

    plan = PlanResult(
        topic="AI writing trends",
        audience="content strategists",
        goal="explain the landscape",
        title="AI Writing Trends in 2026",
        outline=["Overview", "Adoption"],
        key_points=["Tools are mainstream"],
        constraints=["Professional tone"],
        research_questions=["What use cases are growing fastest?"],
    )

    agent.run(plan)

    librarian.ingest_research.assert_called_once()


def test_researcher_normalizes_llm_summary_payload_shapes() -> None:
    llm_provider = Mock()
    llm_provider.generate_json.side_effect = [
        {"queries": ["ai writing trends 2026"]},
        {
            "topic": "AI writing trends",
            "search_queries": ["ai writing trends 2026"],
            "sources": [
                "https://example.com",
            ],
            "findings": {
                "overall_trend": "AI tools are mainstream.",
                "operational_impact": [
                    "Teams use AI to speed up content production.",
                ],
            },
            "key_takeaways": ["AI tools are mainstream."],
            "open_questions": ["Which teams are adopting fastest?"],
        },
    ]
    search_client = Mock()
    search_client.search.return_value = [
        SearchResult(title="Example", url="https://example.com", snippet="Example snippet"),
        SearchResult(title="Example 2", url="https://example.org", snippet="Example snippet 2"),
    ]
    scraper = Mock()
    scraper.scrape_many.return_value = [
        ScrapeResult(
            url="https://example.com",
            title="Example",
            markdown="# Example",
            success=True,
            error=None,
        ),
        ScrapeResult(
            url="https://example.org",
            title="Example 2",
            markdown="# Example 2",
            success=True,
            error=None,
        ),
    ]

    agent = ResearcherAgent(
        settings=Settings(DEEPSEEK_API_KEY="test-key", SEARCH_ENGINE="serper", SEARCH_API_KEY="search-key"),
        sqlite_store=Mock(),
        vector_store=Mock(),
        llm_provider=llm_provider,
        search_client=search_client,
        scraper=scraper,
    )

    result = agent.run(
        PlanResult(
            topic="AI writing trends",
            audience="content strategists",
            goal="explain the landscape",
            title="AI Writing Trends in 2026",
            outline=["Overview", "Adoption"],
            key_points=["Tools are mainstream"],
            constraints=["Professional tone"],
            research_questions=["What use cases are growing fastest?"],
        )
    )

    assert result.sources[0].url == "https://example.com"
    assert result.findings[0].claim == "overall_trend"
