# Stage 4 Research Pipeline Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Extend the Stage 3 core pipeline into a real `planner -> researcher -> writer` workflow with real search and real scraping, structured `research.json`, and strict research failure handling.

**Architecture:** Real external integrations live in `tools/web_search.py` and `tools/web_scraper.py`. `ResearcherAgent` orchestrates query generation, search, scraping, and structured research output, while `WritingPipeline` remains responsible for stage ordering, file writes, and stop-on-failure behavior.

**Tech Stack:** Python 3.11, Typer, Rich, httpx, Crawl4AI, pydantic, pytest

---

### Task 1: Add the Research Models

**Files:**
- Modify: `src/writing_agent/controller/task.py`
- Test: `tests/test_pipeline/test_task.py`

- [ ] **Step 1: Write the failing tests**

```python
from writing_agent.controller.task import ResearchFinding, ResearchResult, ResearchSource


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
```

- [ ] **Step 2: Run the tests to verify they fail**

Run: `pytest tests/test_pipeline/test_task.py -v`
Expected: FAIL because research models do not exist yet.

- [ ] **Step 3: Write the minimal implementation**

```python
class ResearchSource(BaseModel):
    title: str
    url: str
    snippet: str
    fetched_at: str


class ResearchFinding(BaseModel):
    claim: str
    evidence: str
    source_url: str


class ResearchResult(BaseModel):
    topic: str
    search_queries: list[str]
    sources: list[ResearchSource]
    findings: list[ResearchFinding]
    key_takeaways: list[str]
    open_questions: list[str]
```

- [ ] **Step 4: Run the tests to verify they pass**

Run: `pytest tests/test_pipeline/test_task.py -v`
Expected: PASS with the research schema in place.

### Task 2: Implement Real Search and Scrape Tool Boundaries

**Files:**
- Modify: `src/writing_agent/tools/web_search.py`
- Modify: `src/writing_agent/tools/web_scraper.py`
- Test: `tests/test_tools/test_web_search.py`
- Test: `tests/test_tools/test_web_scraper.py`

- [ ] **Step 1: Write the failing tests**

```python
from writing_agent.config import Settings
from writing_agent.tools.web_search import SearchResult, SerperSearchClient


def test_serper_search_client_parses_organic_results(httpx_mock) -> None:
    settings = Settings(DEEPSEEK_API_KEY="test-key", SEARCH_ENGINE="serper", SEARCH_API_KEY="search-key")
    httpx_mock.add_response(
        json={
            "organic": [
                {
                    "title": "Example",
                    "link": "https://example.com",
                    "snippet": "Example snippet",
                }
            ]
        }
    )

    client = SerperSearchClient(settings)
    results = client.search("ai writing trends")

    assert results == [
        SearchResult(title="Example", url="https://example.com", snippet="Example snippet")
    ]
```

- [ ] **Step 2: Run the tests to verify they fail**

Run: `pytest tests/test_tools/test_web_search.py tests/test_tools/test_web_scraper.py -v`
Expected: FAIL because the tool implementations do not exist yet.

- [ ] **Step 3: Write the minimal implementation**

```python
class SearchResult(BaseModel):
    title: str
    url: str
    snippet: str


class SerperSearchClient:
    def __init__(self, settings: Settings) -> None:
        self.settings = settings

    def search(self, query: str, limit: int | None = None) -> list[SearchResult]:
        response = httpx.post(
            "https://google.serper.dev/search",
            headers={"X-API-KEY": self.settings.search_api_key or "", "Content-Type": "application/json"},
            json={"q": query, "num": limit or self.settings.max_research_urls},
            timeout=self.settings.llm_timeout_seconds,
        )
        response.raise_for_status()
        data = response.json()
        return [
            SearchResult(title=item["title"], url=item["link"], snippet=item.get("snippet", ""))
            for item in data.get("organic", [])
        ]
```

```python
class ScrapeResult(BaseModel):
    url: str
    title: str
    markdown: str
    success: bool
    error: str | None = None
```

```python
class Crawl4AIScraper:
    async def scrape_many(self, urls: list[str]) -> list[ScrapeResult]:
        ...
```

- [ ] **Step 4: Run the tests to verify they pass**

Run: `pytest tests/test_tools/test_web_search.py tests/test_tools/test_web_scraper.py -v`
Expected: PASS with normalized search and scraping contracts covered.

### Task 3: Add the Researcher Agent

**Files:**
- Modify: `src/writing_agent/llm/prompts/researcher.py`
- Modify: `src/writing_agent/agents/researcher.py`
- Modify: `src/writing_agent/llm/prompts/writer.py`
- Modify: `src/writing_agent/agents/writer.py`
- Test: `tests/test_agents/test_researcher.py`
- Test: `tests/test_agents/test_writer.py`

- [ ] **Step 1: Write the failing tests**

