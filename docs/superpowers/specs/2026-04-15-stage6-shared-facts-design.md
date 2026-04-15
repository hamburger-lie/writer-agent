# Stage 6 Shared Facts Design

## Goal

Add a shared fact library so research from previous runs can be reused by later writing runs without repeating the full discovery cost.

## Scope

This stage only covers the shortest useful loop:

- `researcher` writes shared facts after successful research
- `writer` reads relevant shared facts before drafting
- `librarian` owns storage and retrieval logic
- storage is SQLite-first

Out of scope:

- shared rule distribution
- Chroma-backed semantic retrieval
- standalone librarian CLI commands
- retroactive ingestion of old task artifacts

## Architecture

The new data flow is:

1. `researcher` completes `research.json`
2. `librarian` ingests normalized findings, sources, and takeaways into a shared SQLite database
3. `writer` asks `librarian` for relevant facts using the current topic, title, and key points
4. the writer prompt includes both current-run research and retrieved shared facts

This keeps the new logic off the main pipeline. The pipeline still orchestrates stages; the agents are responsible for using the shared knowledge service.

## Storage Model

Add one shared database at:

- `data/shared/library.db`

Add one table:

- `shared_facts`

Each row contains:

- `id`
- `topic`
- `title`
- `claim`
- `evidence`
- `source_url`
- `source_title`
- `source_snippet`
- `takeaway`
- `content_hash`
- `created_at`
- `updated_at`

`content_hash` is a deterministic hash of the normalized claim, evidence, and source URL and is used for deduplication.

## Librarian Responsibilities

`LibrarianAgent` is the service boundary for the shared fact library.

It provides:

- `ingest_research(plan, research)`  
  writes one shared fact row per research finding, pairing the finding with its matching source and a best-effort takeaway

- `find_relevant_facts(topic, title, key_points, limit=5)`  
  performs SQLite keyword matching against topic, title, claim, evidence, takeaway, and source title

The first version uses simple tokenized `LIKE` matching with result ordering by recency. This is intentionally basic and stable.

## Agent Integration

### Researcher

After building a valid `ResearchResult`, the researcher calls `librarian.ingest_research(...)`. Ingestion failure should not silently pass; this stage is part of the shared-library goal, so the run should fail if the shared fact write fails.

### Writer

Before building the writer prompt, the writer calls `librarian.find_relevant_facts(...)`. The returned facts are included as extra supporting context in the prompt. If no facts are found, the writer continues using only the current run's research.

## Failure Handling

- if shared fact ingestion fails, the researcher stage fails
- if shared fact lookup fails, the writer stage fails
- if lookup returns no matches, the writer still proceeds

## Testing

Add tests for:

- shared fact table initialization
- deduplicated ingestion by `content_hash`
- librarian retrieval returning relevant facts
- researcher calling ingestion after successful research
- writer including shared fact context in the prompt path

## Completion Criteria

Stage 6 is complete when:

- successful research writes normalized facts into `data/shared/library.db`
- repeated ingestion of the same research does not duplicate rows
- writer retrieves relevant shared facts and uses them in prompt construction
- tests for store, librarian, researcher, and writer pass
