# Stage 7 Auto Reflection Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Add one automatic post-run reflection pass that stores repeated lessons and promotes stable lessons into reviewer rules.

**Architecture:** Keep reflection as a small, pipeline-end service. `WritingPipeline` will call an `AutoReflectionEngine`, which asks the LLM for structured lessons and persists them in the reviewer SQLite store with recurrence tracking and promotion logic.

**Tech Stack:** Python, Pydantic, sqlite3, pytest, existing DeepSeek provider

---

### Task 1: Add failing storage tests for reflection aggregation

**Files:**
- Modify: `tests/test_storage/test_sqlite_store.py`
- Modify: `src/writing_agent/storage/sqlite_store.py`

- [ ] **Step 1: Write the failing tests**

```python
def test_record_reflection_observation_increments_times_seen(tmp_path: Path) -> None:
    store = SQLiteStore(tmp_path / "reviewer.db")
    store.initialize_schema()

    first_id = store.record_reflection_observation(
        reflection_text="Strengthen evidence before review.",
        task_id="task-1",
        trigger_context="review failed",
    )
    second_id = store.record_reflection_observation(
        reflection_text="Strengthen evidence before review.",
        task_id="task-2",
        trigger_context="review failed again",
    )

    rows = store.list_reflections()

    assert second_id == first_id
    assert len(rows) == 1
    assert rows[0]["times_seen"] == 2


def test_mark_reflection_promoted_updates_flag(tmp_path: Path) -> None:
    store = SQLiteStore(tmp_path / "reviewer.db")
    store.initialize_schema()

    reflection_id = store.record_reflection_observation(
        reflection_text="Tighten structure before review.",
        task_id="task-1",
        trigger_context="review failed",
    )

    store.mark_reflection_promoted(reflection_id)

    rows = store.list_reflections()
    assert rows[0]["promoted_to_rule"] == 1
```

- [ ] **Step 2: Run test to verify it fails**

Run: `pytest tests/test_storage/test_sqlite_store.py -v`
Expected: FAIL because `record_reflection_observation`, `list_reflections`, and `mark_reflection_promoted` do not exist yet

- [ ] **Step 3: Write minimal implementation**

```python
def list_reflections(self) -> list[sqlite3.Row]:
    with self._connect() as conn:
        return list(conn.execute("SELECT * FROM reflections ORDER BY created_at DESC").fetchall())


def record_reflection_observation(
    self,
    reflection_text: str,
    task_id: str | None = None,
    trigger_context: str | None = None,
) -> int:
    with self._connect() as conn:
        existing = conn.execute(
            "SELECT id, times_seen FROM reflections WHERE reflection_text = ?",
            (reflection_text,),
        ).fetchone()
        if existing is None:
            cursor = conn.execute(
                """
                INSERT INTO reflections(task_id, reflection_text, trigger_context, times_seen, promoted_to_rule, created_at)
                VALUES(?, ?, ?, 1, 0, ?)
                """,
                (task_id, reflection_text, trigger_context, datetime.now(UTC).isoformat()),
            )
            conn.commit()
            return int(cursor.lastrowid)

        conn.execute(
            """
            UPDATE reflections
            SET task_id = ?, trigger_context = ?, times_seen = ?
            WHERE id = ?
            """,
            (task_id, trigger_context, int(existing["times_seen"]) + 1, int(existing["id"])),
        )
        conn.commit()
        return int(existing["id"])


def mark_reflection_promoted(self, reflection_id: int) -> None:
    with self._connect() as conn:
        conn.execute(
            "UPDATE reflections SET promoted_to_rule = 1 WHERE id = ?",
            (reflection_id,),
        )
        conn.commit()
```

- [ ] **Step 4: Run test to verify it passes**

Run: `pytest tests/test_storage/test_sqlite_store.py -v`
Expected: PASS

- [ ] **Step 5: Commit**

```bash
git add tests/test_storage/test_sqlite_store.py src/writing_agent/storage/sqlite_store.py
git commit -m "feat: add reflection aggregation helpers"
```

### Task 2: Add failing tests for the auto reflection engine

**Files:**
- Create: `tests/test_reflection/test_auto_reflect.py`
- Create: `src/writing_agent/reflection/auto_reflect.py`
- Modify: `src/writing_agent/llm/prompts/reflection.py`
- Modify: `src/writing_agent/controller/task.py`

- [ ] **Step 1: Write the failing tests**

```python
def test_auto_reflection_persists_lessons_and_promotes_repeated_rule(tmp_path: Path) -> None:
    store = SQLiteStore(tmp_path / "reviewer.db")
    store.initialize_schema()
    provider = Mock()
    provider.generate_json.return_value = {
        "summary": "Review loop exposed a recurring evidence gap.",
        "lessons": [
            {
                "reflection_text": "Strengthen evidence support before review.",
                "category": "evidence",
                "confidence": 0.9,
            }
        ],
    }
    engine = AutoReflectionEngine(llm_provider=provider, sqlite_store=store, promotion_threshold=3)

    context = ReflectionContext(
        task_id="task-1",
        topic="AI writing trends",
        status="completed",
        current_stage="reviewer",
        plan_title="AI Writing Trends in 2026",
        review_decision="fail",
        review_summary="Evidence is thin.",
        error_message=None,
    )

    engine.reflect(context)
    engine.reflect(context.model_copy(update={"task_id": "task-2"}))
    result = engine.reflect(context.model_copy(update={"task_id": "task-3"}))

    rows = store.list_reflections()
    rules = store.list_active_rules()

    assert result.lessons[0].reflection_text == "Strengthen evidence support before review."
    assert rows[0]["times_seen"] == 3
    assert rows[0]["promoted_to_rule"] == 1
    assert rules[0]["rule_text"] == "Strengthen evidence support before review."
```

