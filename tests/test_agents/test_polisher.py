from __future__ import annotations

from unittest.mock import Mock

from writing_agent.agents.polisher import PolisherAgent
from writing_agent.config import Settings
from writing_agent.controller.task import (
    PlanResult,
    ResearchFinding,
    ResearchResult,
    ResearchSource,
    ReviewIssue,
    ReviewResult,
)


def test_polisher_returns_markdown() -> None:
    llm_provider = Mock()
    llm_provider.generate.return_value = "# Final Draft\n\nImproved article."
    agent = PolisherAgent(
        Settings(DEEPSEEK_API_KEY="test-key"),
        Mock(),
        Mock(),
        llm_provider,
    )

    result = agent.run(
        draft="# Draft\n\nOriginal article.",
        plan=PlanResult(
            topic="AI writing trends",
            audience="content strategists",
            goal="explain the landscape",
            title="AI Writing Trends in 2026",
            outline=["Overview", "Adoption"],
            key_points=["Tools are mainstream"],
            constraints=["Professional tone"],
            research_questions=["What use cases are growing fastest?"],
        ),
        research=ResearchResult(
            topic="AI writing trends",
            search_queries=["ai writing trends 2026"],
            sources=[
                ResearchSource(
                    title="Example",
                    url="https://example.com",
                    snippet="Example snippet",
                    fetched_at="2026-04-15T00:00:00+00:00",
                )
            ],
            findings=[
                ResearchFinding(
                    claim="AI tools are mainstream.",
                    evidence="Broad enterprise adoption is reported.",
                    source_url="https://example.com",
                )
            ],
            key_takeaways=["AI tools are mainstream."],
            open_questions=["Which teams are moving fastest?"],
        ),
        review=ReviewResult(
            decision="fail",
            summary="Needs stronger evidence.",
            issues=[
                ReviewIssue(
                    severity="high",
                    title="Weak evidence",
                    details="Claims need source-backed support.",
                )
            ],
            revision_instructions=["Add stronger evidence to key sections."],
        ),
    )

    assert result.startswith("# Final Draft")
