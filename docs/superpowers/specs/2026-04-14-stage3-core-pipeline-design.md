# Stage 3 Core Pipeline Design

## Summary

This design covers Stage 3 of the `writing-agent` project: a minimum viable `planner -> writer` pipeline implemented as a real orchestration layer rather than a temporary shortcut. The goal is to make `writing-agent write "<topic>"` create a task workspace, generate a structured plan, generate a Markdown draft, persist outputs to disk, and record execution history for both stages.

This stage intentionally stops before research, polishing, review, publishing, and reflection automation. It should create a stable core pipeline that later stages can extend by inserting additional agents into the same orchestration flow.

## Goals

- Make `writing-agent write "<topic>"` execute a real two-stage pipeline.
- Create a unique `task_id` and task workspace under `data/tasks/<task_id>/`.
- Generate `plan.json` from `PlannerAgent`.
- Generate `draft.md` from `WriterAgent`.
- Record planner and writer execution in their respective `task_history` tables.
- Show a concise terminal summary plus outline and draft preview.
- Preserve intermediate files when a stage fails.

## Non-Goals

- No `researcher`, `polisher`, `reviewer`, `publisher`, or `librarian` stages yet.
- No retry or automatic fallback from `deepseek-reasoner` to `deepseek-chat`.
- No automatic reflection writes in this stage.
- No resume support yet.
- No real vector retrieval dependency on the success path.

## Scope Decisions

### Execution boundary

The Stage 3 MVP is a formal pipeline, not a direct CLI-to-agent shortcut. `write` should call a pipeline controller, and the pipeline controller should own task creation, stage transitions, disk writes, and failure handling.

### Output behavior

The `write` command should both persist files and preview results in the terminal:

- write `plan.json`;
- write `draft.md`;
- print `task_id`, task directory, and output file paths;
- print the outline preview;
- print a short draft preview.

### Planner/writer structure

The planner must produce strongly structured JSON. The writer must consume structured plan data but may generate flexible Markdown prose. This keeps the planner suitable for future researcher handoff while allowing the writer to produce natural output.

### Failure behavior

If planner fails, the pipeline must stop immediately and preserve the task directory. If writer fails, the pipeline must stop immediately and preserve `plan.json`. No silent fallback or placeholder output should be generated.

## Architecture

Stage 3 introduces five collaborating units.

### 1. Task model

`src/writing_agent/controller/task.py` defines the canonical pipeline task state and runtime file paths. It should hold enough information for orchestration, file writes, and CLI reporting without embedding business logic.

This model should capture:

- task identity;
- topic;
- lifecycle status;
- current stage;
- task directory;
- known output paths;
- timestamps.

### 2. Planner agent

`src/writing_agent/agents/planner.py` converts a topic into a structured writing plan. Its job is not to produce prose. It should request JSON from the LLM provider, validate the result against the plan schema, and return a typed object.

Planner output needs to be stable enough to support:

- task serialization to `plan.json`;
- future researcher handoff via `research_questions`;
- future orchestration decisions without reparsing free-form text.

### 3. Writer agent

`src/writing_agent/agents/writer.py` converts a structured plan into Markdown. It should not manage paths or task metadata. It only receives the structured plan object and returns a draft string.

The writer should be constrained by the plan content but not forced into a rigid output schema beyond clean Markdown structure.

### 4. Pipeline controller

`src/writing_agent/controller/pipeline.py` is the orchestration boundary. It should:

- create the task model and task directory;
- invoke planner;
- persist planner output;
- record planner history;
- invoke writer;
- persist draft output;
- record writer history;
- update task status and stage transitions;
- stop on failure while preserving any finished outputs.

This is the long-term insertion point for future stages.

### 5. CLI surface

`src/writing_agent/cli/commands/write.py` should become a thin user-facing entrypoint. It must:

- load settings;
- invoke the pipeline;
- print a readable summary;
- display outline and draft previews;
- surface pipeline failures cleanly.

It should not contain orchestration logic.

## Data Model

### `PipelineTask`

The task model should include at least:

- `task_id`
- `topic`
- `status`
- `current_stage`
- `created_at`
- `updated_at`
- `task_dir`
- `plan_file`
- `draft_file`

Recommended statuses:

- `pending`
- `running`
- `completed`
- `failed`

Recommended stages for Stage 3:

- `planner`
- `writer`

The model should support easy serialization for future diagnostics but does not need to be fully persisted as its own file yet.

### `PlanResult`

The planner output should be a typed model with fields:

- `topic`
- `audience`
- `goal`
- `title`
- `outline`
- `key_points`
- `constraints`
- `research_questions`

Field intent:

- `outline` is an ordered list of section headings.
- `key_points` captures must-cover arguments or facts.
- `constraints` captures tone, exclusions, or style limits.
- `research_questions` is generated now for future Stage 4 use, even though it is not executed yet.

This object should map directly to `plan.json`.

