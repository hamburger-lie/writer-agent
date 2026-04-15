# Stage 7 Auto Reflection Design

## Goal

Add one automatic reflection pass after each pipeline run so the system can turn recent execution outcomes into reusable lessons and, after repeated confirmation, promote stable lessons into agent rules.

## Scope

This stage only covers automatic reflection triggered once at the end of a pipeline run.

Included:
- Reflect after successful pipeline completion
- Reflect after pipeline failure when enough context exists
- Persist reflections in SQLite with recurrence counting
- Promote repeated reflections into rules after a threshold
- Keep the implementation small enough to fit the existing per-agent storage model

Excluded:
- Human edit reflection
- Shared cross-agent rule distribution
- Per-stage reflection
- Reflection-aware prompt injection changes beyond the agent's existing `load_rules()` behavior

## Architecture

The new flow is:

1. `WritingPipeline` finishes or fails
2. `AutoReflectionEngine` builds a structured prompt from available task context
3. The LLM returns a small JSON payload of candidate lessons
4. The engine stores each lesson in the reviewer agent's SQLite database
5. When the same lesson has been seen at least 3 times, it is promoted into an active reviewer rule

The reviewer store is the first persistence target because Stage 5 already established reviewer as the quality gate for the whole pipeline, and the current system only supports per-agent rule storage. This keeps Stage 7 incremental without inventing a shared rule bus.

## Data Model

### Reflection Output

The reflection prompt returns JSON with:

- `summary`: short recap of what happened
- `lessons`: list of lesson objects

Each lesson object contains:

- `reflection_text`: the reusable lesson
- `category`: short bucket such as `evidence`, `structure`, `tone`, or `process`
- `confidence`: float between 0 and 1

### Persistence Rules

Reflections are deduplicated by exact `reflection_text` inside the reviewer database.

When a lesson is seen again:
- increment `times_seen`
- update `task_id` and `trigger_context` to the most recent run context

When `times_seen >= 3` and the lesson has not yet been promoted:
- add an active rule with `source="auto_reflection"`
- use the lesson confidence and category
- mark the reflection row as `promoted_to_rule = true`

## Pipeline Integration

`WritingPipeline` gains an optional `auto_reflector` dependency.

Trigger behavior:
- Success: run reflection after `final.md` is written
- Failure: run reflection before re-raising the exception

The reflection context should include, when available:
- topic
- plan title and outline
- research takeaways count
- final review decision and issues
- failure stage and error message

Reflection failures must never mask the original pipeline result:
- if the main pipeline succeeds and reflection fails, log no extra file and still return success
- if the main pipeline fails and reflection also fails, re-raise the original pipeline exception

## Prompt Strategy

The prompt should bias toward small, reusable lessons rather than long postmortems.

Rules:
- return JSON only
- emit at most 3 lessons
- avoid topic-specific statements
- focus on improvements that can guide future reviewing and revision

## Testing

Add tests for:
- reflection deduplication and recurrence counting
- automatic rule promotion at the threshold
- reflection engine parsing and persistence
- pipeline success triggering reflection once
- pipeline failure triggering reflection once without replacing the original error

## Completion Criteria

Stage 7 is complete when:
- pipeline runs trigger one automatic reflection pass
- repeated lessons increase `times_seen` instead of creating duplicate rows
- repeated lessons promote into active rules after the configured threshold
- reflection tests and existing pipeline tests pass
