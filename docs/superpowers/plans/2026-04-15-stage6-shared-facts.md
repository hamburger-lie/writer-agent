# Stage 6 Shared Facts Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Add a shared SQLite-backed fact library that researcher can write into and writer can read from during drafting.

**Architecture:** Introduce a `SharedKnowledgeStore` plus a thin `LibrarianAgent` service. Researcher ingests normalized findings after successful research, and writer retrieves relevant facts before prompting the LLM.

**Tech Stack:** Python, sqlite3, Pydantic, pytest

---

### Task 1: Add failing tests for shared fact storage

**Files:**
- Create: `tests/test_storage/test_shared_knowledge_store.py`
- Create: `src/writing_agent/storage/shared_knowledge_store.py`
- Modify: `src/writing_agent/controller/task.py`

- [ ] **Step 1: Write the failing tests**

```python
def test_shared_store_deduplicates_ingested_fact_rows(tmp_path: Path) -> None:
    store = SharedKnowledgeStore(tmp_path / "library.db")
    store.initialize_schema()
    fact = SharedFact(
        topic="AI writing trends",
        title="AI Writing Trends in 2026",
        claim="AI tools are mainstream.",
        evidence="Enterprise adoption is broad.",
        source_url="https://example.com/report",
        source_title="Example Report",
        source_snippet="Broad adoption",
        takeaway="AI is mainstream.",
    )

    store.upsert_fact(fact)
    store.upsert_fact(fact)

    rows = store.list_facts()
    assert len(rows) == 1


def test_shared_store_search_returns_matching_fact(tmp_path: Path) -> None:
    store = SharedKnowledgeStore(tmp_path / "library.db")
    store.initialize_schema()
    store.upsert_fact(...)

    results = store.search(["enterprise", "adoption"], limit=5)

    assert len(results) == 1
    assert results[0].claim == "AI tools are mainstream."
```

- [ ] **Step 2: Run test to verify it fails**

Run: `pytest tests/test_storage/test_shared_knowledge_store.py -v`
Expected: FAIL because the shared knowledge store does not exist yet

- [ ] **Step 3: Write minimal implementation**

```python
class SharedFact(BaseModel):
    ...


class SharedKnowledgeStore:
    def initialize_schema(self) -> None:
        ...

    def upsert_fact(self, fact: SharedFact) -> None:
        ...

    def list_facts(self) -> list[SharedFact]:
        ...

    def search(self, terms: list[str], limit: int = 5) -> list[SharedFact]:
        ...
```

- [ ] **Step 4: Run test to verify it passes**

Run: `pytest tests/test_storage/test_shared_knowledge_store.py -v`
Expected: PASS

- [ ] **Step 5: Commit**

```bash
git add tests/test_storage/test_shared_knowledge_store.py src/writing_agent/storage/shared_knowledge_store.py src/writing_agent/controller/task.py
git commit -m "feat: add shared fact storage"
```

### Task 2: Add failing tests for librarian service

**Files:**
- Create: `tests/test_agents/test_librarian.py`
- Modify: `src/writing_agent/agents/librarian.py`

- [ ] **Step 1: Write the failing tests**

```python
def test_librarian_ingests_findings_into_shared_store(tmp_path: Path) -> None:
    store = SharedKnowledgeStore(tmp_path / "library.db")
    store.initialize_schema()
    librarian = LibrarianAgent(shared_store=store)

    librarian.ingest_research(plan, research)

    facts = store.list_facts()
    assert len(facts) == 1
    assert facts[0].source_url == "https://example.com/report"


def test_librarian_finds_relevant_facts(tmp_path: Path) -> None:
    store = SharedKnowledgeStore(tmp_path / "library.db")
    store.initialize_schema()
    librarian = LibrarianAgent(shared_store=store)
    librarian.ingest_research(plan, research)

    facts = librarian.find_relevant_facts(
        topic="AI writing trends",
        title="AI Writing Trends in 2026",
        key_points=["enterprise adoption"],
        limit=5,
    )

    assert len(facts) == 1
```

- [ ] **Step 2: Run test to verify it fails**

Run: `pytest tests/test_agents/test_librarian.py -v`
Expected: FAIL because librarian is still a placeholder

- [ ] **Step 3: Write minimal implementation**

```python
class LibrarianAgent:
    def __init__(self, shared_store: SharedKnowledgeStore) -> None:
        self.shared_store = shared_store

    def ingest_research(self, plan: PlanResult, research: ResearchResult) -> None:
        ...

    def find_relevant_facts(self, topic: str, title: str, key_points: list[str], limit: int = 5) -> list[SharedFact]:
        ...
```

- [ ] **Step 4: Run test to verify it passes**

Run: `pytest tests/test_agents/test_librarian.py -v`
Expected: PASS

- [ ] **Step 5: Commit**

```bash
git add tests/test_agents/test_librarian.py src/writing_agent/agents/librarian.py
git commit -m "feat: add librarian shared fact service"
```

