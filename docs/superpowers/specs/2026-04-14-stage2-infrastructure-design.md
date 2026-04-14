# Stage 2 Infrastructure Design

## Summary

This design covers Stage 2 of the `writing-agent` project: foundational infrastructure only. The scope is intentionally limited to configuration management, per-agent SQLite storage, initialization workflows, a shared storage manager, and stable interfaces for LLM and vector backends.

The goal of this stage is to make local infrastructure real and testable while keeping external-service integrations replaceable. After this stage, the project should be able to initialize its working directories and databases, validate configuration with clear pass/warn/fail semantics, and provide reusable abstractions for later agent and pipeline work.

## Goals

- Make `config + SQLite` production-like and directly usable.
- Add `writing-agent init` to create directories, databases, metadata, and startup diagnostics.
- Add `writing-agent config show` to display resolved configuration and validation status.
- Keep `ChromaDB + DeepSeek` behind stable interfaces so future stages can plug them in without changing callers.
- Establish test coverage for the core infrastructure layer.

## Non-Goals

- No end-to-end writing pipeline yet.
- No real research crawling or search integration yet.
- No agent-specific business logic for planner, writer, reviewer, or other roles.
- No full ChromaDB or DeepSeek dependency on the critical path for initialization.

## Scope Decisions

### Completion model

This stage uses a mixed implementation strategy:

- `config` and `SQLite` are fully implemented and runnable.
- `StorageManager` and `BaseAgent` use the real configuration and SQLite layers.
- `VectorStore` and `LLMProvider` expose real interfaces, configuration awareness, and clear errors, but do not need to be fully integrated into the active workflow.

### Initialization policy

`writing-agent init` should:

- create the standard project data directories;
- create all six agent directories;
- create each agent SQLite database with a shared schema;
- create per-agent `chroma/` directories even if vector storage is not enabled yet;
- initialize base metadata for every agent;
- validate environment configuration and surface pass/warn/fail results.

### Validation policy

Configuration validation follows a layered rule set:

- `DEEPSEEK_API_KEY` is a core required setting and must block initialization when missing.
- `SEARCH_API_KEY` is required only when a search engine is explicitly configured.
- `WHITEPAPER_API_URL` is optional and should only emit a warning when absent.
- Missing optional integrations must not block local infrastructure setup.

## Architecture

Stage 2 introduces five infrastructure units with clean boundaries.

### 1. Configuration

`src/writing_agent/config.py` is the single source of truth for settings. It is responsible for:

- loading values from environment variables and `.env`;
- resolving project-relative paths such as `DATA_DIR`;
- exposing typed settings to the rest of the application;
- reporting validation results in a structured way suitable for CLI output.

The configuration layer should distinguish between raw configuration loading and semantic validation. This keeps object construction simple while allowing commands like `init` and `config show` to present detailed diagnostics.

### 2. SQLite storage

`src/writing_agent/storage/schema.py` and `src/writing_agent/storage/sqlite_store.py` define the persistent local memory foundation. Every agent gets its own database file, but all agent databases share the same schema and lifecycle rules.

The SQLite layer is responsible for:

- creating tables if they do not exist;
- enabling WAL mode;
- providing lightweight CRUD helpers for metadata, rules, task history, and reflections;
- insulating callers from SQL details.

### 3. Storage manager

`src/writing_agent/storage/manager.py` owns filesystem layout and store provisioning. It gives the rest of the system a single place to ask for:

- the canonical paths for a given agent;
- the `SQLiteStore` for that agent;
- the `VectorStore` placeholder for that agent;
- full initialization of the shared project data layout.

This prevents CLI commands and agents from reimplementing path logic.

### 4. Backend interfaces

`src/writing_agent/storage/vector_store.py` and `src/writing_agent/llm/provider.py` define stable contracts for later stages.

The vector layer should support:

- `initialize()`
- `add_documents(...)`
- `query(...)`
- `delete(...)`

The LLM layer should support:

- `generate(...)`
- `generate_json(...)`
- `validate_config()` or `healthcheck()`

At this stage, these modules should be importable, typed, and safe to call in a controlled way. When the underlying backend is not ready, they should fail with explicit, domain-specific exceptions rather than vague runtime errors.

### 5. CLI surface

`src/writing_agent/cli/app.py` and dedicated command modules expose the infrastructure to users. Stage 2 requires at least:

- `writing-agent init`
- `writing-agent config show`

The CLI should give useful, readable feedback and should be the primary way to verify this stage manually.

## Data Model

Each agent database uses the same schema with isolated data files.

### `rules`

Purpose: store persistent writing or operational rules.

Fields:

- `id`
- `rule_text`
- `source`
- `confidence`
- `category`
- `created_at`
- `updated_at`
- `is_active`

### `task_history`

Purpose: track execution history for future observability and reflection.

Fields:

- `id`
- `task_id`
- `task_type`
- `input_summary`
- `output_summary`
- `status`
- `duration_ms`
- `token_usage_json`
- `created_at`

### `reflections`

Purpose: capture repeated lessons and promote them into future rules.

Fields:

- `id`
- `task_id`
- `reflection_text`
- `trigger_context`
- `times_seen`
- `promoted_to_rule`
- `created_at`

### `metadata`

Purpose: store lightweight agent-level configuration and migration markers.

Fields:

- `key`
- `value`
- `updated_at`

## Initialization Data

During `writing-agent init`, each agent database must receive base metadata entries:

- `agent_name`
- `agent_role`
- `db_schema_version`
- `initialized_at`

These values support future migrations, diagnostics, and debugging without requiring schema inspection.

## Directory Layout

Stage 2 initialization must ensure the following structure exists under the configured `DATA_DIR`:

