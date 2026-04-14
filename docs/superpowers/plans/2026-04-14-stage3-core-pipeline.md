# Stage 3 Core Pipeline Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Build a minimum viable `planner -> writer` pipeline so `writing-agent write "<topic>"` creates a task workspace, writes `plan.json` and `draft.md`, records stage history, and previews the result in the terminal.

**Architecture:** The implementation introduces a typed task model, a typed planner result contract, prompt helper functions, and a real pipeline controller that orchestrates planner and writer stages. The CLI remains thin and only renders summaries and previews while the pipeline handles status transitions, file writes, and failure behavior.

**Tech Stack:** Python 3.11, Typer, Rich, pydantic, pytest

---

**Workspace note:** This workspace started outside Git. If upload is needed after verification, initialize Git and connect the provided remote only after tests pass.

### Task 1: Add the Task and Plan Models

**Files:**
- Modify: `src/writing_agent/controller/task.py`
- Test: `tests/test_pipeline/test_task.py`

- [ ] **Step 1: Write the failing tests**

```python
from __future__ import annotations

from pathlib import Path

from writing_agent.controller.task import PipelineStage, PipelineStatus, PipelineTask, PlanResult


def test_pipeline_task_creates_expected_output_paths(tmp_path: Path) -> None:
    task = PipelineTask.create(topic="AI writing trends", tasks_root=tmp_path)

    assert task.status == PipelineStatus.PENDING
    assert task.current_stage is None
    assert task.task_dir.parent == tmp_path
    assert task.plan_file == task.task_dir / "plan.json"
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
```

- [ ] **Step 2: Run the tests to verify they fail**

Run: `pytest tests/test_pipeline/test_task.py -v`
Expected: FAIL because the pipeline task and plan models do not exist yet.

- [ ] **Step 3: Write the minimal implementation**

```python
from __future__ import annotations

from datetime import UTC, datetime
from enum import StrEnum
from pathlib import Path
from uuid import uuid4

from pydantic import BaseModel


class PipelineStatus(StrEnum):
    PENDING = "pending"
    RUNNING = "running"
    COMPLETED = "completed"
    FAILED = "failed"


class PipelineStage(StrEnum):
    PLANNER = "planner"
    WRITER = "writer"


class PlanResult(BaseModel):
    topic: str
    audience: str
    goal: str
    title: str
    outline: list[str]
    key_points: list[str]
    constraints: list[str]
    research_questions: list[str]


class PipelineTask(BaseModel):
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
        task_id = datetime.now(UTC).strftime("%Y%m%d%H%M%S") + "-" + uuid4().hex[:8]
        task_dir = tasks_root / task_id
        return cls(
            task_id=task_id,
            topic=topic,
            status=PipelineStatus.PENDING,
            current_stage=None,
            created_at=datetime.now(UTC),
            updated_at=datetime.now(UTC),
            task_dir=task_dir,
            plan_file=task_dir / "plan.json",
            draft_file=task_dir / "draft.md",
        )
```

- [ ] **Step 4: Run the tests to verify they pass**

Run: `pytest tests/test_pipeline/test_task.py -v`
Expected: PASS with the task model and plan schema in place.

- [ ] **Step 5: Checkpoint**

Verification: `pytest tests/test_pipeline/test_task.py -v`

### Task 2: Add Prompt Helpers and the Planner/Writer Agents

**Files:**
- Modify: `src/writing_agent/llm/prompts/planner.py`
- Modify: `src/writing_agent/llm/prompts/writer.py`
- Modify: `src/writing_agent/agents/planner.py`
- Modify: `src/writing_agent/agents/writer.py`
- Test: `tests/test_agents/test_planner.py`
- Test: `tests/test_agents/test_writer.py`

- [ ] **Step 1: Write the failing tests**

```python
from __future__ import annotations

from unittest.mock import Mock

from writing_agent.agents.planner import PlannerAgent
from writing_agent.agents.writer import WriterAgent
from writing_agent.config import Settings
from writing_agent.controller.task import PlanResult


def test_planner_returns_typed_plan_result(tmp_path) -> None:
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
```

- [ ] **Step 2: Run the tests to verify they fail**

Run: `pytest tests/test_agents/test_planner.py tests/test_agents/test_writer.py -v`
Expected: FAIL because prompt helpers and concrete agent classes do not exist.

- [ ] **Step 3: Write the minimal implementation**

```python
def build_planner_prompt(topic: str) -> tuple[str, str]:
    system_prompt = "You are the planner agent for a multi-agent writing system."
    user_prompt = f"""Create a writing plan for the topic: {topic}

Return valid JSON with these fields:
- topic
- audience
- goal
- title
- outline
- key_points
- constraints
- research_questions
"""
    return system_prompt, user_prompt
```

