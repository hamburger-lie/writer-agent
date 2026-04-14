# Stage 4 Research Pipeline Design

## Summary

Stage 4 extends the existing Stage 3 core pipeline from `planner -> writer` to `planner -> researcher -> writer`. The new researcher stage performs real web search and real webpage scraping, then compresses those results into a structured `research.json` that the writer can consume safely and predictably.

This stage focuses on a production-shaped research path, not a stub. Search and scraping should use real integrations, with Serper as the primary search backend and Crawl4AI as the primary scraping backend.

## Goals

- Extend `writing-agent write "<topic>"` to execute `planner -> researcher -> writer`.
- Add a real `ResearcherAgent`.
- Add real `web_search` and `web_scraper` tool integrations.
- Write `research.json` into the task directory.
- Update writer input so it consumes structured research output, not raw web pages.
- Fail the whole pipeline if research fails, while preserving completed intermediate files.

## Non-Goals

- No `polisher`, `reviewer`, `publisher`, or `librarian` stage yet.
- No caching layer yet.
- No soft fallback to planner-to-writer on research failure.
- No separate `research` CLI command in this step.

## Architecture

### Pipeline shape

The Stage 4 pipeline becomes:

`topic -> planner(plan.json) -> researcher(research.json) -> writer(draft.md)`

### Tool boundaries

- `tools/web_search.py`
  - real search API integration
  - normalize results into a stable internal structure
- `tools/web_scraper.py`
  - real Crawl4AI integration
  - normalize scrape results into a stable internal structure
- `agents/researcher.py`
  - generate search queries
  - call search tool
  - de-duplicate and select URLs
  - call scraper
  - summarize scraped content into structured research output
- `controller/pipeline.py`
  - insert research stage between planner and writer
  - persist `research.json`
  - stop on research failure

This keeps external integration details out of the agent and pipeline layers.

## Data Model

### `ResearchResult`

The researcher output should be a typed model with these fields:

- `topic`
- `search_queries`
- `sources`
- `findings`
- `key_takeaways`
- `open_questions`

### `sources`

Each source should include:

- `title`
- `url`
- `snippet`
- `fetched_at`

### `findings`

Each finding should include:

- `claim`
- `evidence`
- `source_url`

This structure gives writer high-signal material without forcing it to read raw scraped pages.

## File Protocol

### `research.json`

The pipeline must persist structured research output as `research.json`. It becomes the explicit contract between researcher and writer and a debugging artifact when write quality is weak.

## Search and Scraping Flow

The research stage should follow this sequence:

1. Use planner `research_questions` plus topic to ask the LLM for concrete search queries.
2. Execute those queries via the real search tool.
3. De-duplicate URLs across queries.
4. Select the top URLs up to the configured limit.
5. Scrape the selected URLs via Crawl4AI.
6. Require a minimum amount of usable material.
7. Ask the LLM to summarize scraped content into `ResearchResult`.

## Failure Policy

This stage uses a strict failure mode:

- if search fails, fail the pipeline;
- if all scraping fails, fail the pipeline;
- if scraping succeeds for fewer than two sources, fail the pipeline;
- if structured research generation fails, fail the pipeline;
- preserve `plan.json` if research fails after planning;
- preserve `research.json` if writer fails after research.

## Writer Input Upgrade

The writer should now consume both `PlanResult` and `ResearchResult`. It should use:

- planner title and outline for structure;
- research key takeaways and findings for substance;
- source URLs for citation context when phrasing evidence-backed statements.

The writer should still output clean Markdown only.

## Prompt Strategy

`llm/prompts/researcher.py` should expose two prompt helpers:

- one for generating search queries from planner output;
- one for summarizing search and scrape results into structured research output.

The writer prompt should be upgraded to accept both plan and research.

## Testing Strategy

- `web_search` tests should mock HTTP and verify normalized result parsing.
- `web_scraper` tests should mock Crawl4AI integration points and verify normalized scrape results.
- `ResearcherAgent` tests should verify query generation, URL handling, and structured research output.
- pipeline tests should verify `research.json` is written and preserved on downstream failure.
- CLI tests should verify `write` still prints plan and draft previews after the new stage is inserted.

## Acceptance Criteria

- `writing-agent write "<topic>"` runs `planner -> researcher -> writer`.
- `research.json` is written on successful research.
- writer consumes structured research output.
- pipeline fails immediately on research failure.
- completed upstream files are preserved on downstream failure.
- regression tests for Stages 2 through 4 pass.
