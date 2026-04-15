# Stage 5 Polish Review Loop Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Add a structured `polisher -> reviewer` loop to the pipeline, with up to two review-driven revision retries and `final.md` output on success.

**Architecture:** The pipeline keeps orchestration ownership while `PolisherAgent` and `ReviewerAgent` stay focused on content transformation and structured evaluation. Reviewer output becomes strict JSON so the pipeline can branch deterministically.

**Tech Stack:** Python 3.11, Typer, Rich, pydantic, pytest

---

### Task 1: Add Review Models and Output Paths

**Files:**
- Modify: `src/writing_agent/controller/task.py`
- Test: `tests/test_pipeline/test_task.py`

- [ ] **Step 1: Write the failing tests**

```python
from writing_agent.controller.task import ReviewIssue, ReviewResult


def test_review_result_serializes_nested_issues() -> None:
    review = ReviewResult(
        decision="fail",
        summary="Needs stronger evidence and smoother flow.",
        issues=[
            ReviewIssue(
                severity="high",
                title="Weak evidence",
                details="Several claims need clearer source-backed support.",
            )
        ],
        revision_instructions=[
            "Strengthen evidence in the market adoption section.",
            "Tighten transitions between sections.",
        ],
    )

    payload = review.model_dump()

    assert payload["decision"] == "fail"
    assert payload["issues"][0]["severity"] == "high"
```

- [ ] **Step 2: Run test to verify it fails**

Run: `pytest tests/test_pipeline/test_task.py -v`
Expected: FAIL because review models and output paths do not exist yet.

- [ ] **Step 3: Write minimal implementation**

```python
class ReviewIssue(BaseModel):
    severity: str
    title: str
    details: str


class ReviewResult(BaseModel):
    decision: str
    summary: str
    issues: list[ReviewIssue]
    revision_instructions: list[str]
```

- [ ] **Step 4: Run test to verify it passes**

Run: `pytest tests/test_pipeline/test_task.py -v`
Expected: PASS with review schema coverage.

### Task 2: Implement Polisher and Reviewer Agents

**Files:**
- Modify: `src/writing_agent/llm/prompts/polisher.py`
- Modify: `src/writing_agent/llm/prompts/reviewer.py`
- Modify: `src/writing_agent/agents/polisher.py`
- Modify: `src/writing_agent/agents/reviewer.py`
- Test: `tests/test_agents/test_polisher.py`
- Test: `tests/test_agents/test_reviewer.py`

- [ ] **Step 1: Write the failing tests**

```python
from unittest.mock import Mock

from writing_agent.agents.polisher import PolisherAgent
from writing_agent.agents.reviewer import ReviewerAgent
from writing_agent.config import Settings
from writing_agent.controller.task import PlanResult, ResearchResult, ReviewResult


def test_polisher_returns_markdown() -> None:
    llm_provider = Mock()
    llm_provider.generate.return_value = "# Final Draft\n\nImproved article."
    agent = PolisherAgent(Settings(DEEPSEEK_API_KEY="test-key"), Mock(), Mock(), llm_provider)

    result = agent.run(
        draft="# Draft\n\nOriginal article.",
        plan=Mock(spec=PlanResult),
        research=Mock(spec=ResearchResult),
        review=None,
    )

    assert result.startswith("# Final Draft")


def test_reviewer_returns_typed_review_result() -> None:
    llm_provider = Mock()
    llm_provider.generate_json.return_value = {
        "decision": "fail",
        "summary": "Needs stronger evidence.",
        "issues": [
            {
                "severity": "high",
                "title": "Weak evidence",
                "details": "Claims need source-backed support.",
            }
        ],
        "revision_instructions": ["Add stronger evidence to key sections."],
    }
    agent = ReviewerAgent(Settings(DEEPSEEK_API_KEY="test-key"), Mock(), Mock(), llm_provider)

    result = agent.run("# Draft\n\nArticle text.", Mock(spec=PlanResult), Mock(spec=ResearchResult))

    assert isinstance(result, ReviewResult)
    assert result.decision == "fail"
```

- [ ] **Step 2: Run tests to verify they fail**

Run: `pytest tests/test_agents/test_polisher.py tests/test_agents/test_reviewer.py -v`
Expected: FAIL because the agents are not implemented.

- [ ] **Step 3: Write minimal implementation**

```python
class PolisherAgent(BaseAgent):
    ...

    def run(self, draft: str, plan: PlanResult, research: ResearchResult, review: ReviewResult | None) -> str:
        ...
```

```python
class ReviewerAgent(BaseAgent):
    ...

    def run(self, draft: str, plan: PlanResult, research: ResearchResult) -> ReviewResult:
        ...
```

- [ ] **Step 4: Run tests to verify they pass**

Run: `pytest tests/test_agents/test_polisher.py tests/test_agents/test_reviewer.py -v`
Expected: PASS with markdown polish and structured review covered.

### Task 3: Upgrade the Pipeline Loop

**Files:**
- Modify: `src/writing_agent/controller/pipeline.py`
- Test: `tests/test_pipeline/test_pipeline.py`

- [ ] **Step 1: Write the failing tests**

```python
def test_pipeline_writes_final_when_review_passes(tmp_path: Path) -> None:
    ...
    assert result.task.final_file.exists()


def test_pipeline_fails_after_two_review_retries(tmp_path: Path) -> None:
    ...
    with pytest.raises(RuntimeError):
        pipeline.run("AI writing trends")
    assert (task_dir / "review.json").exists()
```

- [ ] **Step 2: Run tests to verify they fail**

Run: `pytest tests/test_pipeline/test_pipeline.py -v`
Expected: FAIL because the loop logic does not exist yet.

- [ ] **Step 3: Write minimal implementation**

```python
for attempt in range(3):
    polished = self.polisher.run(...)
    review = self.reviewer.run(...)
    if review.decision == "pass":
        write final.md
        return
raise RuntimeError("Review loop exceeded maximum retries.")
```

- [ ] **Step 4: Run tests to verify they pass**

Run: `pytest tests/test_pipeline/test_pipeline.py -v`
Expected: PASS with pass-path and max-retry failure-path covered.

### Task 4: Update the CLI Summary

**Files:**
- Modify: `src/writing_agent/cli/commands/write.py`
- Test: `tests/test_cli/test_write_command.py`

- [ ] **Step 1: Write the failing tests**

```python
assert "polished.md" in result.stdout
assert "review.json" in result.stdout
assert "final.md" in result.stdout
```

- [ ] **Step 2: Run tests to verify they fail**

Run: `pytest tests/test_cli/test_write_command.py -v`
Expected: FAIL because the CLI does not expose polish/review/final outputs yet.

- [ ] **Step 3: Write minimal implementation**

```python
console.print(f"polished={result.task.polished_file}")
console.print(f"review={result.task.review_file}")
console.print(f"final={result.task.final_file}")
```

- [ ] **Step 4: Run tests to verify they pass**

Run: `pytest tests/test_cli/test_write_command.py -v`
Expected: PASS with final-stage output reporting covered.

### Task 5: Run Regression And Push

- [ ] **Step 1: Run stage-specific verification**

Run: `pytest tests/test_agents/test_polisher.py tests/test_agents/test_reviewer.py tests/test_pipeline/test_pipeline.py tests/test_cli/test_write_command.py -v`
Expected: PASS.

- [ ] **Step 2: Run full regression**

Run: `pytest tests -v`
Expected: PASS across stages 2-5.

- [ ] **Step 3: Commit and push**

Run:

```bash
git add .
git commit -m "feat: add polisher reviewer loop to pipeline"
git push
```

Expected: Changes are published to the configured remote.
