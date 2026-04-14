"""Main orchestrator for the Stage 3 planner-to-writer pipeline."""

from __future__ import annotations

import json
from dataclasses import dataclass
from datetime import UTC, datetime

from writing_agent.config import Settings
from writing_agent.controller.task import PipelineStage, PipelineStatus, PipelineTask, PlanResult


@dataclass(slots=True)
class PipelineRunResult:
    """Result returned from a successful pipeline execution."""

    task: PipelineTask
    plan: PlanResult
    draft: str


class WritingPipeline:
    """Run the minimum viable planner-to-writer pipeline."""

    def __init__(self, settings: Settings, planner, writer) -> None:
        self.settings = settings
        self.planner = planner
        self.writer = writer

    def run(self, topic: str) -> PipelineRunResult:
        task = PipelineTask.create(topic=topic, tasks_root=self.settings.data_dir / "tasks")
        task.task_dir.mkdir(parents=True, exist_ok=True)
        task.status = PipelineStatus.RUNNING
        task.current_stage = PipelineStage.PLANNER
        task.updated_at = datetime.now(UTC)

        try:
            plan = self.planner.run(topic)
        except Exception:
            task.status = PipelineStatus.FAILED
            task.updated_at = datetime.now(UTC)
            self.planner.record_task_history(
                task_id=task.task_id,
                task_type="planner",
                status="failed",
                input_summary=topic,
                output_summary=None,
            )
            raise

        task.plan_file.write_text(
            json.dumps(plan.model_dump(), ensure_ascii=False, indent=2),
            encoding="utf-8",
        )
        self.planner.record_task_history(
            task_id=task.task_id,
            task_type="planner",
            status="success",
            input_summary=topic,
            output_summary=plan.title,
        )

        task.current_stage = PipelineStage.WRITER
        task.updated_at = datetime.now(UTC)
        try:
            draft = self.writer.run(plan)
        except Exception:
            task.status = PipelineStatus.FAILED
            task.updated_at = datetime.now(UTC)
            self.writer.record_task_history(
                task_id=task.task_id,
                task_type="writer",
                status="failed",
                input_summary=plan.title,
                output_summary=None,
            )
            raise

        task.draft_file.write_text(draft, encoding="utf-8")
        self.writer.record_task_history(
            task_id=task.task_id,
            task_type="writer",
            status="success",
            input_summary=plan.title,
            output_summary=draft.splitlines()[0] if draft else "",
        )

        task.status = PipelineStatus.COMPLETED
        task.updated_at = datetime.now(UTC)
        return PipelineRunResult(task=task, plan=plan, draft=draft)