```python
from unittest.mock import Mock

from writing_agent.agents.researcher import ResearcherAgent
from writing_agent.config import Settings
from writing_agent.controller.task import PlanResult, ResearchResult


def test_researcher_returns_typed_research_result() -> None:
    llm_provider = Mock()
    llm_provider.generate_json.side_effect = [
        {"queries": ["ai writing trends 2026", "enterprise ai content tools"]},
        {
            "topic": "AI writing trends",
            "search_queries": ["ai writing trends 2026"],
            "sources": [
                {
                    "title": "Example",
                    "url": "https://example.com",
                    "snippet": "Example snippet",
                    "fetched_at": "2026-04-14T00:00:00+00:00",
                }
            ],
            "findings": [
                {
                    "claim": "AI writing tools are mainstream.",
                    "evidence": "The article cites broad enterprise adoption.",
                    "source_url": "https://example.com",
                }
            ],
            "key_takeaways": ["AI tools are mainstream."],
            "open_questions": ["Which teams are adopting fastest?"],
        },
    ]
    search_client = Mock()
    search_client.search.return_value = [Mock(title="Example", url="https://example.com", snippet="Example snippet")]
    scraper = Mock()
    scraper.scrape_many.return_value = [Mock(url="https://example.com", title="Example", markdown="# Example", success=True, error=None)]

    agent = ResearcherAgent(
        settings=Settings(DEEPSEEK_API_KEY="test-key", SEARCH_ENGINE="serper", SEARCH_API_KEY="search-key"),
        sqlite_store=Mock(),
        vector_store=Mock(),
        llm_provider=llm_provider,
        search_client=search_client,
        scraper=scraper,
    )

    result = agent.run(
        PlanResult(
            topic="AI writing trends",
            audience="content strategists",
            goal="explain the landscape",
            title="AI Writing Trends in 2026",
            outline=["Overview", "Adoption"],
            key_points=["Tools are mainstream"],
            constraints=["Professional tone"],
            research_questions=["What use cases are growing fastest?"],
        )
    )

    assert isinstance(result, ResearchResult)
    assert result.findings[0].claim == "AI writing tools are mainstream."
```

- [ ] **Step 2: Run the tests to verify they fail**

Run: `pytest tests/test_agents/test_researcher.py tests/test_agents/test_writer.py -v`
Expected: FAIL because the researcher implementation and writer research-aware input do not exist.

- [ ] **Step 3: Write the minimal implementation**

```python
def build_research_query_prompt(plan: PlanResult) -> tuple[str, str]:
    ...


def build_research_summary_prompt(plan: PlanResult, search_queries: list[str], scraped_pages: list[ScrapeResult]) -> tuple[str, str]:
    ...
```

```python
class ResearcherAgent(BaseAgent):
    def __init__(..., search_client, scraper) -> None:
        ...

    def run(self, plan: PlanResult) -> ResearchResult:
        query_payload = self.llm_provider.generate_json(...)
        queries = query_payload["queries"]
        search_results = []
        for query in queries:
            search_results.extend(self.search_client.search(query))
        urls = self._dedupe_urls(search_results)
        scraped = self.scraper.scrape_many(urls[: self.settings.max_research_urls])
        successful = [item for item in scraped if item.success]
        if len(successful) < 2:
            raise RuntimeError("Not enough successful research sources.")
        summary_payload = self.llm_provider.generate_json(...)
        return ResearchResult.model_validate(summary_payload)
```

- [ ] **Step 4: Run the tests to verify they pass**

Run: `pytest tests/test_agents/test_researcher.py tests/test_agents/test_writer.py -v`
Expected: PASS with typed research output and writer compatibility.

### Task 4: Upgrade the Pipeline and CLI

**Files:**
- Modify: `src/writing_agent/controller/pipeline.py`
- Modify: `src/writing_agent/cli/commands/write.py`
- Test: `tests/test_pipeline/test_pipeline.py`
- Test: `tests/test_cli/test_write_command.py`

- [ ] **Step 1: Write the failing tests**

```python
def test_pipeline_writes_research_before_draft(tmp_path: Path) -> None:
    ...
    assert result.task.research_file.exists()
```

- [ ] **Step 2: Run the tests to verify they fail**

Run: `pytest tests/test_pipeline/test_pipeline.py tests/test_cli/test_write_command.py -v`
Expected: FAIL because the pipeline has no research stage yet.

- [ ] **Step 3: Write the minimal implementation**

```python
task.current_stage = PipelineStage.RESEARCHER
research = self.researcher.run(plan)
task.research_file.write_text(...)
self.researcher.record_task_history(...)
draft = self.writer.run(plan, research)
```

- [ ] **Step 4: Run the tests to verify they pass**

Run: `pytest tests/test_pipeline/test_pipeline.py tests/test_cli/test_write_command.py -v`
Expected: PASS with the three-stage pipeline in place.

### Task 5: Run Regression and Push the Update

**Files:**
- Test: `tests/test_tools/test_web_search.py`
- Test: `tests/test_tools/test_web_scraper.py`
- Test: `tests/test_agents/test_researcher.py`
- Test: `tests/test_pipeline/test_pipeline.py`
- Test: `tests/test_cli/test_write_command.py`

- [ ] **Step 1: Run the Stage 4 verification suite**

Run: `pytest tests/test_tools/test_web_search.py tests/test_tools/test_web_scraper.py tests/test_agents/test_researcher.py tests/test_pipeline/test_pipeline.py tests/test_cli/test_write_command.py -v`
Expected: PASS with real research boundaries covered.

- [ ] **Step 2: Run the full regression suite**

Run: `pytest tests -v`
Expected: PASS across Stages 2, 3, and 4.

- [ ] **Step 3: Commit and push the update**

Run:

```bash
git add .
git commit -m "feat: add researcher stage to writing pipeline"
git push
```

Expected: Stage 4 changes are published to the configured remote.
