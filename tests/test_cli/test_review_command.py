from __future__ import annotations

from pathlib import Path

from typer.testing import CliRunner

from writing_agent.cli.app import app
from writing_agent.controller.task import ReviewResult


class _FakeReviewer:
    def __init__(self, review: ReviewResult) -> None:
        self.review = review

    def run(self, draft, plan, research) -> ReviewResult:
        return self.review


def test_review_command_prints_decision(monkeypatch, tmp_path: Path) -> None:
    runner = CliRunner()
    monkeypatch.chdir(tmp_path)
    monkeypatch.setenv("DEEPSEEK_API_KEY", "test-key")
    draft_path = tmp_path / "draft.md"
    draft_path.write_text("# Draft\n\nContent", encoding="utf-8")
    monkeypatch.setattr(
        "writing_agent.cli.commands.review.build_reviewer_agent",
        lambda settings: _FakeReviewer(
            ReviewResult(
                decision="pass",
                summary="Ready to publish.",
                issues=[],
                revision_instructions=[],
            )
        ),
    )

    result = runner.invoke(app, ["review", str(draft_path)])

    assert result.exit_code == 0
    assert "decision=pass" in result.stdout
    assert "Ready to publish." in result.stdout

