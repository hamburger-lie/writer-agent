"""Main orchestrator for the Stage 3 planner-to-writer pipeline."""

from __future__ import annotations

import json
from dataclasses import dataclass
from datetime import UTC, datetime

from writing_agent.config import Settings
from writing_agent.controller.task import (
    PipelineStage,
    PipelineStatus,
    PipelineTask,
    PlanResult,
    ReflectionContext,
    ResearchResult,
    ReviewResult,
)


@dataclass(slots=True)
class PipelineRunResult:
    """Result returned from a successful pipeline execution."""

    task: PipelineTask
    plan: PlanResult
    research: ResearchResult
    draft: str
    polished: str
    review: ReviewResult
    final: str


class WritingPipeline:
    """Run the minimum viable planner-to-writer pipeline."""

    def __init__(
        self,
        settings: Settings,
        planner,
        researcher,
        writer,
        polisher,
        reviewer,
        auto_reflector=None,
    ) -> None:
        self.settings = settings
        self.planner = planner
        self.researcher = researcher
        self.writer = writer
        self.polisher = polisher
        self.reviewer = reviewer
        self.auto_reflector = auto_reflector

    def run(self, topic: str) -> PipelineRunResult:
        task = PipelineTask.create(topic=topic, tasks_root=self.settings.data_dir / "tasks")
        task.task_dir.mkdir(parents=True, exist_ok=True)
        task.status = PipelineStatus.RUNNING
        task.current_stage = PipelineStage.PLANNER
        task.updated_at = datetime.now(UTC)
        plan: PlanResult | None = None
        research: ResearchResult | None = None
        draft: str | None = None
        current_polished: str | None = None
        current_review: ReviewResult | None = None

        try:
            plan = self.planner.run(topic)
        except Exception as exc:
            task.status = PipelineStatus.FAILED
            task.updated_at = datetime.now(UTC)
            self.planner.record_task_history(
                task_id=task.task_id,
                task_type="planner",
                status="failed",
                input_summary=topic,
                output_summary=None,
            )
            self._run_auto_reflection(
                task=task,
                topic=topic,
                plan=plan,
                review=current_review,
                error=exc,
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

        task.current_stage = PipelineStage.RESEARCHER
        task.updated_at = datetime.now(UTC)
        try:
            research = self.researcher.run(plan)
        except Exception as exc:
            task.status = PipelineStatus.FAILED
            task.updated_at = datetime.now(UTC)
            self.researcher.record_task_history(
                task_id=task.task_id,
                task_type="researcher",
                status="failed",
                input_summary=plan.title,
                output_summary=None,
            )
            self._run_auto_reflection(
                task=task,
                topic=topic,
                plan=plan,
                review=current_review,
                error=exc,
            )
            raise

        task.research_file.write_text(
            json.dumps(research.model_dump(), ensure_ascii=False, indent=2),
            encoding="utf-8",
        )
        self.researcher.record_task_history(
            task_id=task.task_id,
            task_type="researcher",
            status="success",
            input_summary=plan.title,
            output_summary=research.key_takeaways[0] if research.key_takeaways else research.topic,
        )

        task.current_stage = PipelineStage.WRITER
        task.updated_at = datetime.now(UTC)
        try:
            draft = self.writer.run(plan, research)
        except Exception as exc:
            task.status = PipelineStatus.FAILED
            task.updated_at = datetime.now(UTC)
            self.writer.record_task_history(
                task_id=task.task_id,
                task_type="writer",
                status="failed",
                input_summary=plan.title,
                output_summary=None,
            )
            self._run_auto_reflection(
                task=task,
                topic=topic,
                plan=plan,
                review=current_review,
                error=exc,
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

        current_polished = draft
        current_draft = draft

        for review_round in range(3):
            task.current_stage = PipelineStage.POLISHER
            task.updated_at = datetime.now(UTC)
            try:
                current_polished = self.polisher.run(
                    draft=current_draft,
                    plan=plan,
                    research=research,
                    review=current_review,
                )
            except Exception as exc:
                task.status = PipelineStatus.FAILED
                task.updated_at = datetime.now(UTC)
                self.polisher.record_task_history(
                    task_id=task.task_id,
                    task_type="polisher",
                    status="failed",
                    input_summary=plan.title,
                    output_summary=None,
                )
                self._run_auto_reflection(
                    task=task,
                    topic=topic,
                    plan=plan,
                    review=current_review,
                    error=exc,
                )
                raise

            task.polished_file.write_text(current_polished, encoding="utf-8")
            self.polisher.record_task_history(
                task_id=task.task_id,
                task_type="polisher",
                status="success",
                input_summary=plan.title,
                output_summary=current_polished.splitlines()[0] if current_polished else "",
            )

            task.current_stage = PipelineStage.REVIEWER
            task.updated_at = datetime.now(UTC)
            try:
                current_review = self.reviewer.run(current_polished, plan, research)
            except Exception as exc:
                task.status = PipelineStatus.FAILED
                task.updated_at = datetime.now(UTC)
                self.reviewer.record_task_history(
                    task_id=task.task_id,
                    task_type="reviewer",
                    status="failed",
                    input_summary=plan.title,
                    output_summary=None,
                )
                self._run_auto_reflection(
                    task=task,
                    topic=topic,
                    plan=plan,
                    review=current_review,
                    error=exc,
                )
                raise

            task.review_file.write_text(
                json.dumps(current_review.model_dump(), ensure_ascii=False, indent=2),
                encoding="utf-8",
            )
            self.reviewer.record_task_history(
                task_id=task.task_id,
                task_type="reviewer",
                status="success",
                input_summary=plan.title,
                output_summary=current_review.decision,
            )

            if current_review.decision == "pass":
                task.final_file.write_text(current_polished, encoding="utf-8")
                task.status = PipelineStatus.COMPLETED
                task.updated_at = datetime.now(UTC)
                self._run_auto_reflection(
                    task=task,
                    topic=topic,
                    plan=plan,
                    review=current_review,
                    error=None,
                )
                return PipelineRunResult(
                    task=task,
                    plan=plan,
                    research=research,
                    draft=draft,
                    polished=current_polished,
                    review=current_review,
                    final=current_polished,
                )

            current_draft = current_polished

        task.status = PipelineStatus.FAILED
        task.updated_at = datetime.now(UTC)
        review_loop_error = RuntimeError("Review loop exceeded maximum retries.")
        self._run_auto_reflection(
            task=task,
            topic=topic,
            plan=plan,
            review=current_review,
            error=review_loop_error,
        )
        raise review_loop_error

    def _run_auto_reflection(
        self,
        task: PipelineTask,
        topic: str,
        plan: PlanResult | None,
        review: ReviewResult | None,
        error: Exception | None,
    ) -> None:
        if self.auto_reflector is None:
            return

        context = ReflectionContext(
            task_id=task.task_id,
            topic=topic,
            status=task.status.value,
            current_stage=None if task.current_stage is None else task.current_stage.value,
            plan_title=None if plan is None else plan.title,
            review_decision=None if review is None else review.decision,
            review_summary=None if review is None else review.summary,
            error_message=None if error is None else str(error),
        )
        try:
            self.auto_reflector.reflect(context)
        except Exception:
            return