```text
data/
├── agents/
│   ├── planner/
│   │   ├── planner.db
│   │   └── chroma/
│   ├── researcher/
│   │   ├── researcher.db
│   │   └── chroma/
│   ├── writer/
│   │   ├── writer.db
│   │   └── chroma/
│   ├── polisher/
│   │   ├── polisher.db
│   │   └── chroma/
│   ├── reviewer/
│   │   ├── reviewer.db
│   │   └── chroma/
│   └── librarian/
│       ├── librarian.db
│       └── chroma/
├── shared/
│   └── chroma/
├── tasks/
└── exports/
```

## Core Interfaces

### `StorageManager`

Expected responsibilities:

- initialize the full storage layout;
- return canonical paths for an agent;
- return the agent-specific `SQLiteStore`;
- return the agent-specific `VectorStore`.

Recommended public methods:

- `initialize()`
- `get_agent_paths(agent_name)`
- `get_sqlite_store(agent_name)`
- `get_vector_store(agent_name)`

### `SQLiteStore`

Expected responsibilities:

- initialize schema;
- manage metadata;
- add and query foundational records.

Recommended public methods:

- `initialize_schema()`
- `upsert_metadata(key, value)`
- `get_metadata(key)`
- `list_active_rules()`
- `add_rule(...)`
- `add_task_history(...)`
- `add_reflection(...)`

Implementation constraints:

- use `sqlite3`;
- enable WAL mode;
- use `sqlite3.Row` for row access;
- commit writes automatically;
- keep schema versioning explicit.

### `VectorStore`

Expected responsibilities:

- own the future vector backend boundary;
- support initialization and future CRUD semantics;
- fail clearly when real vector capabilities are not yet enabled.

Recommended behavior:

- initialization may succeed as a placeholder;
- mutating or query operations may raise `VectorStoreNotReadyError` until the backend is wired in.

### `LLMProvider`

Expected responsibilities:

- centralize model invocation behavior;
- normalize DeepSeek-specific parameter differences;
- provide structured failures for config, transport, and parse errors.

Recommended behavior:

- accept model selection explicitly or by default;
- strip unsupported parameters for reasoning models such as `deepseek-reasoner`;
- support structured JSON responses through a helper method;
- validate config separately from making a generation request.

### `BaseAgent`

Expected responsibilities:

- hold common dependencies;
- expose shared helper methods for rules, memory, history, and reflection;
- leave role-specific task execution to subclasses.

Recommended shared methods:

- `load_rules()`
- `load_relevant_memory()`
- `record_task_history(...)`
- `record_reflection(...)`
- abstract `run(...)`

## Control Flow

### `writing-agent init`

1. Load settings from environment and `.env`.
2. Validate settings and collect pass/warn/fail diagnostics.
3. If a core required setting is missing, stop with a clear error summary.
4. Create the base storage directories.
5. For each of the six agents:
   - create the agent directory;
   - create the `chroma/` directory;
   - initialize the SQLite database schema;
   - write base metadata.
6. Create shared directories such as `shared/chroma`, `tasks`, and `exports`.
7. Print a success summary plus any non-blocking warnings.

### `writing-agent config show`

1. Load the resolved settings.
2. Run semantic validation.
3. Print the normalized configuration values.
4. Print the validation report grouped into pass, warning, and error items.

## Error Handling

Stage 2 should favor explicit failures over hidden behavior.

- Invalid or missing core configuration should stop `init`.
- Optional integration gaps should be warnings, not silent skips.
- SQLite initialization errors should surface the affected agent and database path.
- Placeholder vector and LLM backends should fail with named exceptions that tell the caller what is not ready.
- CLI commands should convert internal exceptions into readable terminal output.

## Testing Strategy

The initial test suite should cover infrastructure behavior rather than external services.

### Configuration tests

- loads defaults correctly;
- resolves `DATA_DIR` deterministically;
- reports missing `DEEPSEEK_API_KEY` as blocking;
- reports optional integration gaps as warnings.

### SQLite tests

- creates all tables;
- supports metadata upsert and retrieval;
- inserts rules, task history, and reflections correctly;
- returns active rules only.

### Storage manager tests

- creates the expected directory structure;
- creates six agent databases;
- creates shared directories;
- writes initialization metadata.

### CLI tests

- `writing-agent init` succeeds with valid configuration;
- `writing-agent init` fails with missing core configuration;
- `writing-agent config show` displays resolved values and diagnostics.

### Backend boundary tests

- `VectorStore` placeholder raises the expected not-ready exception for unsupported operations;
- `LLMProvider` validation and parameter normalization behave as designed without depending on live APIs.

## Implementation Order

The implementation should proceed in this order:

1. `config.py`
2. `storage/schema.py`
3. `storage/sqlite_store.py`
4. `storage/manager.py`
5. `storage/vector_store.py`
6. `llm/provider.py`
7. `agents/base.py`
8. CLI command wiring for `init` and `config show`
9. tests

This order makes local state and validation real before wiring higher-level abstractions.

## Acceptance Criteria

Stage 2 is complete when all of the following are true:

- `writing-agent init` creates the full expected directory layout;
- all six agent databases exist and share the expected schema;
- each database contains initialization metadata;
- `writing-agent config show` displays resolved configuration and validation results;
- missing `DEEPSEEK_API_KEY` blocks initialization;
- missing optional integrations only produce warnings;
- `StorageManager`, `BaseAgent`, `LLMProvider`, and `VectorStore` expose stable reusable interfaces;
- tests for the above behavior pass locally.

## Open Follow-Up

Stage 3 can build on this foundation by implementing the first minimal workflow, most likely planner-led orchestration and a basic writer path, without needing to redesign storage or configuration boundaries.
