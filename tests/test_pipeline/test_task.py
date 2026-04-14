from __future__ import annotations

from pathlib import Path

from writing_agent.controller.task import (
    PipelineStatus,
    PipelineTask,
    PlanResult,
    ResearchFinding,
    ResearchResult,
    ResearchSource,
)


def test_pipeline_task_creates_expected_output_paths(tmp_path: Path) -> None:
    task = PipelineTask.create(topic="AI writing trends", tasks_root=tmp_path)

    assert task.status == PipelineStatus.PENDING
    assert task.current_stage is None
    assert task.task_dir.parent == tmp_path
    assert task.plan_file == task.task_dir / "plan.json"
    assert task.research_file == task.task_dir / "research.json"
    assert task.draft_file == task.task_dir / "draft.md"


def test_plan_result_serializes_to_json_ready_payload() -> None:
    plan = PlanResult(
        topic="AI writing trends",
        audience="content strategists",
        goal="explain the landscape",
        title="AI Writing Trends in 2026",
        outline=["Overview", "Adoption", "Risks"],
        key_points=["Tools are mainstream", "Quality control still matters"],
        constraints=["Professional tone"],
        research_questions=["What are the fastest-growing use cases?"],
    )

    payload = plan.model_dump()

    assert payload["title"] == "AI Writing Trends in 2026"
    assert payload["outline"][1] == "Adoption"


def test_research_result_serializes_nested_sources_and_findings() -> None:
    result = ResearchResult(
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
                claim="AI tools are becoming standard in content teams.",
                evidence="A market survey reports strong adoption growth.",
                source_url="https://example.com/report",
            )
        ],
        key_takeaways=["AI writing tools are now mainstream."],
        open_questions=["Which verticals are adopting fastest?"],
    )

    payload = result.model_dump()

    assert payload["sources"][0]["url"] == "https://example.com/report"
    assert payload["findings"][0]["source_url"] == "https://example.com/report"
