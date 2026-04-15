from __future__ import annotations

import json
from pathlib import Path

from typer.testing import CliRunner

from writing_agent.cli.app import app
from writing_agent.controller.task import ResearchFinding, ResearchResult, ResearchSource


class _FakeResearchAgent:
    def __init__(self, result: ResearchResult) -> None:
        self.result = result

    def run(self, plan) -> ResearchResult:
        return self.result


def test_research_command_writes_research_json(monkeypatch, tmp_path: Path) -> None:
    runner = CliRunner()
    monkeypatch.chdir(tmp_path)
    monkeypatch.setenv("DEEPSEEK_API_KEY", "test-key")
    fake_result = ResearchResult(
        topic="AI writing trends",
        search_queries=["ai writing trends 2026"],
        sources=[
            ResearchSource(
                title="Example",
                url="https://example.com",
                snippet="Example snippet",
                fetched_at="2026-04-14T00:00:00+00:00",
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
    )
    monkeypatch.setattr(
        "writing_agent.cli.commands.research.build_research_agent",
        lambda settings: _FakeResearchAgent(fake_result),
    )

    output_path = tmp_path / "research.json"
    result = runner.invoke(app, ["research", "AI writing trends", "--output", str(output_path)])

    assert result.exit_code == 0
    assert output_path.exists()
    assert json.loads(output_path.read_text(encoding="utf-8"))["topic"] == "AI writing trends"

