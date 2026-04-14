from __future__ import annotations

from unittest.mock import Mock

from writing_agent.agents.writer import WriterAgent
from writing_agent.config import Settings
from writing_agent.controller.task import PlanResult


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

    agent = WriterAgent(
        settings=Settings(DEEPSEEK_API_KEY="test-key"),
        sqlite_store=sqlite_store,
        vector_store=vector_store,
        llm_provider=llm_provider,
    )

    result = agent.run(plan)

    assert result.startswith("# AI Writing Trends in 2026")