### Task 3: Add failing agent tests for researcher ingestion and writer retrieval

**Files:**
- Modify: `tests/test_agents/test_researcher.py`
- Modify: `tests/test_agents/test_writer.py`
- Modify: `src/writing_agent/agents/researcher.py`
- Modify: `src/writing_agent/agents/writer.py`
- Modify: `src/writing_agent/llm/prompts/writer.py`

- [ ] **Step 1: Write the failing tests**

```python
def test_researcher_ingests_shared_facts_after_success() -> None:
    librarian = Mock()
    agent = ResearcherAgent(..., librarian=librarian)

    agent.run(plan)

    librarian.ingest_research.assert_called_once()


def test_writer_includes_shared_facts_in_prompt_context() -> None:
    librarian = Mock()
    librarian.find_relevant_facts.return_value = [
        SharedFact(...)
    ]
    agent = WriterAgent(..., librarian=librarian)

    agent.run(plan, research)

    prompt = llm_provider.generate.call_args.kwargs["prompt"]
    assert "Shared knowledge facts" in prompt
    assert "AI tools are mainstream." in prompt
```

- [ ] **Step 2: Run test to verify it fails**

Run: `pytest tests/test_agents/test_researcher.py tests/test_agents/test_writer.py -v`
Expected: FAIL because the agents do not accept or use librarian yet

- [ ] **Step 3: Write minimal implementation**

```python
class ResearcherAgent(BaseAgent):
    def __init__(..., librarian=None) -> None:
        ...
        self.librarian = librarian

    def run(self, plan: PlanResult) -> ResearchResult:
        ...
        if self.librarian is not None:
            self.librarian.ingest_research(plan, research)
        return research


class WriterAgent(BaseAgent):
    def __init__(..., librarian=None) -> None:
        ...
        self.librarian = librarian

    def run(self, plan: PlanResult, research: ResearchResult) -> str:
        shared_facts = []
        if self.librarian is not None:
            shared_facts = self.librarian.find_relevant_facts(...)
        system_prompt, prompt = build_writer_prompt(plan, research, shared_facts=shared_facts)
        ...
```

- [ ] **Step 4: Run test to verify it passes**

Run: `pytest tests/test_agents/test_researcher.py tests/test_agents/test_writer.py -v`
Expected: PASS

- [ ] **Step 5: Commit**

```bash
git add tests/test_agents/test_researcher.py tests/test_agents/test_writer.py src/writing_agent/agents/researcher.py src/writing_agent/agents/writer.py src/writing_agent/llm/prompts/writer.py
git commit -m "feat: connect shared fact library to agents"
```

### Task 4: Wire the shared library into runtime construction

**Files:**
- Modify: `src/writing_agent/storage/manager.py`
- Modify: `src/writing_agent/cli/commands/write.py`

- [ ] **Step 1: Write the failing integration expectation**

Use existing CLI/build tests or add a narrow assertion that the runtime builder can construct the pipeline with a shared store-backed librarian.

- [ ] **Step 2: Run test to verify it fails**

Run: `pytest tests/test_cli/test_write_command.py -v`
Expected: FAIL only if constructor wiring is incompatible

- [ ] **Step 3: Write minimal implementation**

```python
class StorageManager:
    def get_shared_library_path(self) -> Path:
        return self.settings.data_dir / "shared" / "library.db"

    def get_shared_knowledge_store(self) -> SharedKnowledgeStore:
        ...
```

Then instantiate one `LibrarianAgent` in `build_write_pipeline` and pass it to both `ResearcherAgent` and `WriterAgent`.

- [ ] **Step 4: Run test to verify it passes**

Run: `pytest tests/test_cli/test_write_command.py -v`
Expected: PASS

- [ ] **Step 5: Commit**

```bash
git add src/writing_agent/storage/manager.py src/writing_agent/cli/commands/write.py
git commit -m "feat: wire shared fact library into write pipeline"
```

### Task 5: Full verification and documentation check

**Files:**
- Modify: `docs/superpowers/specs/2026-04-15-stage6-shared-facts-design.md`
- Modify: `docs/superpowers/plans/2026-04-15-stage6-shared-facts.md`

- [ ] **Step 1: Run the focused test suite**

Run: `pytest tests/test_storage/test_shared_knowledge_store.py tests/test_agents/test_librarian.py tests/test_agents/test_researcher.py tests/test_agents/test_writer.py -v`
Expected: PASS

- [ ] **Step 2: Run the full test suite**

Run: `pytest tests -v`
Expected: PASS

- [ ] **Step 3: Check git status**

Run: `git status --short`
Expected: only intended tracked changes plus any pre-existing incidental files

- [ ] **Step 4: Commit**

```bash
git add docs/superpowers/specs/2026-04-15-stage6-shared-facts-design.md docs/superpowers/plans/2026-04-15-stage6-shared-facts.md
git commit -m "docs: add stage6 shared facts design and plan"
```
