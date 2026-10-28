# Decision Audit Log: 00099-evaluation-render-crashes-malformed-data-v1

PRD: `00099-evaluation-render-crashes-malformed-data-v1.md`
Started: 2026-10-28T08:01:33Z
Completed: 2026-10-28T08:01:33Z
Autonomous: 12  |  Deferred: 1  |  Doubts: 0

### [autonomous] 2026-10-28T08:01:33Z

**Decision**: R1/R3/R4/R5 (one defect, 3/3 in substance): _check_run_shape validates key presence only, so a non-list tasks, a non-object engine entry, a task without id, and a missing root started all still escape render as Python tracebacks

**Choice**: auto-fix (additive validation plus regressions)

**Rationale**: High but additive only: adds validation and tests, changes no signature, type or schema

### [autonomous] 2026-10-28T08:01:33Z

**Decision**: R2: the no-new-report-outputs must-have is pinned only after a prior successful render, so a never-rendered run dir is uncovered

**Choice**: auto-fix (add the never-rendered case)

**Rationale**: Low severity, additive test only, raised by two reviewers

### [autonomous] 2026-10-28T08:01:33Z

**Decision**: R6-R15: ten single-voice medium and low findings

**Choice**: discarded, recorded in the settled-decisions ledger

**Rationale**: single-voice Medium or Low is discarded by the Classification rule; each is ledgered so a re-raise is auto-dismissed next cycle

### [autonomous] 2026-10-28T08:01:33Z

**Decision**: Task-container fields and the root `started` stay unvalidated, so the must-have "validate the engine and task containers and fields needed by rendering before use" is only half met: the engine container gets its `id` check, but `{"engines":[{"id":"qwen"}],"tasks":[{}],"run_id":"x"}` escapes as KeyError 'id' at report.py:544 (probed: `_check_run_shape` returns None for `tasks:[{}]`), and a body missing `started` escapes as KeyError 'started' at report.py:284/307. Both reach the operator as tracebacks.

**Choice**: auto-fixed

**Rationale**: fixed by review-close

### [autonomous] 2026-10-28T08:01:33Z

**Decision**: The must-have "refused malformed data produces no new report outputs" is pinned only as "byte-identical after a prior successful render": `_run_json_cli_refusal` calls `_render(round_)` first, so no case proves a never-rendered run dir stays free of report.md/evidence.md/audit-queue.md. This matches the file's documented contract (test_report_audit.py:4), so it is a note, not a defect.

**Choice**: auto-fixed

**Rationale**: fixed by review-close

### [autonomous] 2026-10-28T08:01:33Z

**Decision**: `tasks` is checked for presence only, never for type: `_check_run_shape` accepts `{"engines":[],"tasks":3,"run_id":"x"}` (probed: returns None), and `render` then iterates it at report.py:544, raising TypeError through the CLI as a traceback — the exact defect class the PRD closes. The task contract spells this out ("`tasks` key is present and is a list") and the existing writer schema checks it at skills/use-qwen/scripts/eval_harness/records_domains.py:85. Add `isinstance(run["tasks"], list)` with a `tasks is not a list` detail plus a `'{"engines":[],"tasks":3,"run_id":"x"}'` row in RUN_JSON_WRONG_SHAPE.

**Choice**: auto-fixed

**Rationale**: fixed by review-close

### [autonomous] 2026-10-28T08:01:33Z

**Decision**: Must-have "Validate the engine and task containers" is unmet: `_check_run_shape` only checks `tasks` presence, never its type or element shape, so `{"engines":[{"id":"qwen"}],"tasks":3,"run_id":"r1"}` still escapes as `TypeError: 'int' object is not iterable` and `{"engines":[{"id":"q"}],"tasks":[{}],...}` as `KeyError: 'id'`, both with a full Python traceback through the CLI (reproduced at HEAD)

**Choice**: auto-fixed

**Rationale**: fixed by review-close

### [autonomous] 2026-10-28T08:01:33Z

**Decision**: Required field types remain unchecked. `{"engines":[],"tasks":null,"run_id":"r1"}` passes validation despite the explicit requirement that `tasks` be a list; engine `id` and `run_id` values also receive no type checks. Validate these fields against the writer contract and expand direct/CLI regressions to cover wrong types and non-object engine entries.

**Choice**: auto-fixed

**Rationale**: fixed by review-close

### [autonomous] 2026-10-28T08:01:33Z

**Decision**: R1 (high, cycle 2): _check_run_shape still leaves every run.json field except the per-task id and the root started unvalidated, so slug/repo/kind/config/versions/server omissions and wrong types still escape as CLI tracebacks

**Choice**: deferred to batch end as a cap-overflow record

**Rationale**: rework cap 2 reached with this finding unresolved; autopilot cap-check exited 0, so it is a pre-existing residual gap and not a regression introduced by the cycle-1 rework. Stop polishing, not the batch.

### [autonomous] 2026-10-28T08:01:33Z

**Decision**: R2, R3, R4, R5, R6 (cycle 2 medium/low tail: missing field-validation test cases, test_report_audit.py at 799 of 800 lines, an all-clear note, the untested non-object task-item branch, and the fail-first replay adjudication)

**Choice**: discarded, each appended to the settled-decisions ledger

**Rationale**: every row is single-voice [1/3] medium or low, which the decision gate discards and never turns into a task; R6's replay line is adjudicated as the PRD-mandated preservation control rather than a tautology. Ledgered so a re-raise is auto-dismissed next cycle.

### [autonomous] 2026-10-28T08:01:33Z

**Decision**: Carl (gemini) failed again with exit 1, monthly quota exceeded on the copilot backend

**Choice**: recorded as a one-off runtime failure; Carl not latched for the batch, not retried

**Rationale**: exit 1 is not the exit-4 permanent-unavailability contract, so the batch latch does not apply; a monthly quota does not recover within the cycle, so a retry would only burn a dispatch. Three reviewers produced usable output: the cycle is degraded, not invalid.

### [autonomous] 2026-10-28T08:01:33Z

**Decision**: The ledger auto-dismiss filter wrongly discarded Blake's cycle-2 high finding, matching it against cycle 1 R7 (engine id type, settled single-voice) when it is the same defect Alice raises as R1

**Choice**: dismissal recorded verbatim in the review file with the reason it is wrong; R1 reported as 2/3 consolidated but 3/3 substantively

**Rationale**: the --ledger-dismiss BLAKE filter matched on file proximity rather than on the settled issue. It changed no outcome (R1 is unresolved either way) but it understates the consensus on the finding that decided the cycle, so it is surfaced rather than left silent.

### [deferred] 2026-10-28T08:01:33Z

**Decision**: _check_run_shape validates only the per-task id key and the root started key, so every other run.json field render dereferences still escapes as a Python traceback through the CLI: a task missing slug, repo or kind (KeyError at report.py:150/296/298/329/430), a missing config, versions or server (KeyError at report.py:285/287/310/318), config as a list (AttributeError: list has no attribute items), a list-valued task id (TypeError: unhashable type at report.py:552), and a non-string engine id (TypeError in the join at report.py:308). The PRD must-have "validate the engine and task containers and fields needed by rendering before use" is therefore half met after two cycles. The writer contract for every one of these fields is already encoded at skills/use-qwen/scripts/eval_harness/records_domains.py:74 and render does not use it. Fix: require slug, repo and kind on each task, require config, versions and server as dicts, type-check the task id and the engine id, and add the matching RUN_JSON_WRONG_SHAPE rows.

**Rationale**: rework cap reached with this finding unresolved