- [ ] **Step 2: Run test to verify it fails**

Run: `pytest tests/test_reflection/test_auto_reflect.py -v`
Expected: FAIL because the reflection engine and models do not exist yet

- [ ] **Step 3: Write minimal implementation**

```python
class ReflectionLesson(BaseModel):
    reflection_text: str
    category: str
    confidence: float


class ReflectionContext(BaseModel):
    task_id: str
    topic: str
    status: str
    current_stage: str | None
    plan_title: str | None
    review_decision: str | None
    review_summary: str | None
    error_message: str | None


class ReflectionResult(BaseModel):
    summary: str
    lessons: list[ReflectionLesson]


class AutoReflectionEngine:
    def reflect(self, context: ReflectionContext) -> ReflectionResult:
        system_prompt, prompt = build_auto_reflection_prompt(context)
        payload = self.llm_provider.generate_json(prompt=prompt, system_prompt=system_prompt)
        result = ReflectionResult.model_validate(payload)
        for lesson in result.lessons:
            reflection_id = self.sqlite_store.record_reflection_observation(
                reflection_text=lesson.reflection_text,
                task_id=context.task_id,
                trigger_context=context.status,
            )
            row = self.sqlite_store.get_reflection(reflection_id)
            if row and int(row["times_seen"]) >= self.promotion_threshold and not int(row["promoted_to_rule"]):
                self.sqlite_store.add_rule(
                    rule_text=lesson.reflection_text,
                    source="auto_reflection",
                    confidence=lesson.confidence,
                    category=lesson.category,
                )
                self.sqlite_store.mark_reflection_promoted(reflection_id)
        return result
```

- [ ] **Step 4: Run test to verify it passes**

Run: `pytest tests/test_reflection/test_auto_reflect.py -v`
Expected: PASS

- [ ] **Step 5: Commit**

```bash
git add tests/test_reflection/test_auto_reflect.py src/writing_agent/reflection/auto_reflect.py src/writing_agent/llm/prompts/reflection.py src/writing_agent/controller/task.py src/writing_agent/storage/sqlite_store.py
git commit -m "feat: add automatic reflection engine"
```

### Task 3: Add failing pipeline tests for reflection triggers

**Files:**
- Modify: `tests/test_pipeline/test_pipeline.py`
- Modify: `src/writing_agent/controller/pipeline.py`

- [ ] **Step 1: Write the failing tests**

```python
def test_pipeline_triggers_auto_reflection_after_success(tmp_path: Path) -> None:
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
    auto_reflector = Mock()
    auto_reflector.reflect.side_effect = RuntimeError("reflection failed")
    writer.run.side_effect = RuntimeError("writer failed")
    pipeline = WritingPipeline(
        settings=settings,
        planner=planner,
        researcher=researcher,
        writer=writer,
        polisher=polisher,
        reviewer=reviewer,
        auto_reflector=auto_reflector,
    )

    with pytest.raises(RuntimeError, match="writer failed"):
        pipeline.run("AI writing trends")
```

- [ ] **Step 2: Run test to verify it fails**

Run: `pytest tests/test_pipeline/test_pipeline.py -v`
Expected: FAIL because `WritingPipeline` does not accept or invoke `auto_reflector`

- [ ] **Step 3: Write minimal implementation**

```python
def __init__(..., auto_reflector=None) -> None:
    self.auto_reflector = auto_reflector


def _run_auto_reflection(self, context: ReflectionContext) -> None:
    if self.auto_reflector is None:
        return
    try:
        self.auto_reflector.reflect(context)
    except Exception:
        return
```

Then call `_run_auto_reflection(...)` once on success and once in each failure path before re-raising.

- [ ] **Step 4: Run test to verify it passes**

Run: `pytest tests/test_pipeline/test_pipeline.py -v`
Expected: PASS

- [ ] **Step 5: Commit**

```bash
git add tests/test_pipeline/test_pipeline.py src/writing_agent/controller/pipeline.py
git commit -m "feat: trigger auto reflection from pipeline"
```

### Task 4: Full verification and documentation check

**Files:**
- Modify: `docs/superpowers/specs/2026-04-15-stage7-auto-reflection-design.md`
- Modify: `docs/superpowers/plans/2026-04-15-stage7-auto-reflection.md`

- [ ] **Step 1: Run the focused test suite**

Run: `pytest tests/test_storage/test_sqlite_store.py tests/test_reflection/test_auto_reflect.py tests/test_pipeline/test_pipeline.py -v`
Expected: PASS

- [ ] **Step 2: Run the full test suite**

Run: `pytest tests -v`
Expected: PASS

- [ ] **Step 3: Check git status**

Run: `git status --short`
Expected: only intended tracked changes plus the existing untracked `~$README.md`

- [ ] **Step 4: Commit**

```bash
git add docs/superpowers/specs/2026-04-15-stage7-auto-reflection-design.md docs/superpowers/plans/2026-04-15-stage7-auto-reflection.md
git commit -m "docs: add stage7 auto reflection design and plan"
```
