from __future__ import annotations

from unittest.mock import Mock

from writing_agent.agents.writer import WriterAgent
from writing_agent.config import Settings
from writing_agent.controller.task import PlanResult, ResearchFinding, ResearchResult, ResearchSource, SharedFact


def test_writer_returns_markdown_from_plan() -> None:
    sqlite_store = Mock()
    vector_store = Mock()
    llm_provider = Mock()
    llm_provider.generate.return_value = "# AI Writing Trends in 2026\n\nIntro paragraph."

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
    research = ResearchResult(
        topic="AI writing trends",
        search_queries=["ai writing trends 2026"],
        sources=[
            ResearchSource(
                title="Example Source",
                url="https://example.com/report",
                snippet="Example snippet",
                fetched_at="2026-04-14T00:00:00+00:00",
            )
        ],
        findings=[
            ResearchFinding(
                claim="AI tools are becoming standard.",
                evidence="Industry adoption is growing quickly.",
                source_url="https://example.com/report",
            )
        ],
        key_takeaways=["AI writing tools are now mainstream."],
        open_questions=["Which teams are moving fastest?"],
    )

    agent = WriterAgent(
        settings=Settings(DEEPSEEK_API_KEY="test-key"),
        sqlite_store=sqlite_store,
        vector_store=vector_store,
        llm_provider=llm_provider,
    )

    result = agent.run(plan, research)

    assert result.startswith("# AI Writing Trends in 2026")


def test_writer_includes_shared_facts_in_prompt_context() -> None:
    sqlite_store = Mock()
    vector_store = Mock()
    llm_provider = Mock()
    llm_provider.generate.return_value = "# AI Writing Trends in 2026\n\nIntro paragraph."
    librarian = Mock()
    librarian.find_relevant_facts.return_value = [
        SharedFact(
            topic="AI writing trends",
            title="AI Writing Trends in 2026",
            claim="AI tools are mainstream.",
            evidence="Industry adoption is growing quickly.",
            source_url="https://example.com/report",
            source_title="Example Source",
            source_snippet="Example snippet",
            takeaway="AI writing tools are now mainstream.",
        )
    ]

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
    research = ResearchResult(
        topic="AI writing trends",
        search_queries=["ai writing trends 2026"],
        sources=[
            ResearchSource(
                title="Example Source",
                url="https://example.com/report",
                snippet="Example snippet",
                fetched_at="2026-04-14T00:00:00+00:00",
            )
        ],
        findings=[
            ResearchFinding(
                claim="AI tools are becoming standard.",
                evidence="Industry adoption is growing quickly.",
                source_url="https://example.com/report",
            )
        ],
        key_takeaways=["AI writing tools are now mainstream."],
        open_questions=["Which teams are moving fastest?"],
    )

    agent = WriterAgent(
        settings=Settings(DEEPSEEK_API_KEY="test-key"),
        sqlite_store=sqlite_store,
        vector_store=vector_store,
        llm_provider=llm_provider,
        librarian=librarian,
    )

    agent.run(plan, research)

    prompt = llm_provider.generate.call_args.kwargs["prompt"]
    assert "Shared knowledge facts" in prompt
    assert "AI tools are mainstream." in prompt