## File Protocol

### `plan.json`

Planner output must be written as structured JSON. The output file should be deterministic, machine-readable, and stable enough for later stages to consume directly.

This file is the contract between:

- planner and writer in Stage 3;
- planner and researcher in Stage 4;
- orchestration and debugging workflows later on.

### `draft.md`

Writer output must be plain Markdown. Minimum structure:

- a level-1 title;
- a short introduction;
- body sections corresponding to the planner outline;
- a conclusion.

The writer should cover the planner’s title, outline, key points, and constraints, but the prose itself may remain flexible.

## Prompt Strategy

Prompt construction should move into dedicated prompt helpers instead of being embedded directly inside agent classes.

### Planner prompt

`src/writing_agent/llm/prompts/planner.py` should expose a helper such as `build_planner_prompt(topic)` or `build_planner_messages(topic)`.

The prompt should instruct the model to:

- act as a planning specialist;
- define audience and goal;
- produce a clear article title;
- create an ordered outline;
- produce key points and constraints;
- return valid JSON only.

### Writer prompt

`src/writing_agent/llm/prompts/writer.py` should expose a helper such as `build_writer_prompt(plan)`.

The prompt should instruct the model to:

- write a complete Markdown draft from the structured plan;
- preserve the outline structure;
- cover the listed key points;
- obey constraints;
- return Markdown only, not JSON or commentary.

This keeps prompts maintainable and consistent with future agents.

## Control Flow

The Stage 3 pipeline should follow this sequence:

1. CLI receives `topic`.
2. Pipeline creates a new `PipelineTask`.
3. Task status becomes `running`.
4. Pipeline invokes planner.
5. Planner returns `PlanResult`.
6. Pipeline writes `plan.json`.
7. Pipeline records planner history.
8. Pipeline invokes writer with `PlanResult`.
9. Writer returns Markdown draft.
10. Pipeline writes `draft.md`.
11. Pipeline records writer history.
12. Task status becomes `completed`.
13. CLI prints summary and previews.

Failure path:

- on planner failure, mark task `failed`, preserve task directory, and exit;
- on writer failure, preserve `plan.json`, mark task `failed`, and exit.

## History Recording

Each successful `write` invocation should add two `task_history` rows:

- planner history row:
  - input summary: topic;
  - output summary: title and outline summary;
  - status: success or failed.
- writer history row:
  - input summary: plan title and outline summary;
  - output summary: draft title and brief summary;
  - status: success or failed.

If token usage data is unavailable, it can remain empty for now.

## Error Handling

Stage 3 should remain explicit and conservative.

- planner JSON parse or schema validation failures should fail the task immediately;
- writer generation failures should fail the task immediately;
- disk write failures should surface the file path involved;
- history write failures should be surfaced rather than silently ignored;
- CLI errors should be readable and preserve any successfully written outputs.

## Testing Strategy

### Planner tests

Test that planner:

- requests structured JSON;
- converts the LLM JSON output into a typed plan result;
- fails clearly on invalid planner output.

Mock `LLMProvider.generate_json` so tests exercise the agent contract instead of the live API.

### Writer tests

Test that writer:

- receives a `PlanResult`;
- builds the expected prompt inputs;
- returns Markdown text.

Mock `LLMProvider.generate` so tests stay local and deterministic.

### Pipeline tests

Test that the pipeline:

- creates task directories;
- writes `plan.json`;
- writes `draft.md`;
- updates task status correctly;
- records planner and writer history;
- preserves intermediate files when later stages fail.

### CLI tests

Test that `writing-agent write "<topic>"`:

- exits successfully on a mocked happy path;
- prints task ID and output paths;
- shows outline preview;
- shows draft preview;
- surfaces failures cleanly.

## Implementation Order

The implementation should proceed in this order:

1. `src/writing_agent/controller/task.py`
2. `src/writing_agent/llm/prompts/planner.py`
3. `src/writing_agent/llm/prompts/writer.py`
4. `src/writing_agent/agents/planner.py`
5. `src/writing_agent/agents/writer.py`
6. `src/writing_agent/controller/pipeline.py`
7. `src/writing_agent/cli/commands/write.py`
8. tests

This order keeps contracts clear before wiring orchestration.

## Acceptance Criteria

Stage 3 is complete when all of the following are true:

- `writing-agent write "<topic>"` runs a real `planner -> writer` pipeline;
- a unique task directory is created under `data/tasks/<task_id>/`;
- `plan.json` is written and matches the structured planner schema;
- `draft.md` is written as readable Markdown;
- planner and writer each write a `task_history` row;
- the CLI prints task metadata, outline preview, and draft preview;
- failures stop immediately and preserve already-written files;
- the corresponding tests pass locally.

## Open Follow-Up

Stage 4 can extend this design by attaching `researcher` after planner, consuming `research_questions`, and enriching the writer input with gathered materials without changing the core orchestration model.
