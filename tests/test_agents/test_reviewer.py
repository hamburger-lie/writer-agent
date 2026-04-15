from __future__ import annotations

from unittest.mock import Mock

from writing_agent.agents.reviewer import ReviewerAgent
from writing_agent.config import Settings
from writing_agent.controller.task import (
    PlanResult,
    ResearchFinding,
    ResearchResult,
    ResearchSource,
    ReviewResult,
)


def test_reviewer_returns_typed_review_result() -> None:
    llm_provider = Mock()
    llm_provider.generate_json.return_value = {
        "decision": "fail",
        "summary": "Needs stronger evidence.",
        "issues": [
            {
                "severity": "high",
                "title": "Weak evidence",
                "details": "Claims need source-backed support.",
            }
        ],
        "revision_instructions": ["Add stronger evidence to key sections."],
    }
    agent = ReviewerAgent(
        Settings(DEEPSEEK_API_KEY="test-key"),
        Mock(),
        Mock(),
        llm_provider,
    )

    result = agent.run(
        "# Draft\n\nArticle text.",
        PlanResult(
            topic="AI writing trends",
            audience="content strategists",
            goal="explain the landscape",
            title="AI Writing Trends in 2026",
            outline=["Overview", "Adoption"],
            key_points=["Tools are mainstream"],
            constraints=["Professional tone"],
            research_questions=["What use cases are growing fastest?"],
        ),
        ResearchResult(
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
    )

    assert isinstance(result, ReviewResult)
    assert result.decision == "fail"