```python
from writing_agent.controller.task import PlanResult


def build_writer_prompt(plan: PlanResult) -> tuple[str, str]:
    system_prompt = "You are the writer agent for a multi-agent writing system."
    user_prompt = f"""Write a complete Markdown draft using this plan:

Title: {plan.title}
Audience: {plan.audience}
Goal: {plan.goal}
Outline: {plan.outline}
Key points: {plan.key_points}
Constraints: {plan.constraints}

Return Markdown only.
"""
    return system_prompt, user_prompt
```

```python
class PlannerAgent(BaseAgent):
    def __init__(self, settings, sqlite_store, vector_store, llm_provider) -> None:
        super().__init__(
            name="planner",
            role="策划",
            settings=settings,
            sqlite_store=sqlite_store,
            vector_store=vector_store,
            llm_provider=llm_provider,
        )

    def run(self, topic: str) -> PlanResult:
        system_prompt, prompt = build_planner_prompt(topic)
        payload = self.llm_provider.generate_json(prompt=prompt, system_prompt=system_prompt, model="deepseek-reasoner")
        return PlanResult.model_validate(payload)
```

```python
class WriterAgent(BaseAgent):
    def __init__(self, settings, sqlite_store, vector_store, llm_provider) -> None:
        super().__init__(
            name="writer",
            role="主笔",
            settings=settings,
            sqlite_store=sqlite_store,
            vector_store=vector_store,
            llm_provider=llm_provider,
        )

    def run(self, plan: PlanResult) -> str:
        system_prompt, prompt = build_writer_prompt(plan)
        return self.llm_provider.generate(prompt=prompt, system_prompt=system_prompt, model="deepseek-chat")
```

- [ ] **Step 4: Run the tests to verify they pass**

Run: `pytest tests/test_agents/test_planner.py tests/test_agents/test_writer.py -v`
Expected: PASS with typed planner output and Markdown writer output.

- [ ] **Step 5: Checkpoint**

Verification: `pytest tests/test_agents/test_planner.py tests/test_agents/test_writer.py -v`

### Task 3: Build the Pipeline Orchestrator

**Files:**
- Modify: `src/writing_agent/controller/pipeline.py`
- Test: `tests/test_pipeline/test_pipeline.py`

- [ ] **Step 1: Write the failing tests**

```python
from __future__ import annotations

import json
from pathlib import Path
from unittest.mock import Mock

import pytest

from writing_agent.config import Settings
from writing_agent.controller.pipeline import WritingPipeline
from writing_agent.controller.task import PlanResult, PipelineStatus


def test_pipeline_writes_plan_and_draft(monkeypatch: pytest.MonkeyPatch, tmp_path: Path) -> None:
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
    writer = Mock()
    writer.run.return_value = "# AI Writing Trends in 2026\n\nIntro paragraph."

    pipeline = WritingPipeline(settings=settings, planner=planner, writer=writer)
    result = pipeline.run("AI writing trends")

    assert result.task.status == PipelineStatus.COMPLETED
    assert result.task.plan_file.exists()
    assert result.task.draft_file.exists()
    assert json.loads(result.task.plan_file.read_text(encoding="utf-8"))["title"] == "AI Writing Trends in 2026"


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
    writer = Mock()
    writer.run.side_effect = RuntimeError("writer failed")

    pipeline = WritingPipeline(settings=settings, planner=planner, writer=writer)

    with pytest.raises(RuntimeError):
        pipeline.run("AI writing trends")

    task_dirs = list((settings.data_dir / "tasks").iterdir())
    assert len(task_dirs) == 1
    assert (task_dirs[0] / "plan.json").exists()
```

- [ ] **Step 2: Run the tests to verify they fail**

Run: `pytest tests/test_pipeline/test_pipeline.py -v`
Expected: FAIL because the pipeline orchestrator does not exist.

- [ ] **Step 3: Write the minimal implementation**

```python
from __future__ import annotations

import json
from dataclasses import dataclass
from datetime import UTC, datetime

from writing_agent.agents.planner import PlannerAgent
from writing_agent.agents.writer import WriterAgent
from writing_agent.config import Settings
from writing_agent.controller.task import PipelineStage, PipelineStatus, PipelineTask, PlanResult


@dataclass(slots=True)
class PipelineRunResult:
    task: PipelineTask
    plan: PlanResult
    draft: str


class WritingPipeline:
    def __init__(self, settings: Settings, planner: PlannerAgent, writer: WriterAgent) -> None:
        self.settings = settings
        self.planner = planner
        self.writer = writer

    def run(self, topic: str) -> PipelineRunResult:
        task = PipelineTask.create(topic=topic, tasks_root=self.settings.data_dir / "tasks")
        task.task_dir.mkdir(parents=True, exist_ok=True)
        task.status = PipelineStatus.RUNNING
        task.current_stage = PipelineStage.PLANNER
        task.updated_at = datetime.now(UTC)

        plan = self.planner.run(topic)
        task.plan_file.write_text(json.dumps(plan.model_dump(), ensure_ascii=False, indent=2), encoding="utf-8")
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
```

- [ ] **Step 4: Run the tests to verify they pass**

