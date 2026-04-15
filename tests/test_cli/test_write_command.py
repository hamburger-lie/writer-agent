from __future__ import annotations

from pathlib import Path

from typer.testing import CliRunner

from writing_agent.cli.app import app
from writing_agent.controller.pipeline import PipelineRunResult
from writing_agent.controller.task import (
    PipelineStage,
    PipelineStatus,
    PipelineTask,
    PlanResult,
    ReviewIssue,
    ReviewResult,
    ResearchFinding,
    ResearchResult,
    ResearchSource,
)


class _FakePipeline:
    def __init__(self, result: PipelineRunResult) -> None:
        self.result = result

    def run(self, topic: str) -> PipelineRunResult:
        return self.result


def test_write_command_shows_paths_and_previews(monkeypatch, tmp_path: Path) -> None:
    runner = CliRunner()
    monkeypatch.chdir(tmp_path)
    monkeypatch.setenv("DEEPSEEK_API_KEY", "test-key")

    task_dir = tmp_path / "data" / "tasks" / "task-123"
    task = PipelineTask(
        task_id="task-123",
        topic="AI writing trends",
        status=PipelineStatus.COMPLETED,
        current_stage=PipelineStage.WRITER,
        created_at=PipelineTask.create("seed", tmp_path).created_at,
        updated_at=PipelineTask.create("seed", tmp_path).updated_at,
        task_dir=task_dir,
        plan_file=task_dir / "plan.json",
        research_file=task_dir / "research.json",
        draft_file=task_dir / "draft.md",
        polished_file=task_dir / "polished.md",
        review_file=task_dir / "review.json",
        final_file=task_dir / "final.md",
    )
    result_payload = PipelineRunResult(
        task=task,
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
        ),
        draft="# AI Writing Trends in 2026\n\nIntro paragraph.\n\n## Overview\n\nBody text.",
        polished="# Final Draft\n\nImproved article.",
        review=ReviewResult(
            decision="pass",
            summary="Ready to publish.",
            issues=[],
            revision_instructions=[],
        ),
        final="# Final Draft\n\nImproved article.",
    )

    monkeypatch.setattr(
        "writing_agent.cli.commands.write.build_write_pipeline",
        lambda settings: _FakePipeline(result_payload),
    )

    result = runner.invoke(app, ["write", "AI writing trends"])

    assert result.exit_code == 0
    assert "task_id=task-123" in result.stdout
    assert "plan.json" in result.stdout
    assert "research.json" in result.stdout
    assert "draft.md" in result.stdout
    assert "polished.md" in result.stdout
    assert "review.json" in result.stdout
    assert "final.md" in result.stdout
    assert "Outline Preview" in result.stdout
    assert "Draft Preview" in result.stdout
