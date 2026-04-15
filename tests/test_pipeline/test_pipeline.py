from __future__ import annotations

import json
from pathlib import Path
from unittest.mock import Mock

import pytest

from writing_agent.config import Settings
from writing_agent.controller.pipeline import WritingPipeline
from writing_agent.controller.task import (
    PlanResult,
    PipelineStatus,
    ResearchFinding,
    ResearchResult,
    ResearchSource,
    ReviewIssue,
    ReviewResult,
)


def test_pipeline_writes_plan_and_draft(tmp_path: Path) -> None:
    settings = Settings(DEEPSEEK_API_KEY="test-key", DATA_DIR=str(tmp_path / "data"))
    planner = Mock()
    planner.run.return_value = PlanResult(
        topic="AI writing trends",
        audience="content strategists",
        goal="explain the landscape",
        title="AI Writing Trends in 2026",
        outline=["Overview", "Adoption"],
        key_points=["Tools are mainstream"],
        constraints=["Professional tone"],
        research_questions=["What use cases are growing fastest?"],
    )
    researcher = Mock()
    researcher.run.return_value = ResearchResult(
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
    polisher = Mock()
    polisher.run.return_value = "# Polished Draft\n\nImproved article."
    reviewer = Mock()
    reviewer.run.return_value = ReviewResult(
        decision="pass",
        summary="Ready to publish.",
        issues=[],
        revision_instructions=[],
    )
    writer = Mock()
    writer.run.return_value = "# AI Writing Trends in 2026\n\nIntro paragraph."

    pipeline = WritingPipeline(
        settings=settings,
        planner=planner,
        researcher=researcher,
        writer=writer,
        polisher=polisher,
        reviewer=reviewer,
        auto_reflector=Mock(),
    )
    result = pipeline.run("AI writing trends")

    assert result.task.status == PipelineStatus.COMPLETED
    assert result.task.plan_file.exists()
    assert result.task.research_file.exists()
    assert result.task.draft_file.exists()
    assert result.task.polished_file.exists()
    assert result.task.review_file.exists()
    assert result.task.final_file.exists()
    assert json.loads(result.task.plan_file.read_text(encoding="utf-8"))["title"] == "AI Writing Trends in 2026"
    assert json.loads(result.task.research_file.read_text(encoding="utf-8"))["key_takeaways"][0] == "AI tools are mainstream."


def test_pipeline_preserves_plan_when_writer_fails(tmp_path: Path) -> None:
    settings = Settings(DEEPSEEK_API_KEY="test-key", DATA_DIR=str(tmp_path / "data"))
    planner = Mock()
    planner.run.return_value = PlanResult(
        topic="AI writing trends",
        audience="content strategists",
        goal="explain the landscape",
        title="AI Writing Trends in 2026",
        outline=["Overview", "Adoption"],
        key_points=["Tools are mainstream"],
        constraints=["Professional tone"],
        research_questions=["What use cases are growing fastest?"],
    )
    researcher = Mock()
    researcher.run.return_value = ResearchResult(
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
    writer = Mock()
    writer.run.side_effect = RuntimeError("writer failed")

    auto_reflector = Mock()
    auto_reflector.reflect.side_effect = RuntimeError("reflection failed")
    pipeline = WritingPipeline(
        settings=settings,
        planner=planner,
        researcher=researcher,
        writer=writer,
        polisher=Mock(),
        reviewer=Mock(),
        auto_reflector=auto_reflector,
    )

    with pytest.raises(RuntimeError):
        pipeline.run("AI writing trends")

    task_dirs = list((settings.data_dir / "tasks").iterdir())
    assert len(task_dirs) == 1
    assert (task_dirs[0] / "plan.json").exists()
    assert (task_dirs[0] / "research.json").exists()


def test_pipeline_preserves_plan_when_research_fails(tmp_path: Path) -> None:
    settings = Settings(DEEPSEEK_API_KEY="test-key", DATA_DIR=str(tmp_path / "data"))
    planner = Mock()
    planner.run.return_value = PlanResult(
        topic="AI writing trends",
        audience="content strategists",
        goal="explain the landscape",
        title="AI Writing Trends in 2026",
        outline=["Overview", "Adoption"],
        key_points=["Tools are mainstream"],
        constraints=["Professional tone"],
        research_questions=["What use cases are growing fastest?"],
    )
    researcher = Mock()
    researcher.run.side_effect = RuntimeError("research failed")
    writer = Mock()

    auto_reflector = Mock()
    pipeline = WritingPipeline(
        settings=settings,
        planner=planner,
        researcher=researcher,
        writer=writer,
        polisher=Mock(),
        reviewer=Mock(),
        auto_reflector=auto_reflector,
    )

    with pytest.raises(RuntimeError):
        pipeline.run("AI writing trends")

    task_dirs = list((settings.data_dir / "tasks").iterdir())
    assert len(task_dirs) == 1
    assert (task_dirs[0] / "plan.json").exists()
    assert not (task_dirs[0] / "research.json").exists()


def test_pipeline_fails_after_two_review_retries(tmp_path: Path) -> None:
    settings = Settings(DEEPSEEK_API_KEY="test-key", DATA_DIR=str(tmp_path / "data"))
    planner = Mock()
    planner.run.return_value = PlanResult(
        topic="AI writing trends",
        audience="content strategists",
        goal="explain the landscape",
        title="AI Writing Trends in 2026",
        outline=["Overview", "Adoption"],
        key_points=["Tools are mainstream"],
        constraints=["Professional tone"],
        research_questions=["What use cases are growing fastest?"],
    )
    researcher = Mock()
    researcher.run.return_value = ResearchResult(
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
    writer = Mock()
    writer.run.return_value = "# AI Writing Trends in 2026\n\nIntro paragraph."
    polisher = Mock()
    polisher.run.side_effect = [
        "# Polished 1\n\nDraft.",
        "# Polished 2\n\nDraft.",
        "# Polished 3\n\nDraft.",
    ]
    reviewer = Mock()
    fail_review = ReviewResult(
        decision="fail",
        summary="Still not ready.",
        issues=[
            ReviewIssue(
                severity="high",
                title="Weak evidence",
                details="Claims still need better support.",
            )
        ],
        revision_instructions=["Strengthen evidence and tighten structure."],
    )
    reviewer.run.side_effect = [fail_review, fail_review, fail_review]

    auto_reflector = Mock()
    pipeline = WritingPipeline(
        settings=settings,
        planner=planner,
        researcher=researcher,
        writer=writer,
        polisher=polisher,
        reviewer=reviewer,
        auto_reflector=auto_reflector,
    )

    with pytest.raises(RuntimeError):
        pipeline.run("AI writing trends")

    task_dirs = list((settings.data_dir / "tasks").iterdir())
    assert len(task_dirs) == 1
    assert (task_dirs[0] / "polished.md").exists()
    assert (task_dirs[0] / "review.json").exists()
    assert not (task_dirs[0] / "final.md").exists()


def test_pipeline_triggers_auto_reflection_after_success(tmp_path: Path) -> None:
    settings = Settings(DEEPSEEK_API_KEY="test-key", DATA_DIR=str(tmp_path / "data"))
    planner = Mock()
    planner.run.return_value = PlanResult(
        topic="AI writing trends",
        audience="content strategists",
        goal="explain the landscape",
        title="AI Writing Trends in 2026",
        outline=["Overview", "Adoption"],
        key_points=["Tools are mainstream"],
        constraints=["Professional tone"],
        research_questions=["What use cases are growing fastest?"],
    )
    researcher = Mock()
    researcher.run.return_value = ResearchResult(
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
    writer = Mock()
    writer.run.return_value = "# AI Writing Trends in 2026\n\nIntro paragraph."
    polisher = Mock()
    polisher.run.return_value = "# Polished Draft\n\nImproved article."
    reviewer = Mock()
    reviewer.run.return_value = ReviewResult(
        decision="pass",
        summary="Ready to publish.",
        issues=[],
        revision_instructions=[],
    )
    auto_reflector = Mock()

    pipeline = WritingPipeline(
        settings=settings,
        planner=planner,
        researcher=researcher,
        writer=writer,
        polisher=polisher,
        reviewer=reviewer,
        auto_reflector=auto_reflector,
    )

    pipeline.run("AI writing trends")

    auto_reflector.reflect.assert_called_once()


def test_pipeline_failure_preserves_original_error_when_reflection_fails(tmp_path: Path) -> None:
    settings = Settings(DEEPSEEK_API_KEY="test-key", DATA_DIR=str(tmp_path / "data"))
    planner = Mock()
    planner.run.return_value = PlanResult(
        topic="AI writing trends",
        audience="content strategists",
        goal="explain the landscape",
        title="AI Writing Trends in 2026",
        outline=["Overview", "Adoption"],
        key_points=["Tools are mainstream"],
        constraints=["Professional tone"],
        research_questions=["What use cases are growing fastest?"],
    )
    researcher = Mock()
    researcher.run.return_value = ResearchResult(
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
    writer = Mock()
    writer.run.side_effect = RuntimeError("writer failed")
    auto_reflector = Mock()
    auto_reflector.reflect.side_effect = RuntimeError("reflection failed")

    pipeline = WritingPipeline(
        settings=settings,
        planner=planner,
        researcher=researcher,
        writer=writer,
        polisher=Mock(),
        reviewer=Mock(),
        auto_reflector=auto_reflector,
    )

    with pytest.raises(RuntimeError, match="writer failed"):
        pipeline.run("AI writing trends")