Run: `pytest tests/test_pipeline/test_pipeline.py -v`
Expected: PASS with task creation, file persistence, and failure preservation covered.

- [ ] **Step 5: Checkpoint**

Verification: `pytest tests/test_pipeline/test_pipeline.py -v`

### Task 4: Wire the CLI `write` Command

**Files:**
- Modify: `src/writing_agent/cli/commands/write.py`
- Test: `tests/test_cli/test_write_command.py`

- [ ] **Step 1: Write the failing tests**

```python
from __future__ import annotations

from pathlib import Path

from typer.testing import CliRunner

from writing_agent.cli.app import app


def test_write_command_shows_paths_and_previews(monkeypatch, tmp_path: Path) -> None:
    runner = CliRunner()
    monkeypatch.chdir(tmp_path)
    monkeypatch.setenv("DEEPSEEK_API_KEY", "test-key")

    result = runner.invoke(app, ["write", "AI writing trends"])

    assert result.exit_code == 0
    assert "task_id" in result.stdout
    assert "plan.json" in result.stdout
    assert "draft.md" in result.stdout
    assert "Outline Preview" in result.stdout
    assert "Draft Preview" in result.stdout
```

- [ ] **Step 2: Run the tests to verify they fail**

Run: `pytest tests/test_cli/test_write_command.py -v`
Expected: FAIL because the CLI write command is not wired to the pipeline.

- [ ] **Step 3: Write the minimal implementation**

```python
from __future__ import annotations

import typer
from rich.console import Console

from writing_agent.agents.planner import PlannerAgent
from writing_agent.agents.writer import WriterAgent
from writing_agent.config import get_settings
from writing_agent.controller.pipeline import WritingPipeline
from writing_agent.llm.provider import LLMProvider
from writing_agent.storage.manager import StorageManager

console = Console()


def write_command(topic: str) -> None:
    settings = get_settings(clear_cache=True)
    manager = StorageManager(settings)
    planner = PlannerAgent(
        settings=settings,
        sqlite_store=manager.get_sqlite_store("planner"),
        vector_store=manager.get_vector_store("planner"),
        llm_provider=LLMProvider(settings),
    )
    writer = WriterAgent(
        settings=settings,
        sqlite_store=manager.get_sqlite_store("writer"),
        vector_store=manager.get_vector_store("writer"),
        llm_provider=LLMProvider(settings),
    )
    result = WritingPipeline(settings=settings, planner=planner, writer=writer).run(topic)
    console.print(f"task_id={result.task.task_id}")
    console.print(f"plan={result.task.plan_file}")
    console.print(f"draft={result.task.draft_file}")
    console.print("Outline Preview")
    for item in result.plan.outline[:5]:
        console.print(f"- {item}")
    console.print("Draft Preview")
    for line in result.draft.splitlines()[:12]:
        console.print(line)
```

- [ ] **Step 4: Run the tests to verify they pass**

Run: `pytest tests/test_cli/test_write_command.py -v`
Expected: PASS with command output and previews covered.

- [ ] **Step 5: Checkpoint**

Verification: `pytest tests/test_cli/test_write_command.py -v`

### Task 5: Run Stage 3 Verification and Prepare Upload

**Files:**
- Test: `tests/test_pipeline/test_task.py`
- Test: `tests/test_agents/test_planner.py`
- Test: `tests/test_agents/test_writer.py`
- Test: `tests/test_pipeline/test_pipeline.py`
- Test: `tests/test_cli/test_write_command.py`

- [ ] **Step 1: Run the Stage 3 verification suite**

Run: `pytest tests/test_pipeline/test_task.py tests/test_agents/test_planner.py tests/test_agents/test_writer.py tests/test_pipeline/test_pipeline.py tests/test_cli/test_write_command.py -v`
Expected: PASS with the planner and writer pipeline fully covered.

- [ ] **Step 2: Run the broader regression suite**

Run: `pytest tests/test_config.py tests/test_storage/test_sqlite_store.py tests/test_storage/test_manager.py tests/test_storage/test_vector_store.py tests/test_llm/test_provider.py tests/test_cli/test_init_command.py tests/test_cli/test_config_command.py tests/test_pipeline/test_task.py tests/test_agents/test_planner.py tests/test_agents/test_writer.py tests/test_pipeline/test_pipeline.py tests/test_cli/test_write_command.py -v`
Expected: PASS with Stage 2 and Stage 3 behavior working together.

- [ ] **Step 3: If upload is requested, initialize Git and connect the remote**

Run:

```bash
git init
git branch -M main
git remote add origin https://github.com/hamburger-lie/writer-agent.git
```

Expected: Local repository initialized and remote attached.

- [ ] **Step 4: Commit and push only after tests pass**

Run:

```bash
git add .
git commit -m "feat: add planner to writer core pipeline"
git push -u origin main
```

Expected: Branch pushed to the provided repository. If authentication blocks push, stop and report the blocker instead of guessing.
