# Stage 5 Polish And Review Loop Design

## Summary

Stage 5 extends the writing pipeline from `planner -> researcher -> writer` to `planner -> researcher -> writer -> polisher -> reviewer`, with a structured review loop that can send the draft back to the polisher for up to two additional revision rounds.

The reviewer must return strict JSON so the pipeline can reliably decide whether the article passes, fails, or needs another polish cycle. When review passes, the accepted text is written to `final.md`.

## Goals

- Add a real `PolisherAgent`.
- Add a real `ReviewerAgent`.
- Add structured `review.json`.
- Support review-driven revision loops with a maximum of two retries.
- Write `polished.md`, `review.json`, and `final.md`.
- Keep the loop inside the pipeline, not in the CLI.

## Non-Goals

- No publishing integration yet.
- No automatic reflection updates yet.
- No writer rewrite loop; only the polisher revises after review feedback.

## Review Contract

The reviewer output should be strict JSON with:

- `decision`
- `summary`
- `issues`
- `revision_instructions`

`decision` should be either `pass` or `fail`.

Each issue should include:

- `severity`
- `title`
- `details`

This gives the pipeline a stable branching condition and gives the polisher concrete feedback to apply.

## File Protocol

- `draft.md`: writer output
- `polished.md`: latest polished version
- `review.json`: latest review result
- `final.md`: written only when review passes

The latest polished and review outputs should overwrite their previous versions for simplicity in Stage 5. The pipeline can still keep round metadata in memory for reporting.

## Loop Policy

1. Writer produces `draft.md`.
2. Polisher creates the first polished draft.
3. Reviewer evaluates the polished draft.
4. If review passes:
   - write `final.md`
   - mark task completed
5. If review fails:
   - pass review instructions back to the polisher
   - run another polish round
   - review again
6. Stop after at most two failed review loops.

If the maximum number of retries is reached without a pass, the pipeline should fail and preserve the latest `polished.md` and `review.json`.

## Testing Strategy

- task model tests for review schema and final output paths
- polisher tests for initial polish and feedback-driven polish
- reviewer tests for structured review parsing
- pipeline tests for pass path and fail-after-max-retries path
- CLI tests for final output reporting

## Acceptance Criteria

- the pipeline runs `planner -> researcher -> writer -> polisher -> reviewer`
- reviewer output is parsed as structured JSON
- failed review triggers polish-retry-review loop
- the loop stops after two retries
- `final.md` is written only on pass
- all tests pass locally
