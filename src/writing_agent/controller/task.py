"""Pipeline task and planner output models."""

from __future__ import annotations

from datetime import UTC, datetime
from enum import StrEnum
from pathlib import Path
from uuid import uuid4

from pydantic import BaseModel


class PipelineStatus(StrEnum):
    """Lifecycle statuses for a pipeline task."""

    PENDING = "pending"
    RUNNING = "running"
    COMPLETED = "completed"
    FAILED = "failed"


class PipelineStage(StrEnum):
    """Supported stages in the Stage 3 pipeline."""

    PLANNER = "planner"
    WRITER = "writer"


class PlanResult(BaseModel):
    """Structured planner output persisted to `plan.json`."""

    topic: str
    audience: str
    goal: str
    title: str
    outline: list[str]
    key_points: list[str]
    constraints: list[str]
    research_questions: list[str]


class PipelineTask(BaseModel):
    """Runtime metadata for a single writing task execution."""

    task_id: str
    topic: str
    status: PipelineStatus
    current_stage: PipelineStage | None
    created_at: datetime
    updated_at: datetime
    task_dir: Path
    plan_file: Path
    draft_file: Path

    @classmethod
    def create(cls, topic: str, tasks_root: Path) -> "PipelineTask":
        now = datetime.now(UTC)
        task_id = now.strftime("%Y%m%d%H%M%S") + "-" + uuid4().hex[:8]
        task_dir = tasks_root / task_id
        return cls(
            task_id=task_id,
            topic=topic,
            status=PipelineStatus.PENDING,
            current_stage=None,
            created_at=now,
            updated_at=now,
            task_dir=task_dir,
            plan_file=task_dir / "plan.json",
            draft_file=task_dir / "draft.md",
        )
