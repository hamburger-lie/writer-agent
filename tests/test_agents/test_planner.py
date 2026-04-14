from __future__ import annotations

from unittest.mock import Mock

from writing_agent.agents.planner import PlannerAgent
from writing_agent.config import Settings
from writing_agent.controller.task import PlanResult


def test_planner_returns_typed_plan_result() -> None:
    sqlite_store = Mock()
    vector_store = Mock()
    llm_provider = Mock()
    llm_provider.generate_json.return_value = {
        "topic": "AI writing trends",
        "audience": "content strategists",
        "goal": "explain the landscape",
        "title": "AI Writing Trends in 2026",
        "outline": ["Overview", "Adoption"],
        "key_points": ["Tools are mainstream"],
        "constraints": ["Professional tone"],
        "research_questions": ["What use cases are growing fastest?"],
    }

    agent = PlannerAgent(
        settings=Settings(DEEPSEEK_API_KEY="test-key"),
        sqlite_store=sqlite_store,
        vector_store=vector_store,
        llm_provider=llm_provider,
    )

    result = agent.run("AI writing trends")

    assert isinstance(result, PlanResult)
    assert result.title == "AI Writing Trends in 2026"
