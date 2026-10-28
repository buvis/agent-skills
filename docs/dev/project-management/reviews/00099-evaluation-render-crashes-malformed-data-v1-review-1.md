---
prd: docs/dev/project-management/prds/wip/00099-evaluation-render-crashes-malformed-data-v1.md
review: 1
date: 2026-10-28
head_sha: 8a281e215f40fb6f44bcccd7b0d6dc834e3923e5
codex_thread_id: 01a18156-660d-7f81-a363-caa9a5140a99
reviewers: alice,blake,bob
agents:
  alice: available
  blake: available
  bob: available
  carl: unavailable
dispatch_rows:
  bob: 1ae1c2f6
  carl: 8835a0f3
---

# Review: 00099-evaluation-render-crashes-malformed-data-v1

Diff range: `eba9191f03bdd731375822872be0bcb6571439f7..8a281e215f40fb6f44bcccd7b0d6dc834e3923e5`

codex_rung_guard: not fired

carl: runtime failure (exit 1, copilot backend `gemini-3.8-flash`: "You have exceeded your monthly quota"). Not latched for the batch: exit 1 is a one-off runtime failure, not the exit-4 permanent-unavailability contract. No retry: a monthly quota does not recover within the cycle. Three reviewers produced usable output; the cycle is degraded, not invalid.

pack: ok

## Consolidated Findings

| Ref | Consensus | Severity | Issue | File | Task | Found By |
|-----|-----------|----------|-------|------|------|----------|
| R1 | [2/3] | 🟠 | Task-container fields and the root `started` stay unvalidated, so the must-have "validate the engine and task containers and fields needed by rendering before use" is only half met: the engine container gets its `id` check, but `{"engines":[{"id":"qwen"}],"tasks":[{}],"run_id":"x"}` escapes as KeyError 'id' at report.py:544 (probed: `_check_run_shape` returns None for `tasks:[{}]`), and a body missing `started` escapes as KeyError 'started' at report.py:284/307. Both reach the operator as tracebacks. | skills/use-qwen/scripts/eval_harness/report.py:501 | 1 | ALICE, BLAKE |
| R2 | [2/3] | ⚪ | The must-have "refused malformed data produces no new report outputs" is pinned only as "byte-identical after a prior successful render": `_run_json_cli_refusal` calls `_render(round_)` first, so no case proves a never-rendered run dir stays free of report.md/evidence.md/audit-queue.md. This matches the file's documented contract (test_report_audit.py:4), so it is a note, not a defect. | skills/use-qwen/scripts/test_report_audit.py:681 | 1 | ALICE, BLAKE |
| R3 | [1/3] | 🟠 | `tasks` is checked for presence only, never for type: `_check_run_shape` accepts `{"engines":[],"tasks":3,"run_id":"x"}` (probed: returns None), and `render` then iterates it at report.py:544, raising TypeError through the CLI as a traceback — the exact defect class the PRD closes. The task contract spells this out ("`tasks` key is present and is a list") and the existing writer schema checks it at skills/use-qwen/scripts/eval_harness/records_domains.py:85. Add `isinstance(run["tasks"], list)` with a `tasks is not a list` detail plus a `'{"engines":[],"tasks":3,"run_id":"x"}'` row in RUN_JSON_WRONG_SHAPE. | skills/use-qwen/scripts/eval_harness/report.py:516 | 1 | ALICE |
| R4 | [1/3] | 🟠 | Must-have "Validate the engine and task containers" is unmet: `_check_run_shape` only checks `tasks` presence, never its type or element shape, so `{"engines":[{"id":"qwen"}],"tasks":3,"run_id":"r1"}` still escapes as `TypeError: 'int' object is not iterable` and `{"engines":[{"id":"q"}],"tasks":[{}],...}` as `KeyError: 'id'`, both with a full Python traceback through the CLI (reproduced at HEAD) | skills/use-qwen/scripts/eval_harness/report.py:518 | general | BLAKE |
| R5 | [1/3] | 🟠 | Required field types remain unchecked. `{"engines":[],"tasks":null,"run_id":"r1"}` passes validation despite the explicit requirement that `tasks` be a list; engine `id` and `run_id` values also receive no type checks. Validate these fields against the writer contract and expand direct/CLI regressions to cover wrong types and non-object engine entries. | skills/use-qwen/scripts/eval_harness/report.py:514 | 1 | BOB |
| R6 | [1/3] | 🟡 | `test_render_succeeds_on_a_well_formed_run_json` asserts only `result is None`, which `render`'s `-> None` signature guarantees; the assert cannot fail, and the clean path is already pinned by `test_main_render_returns_0_with_empty_stderr_on_a_clean_round` (test_report_audit.py:761) and by `_render` inside every refusal helper. Drop it, or assert the three report files' content. | skills/use-qwen/scripts/test_report_audit.py:652 | 1 | ALICE |
| R7 | [1/3] | 🟡 | Engine field validation is presence-only: `engine["id"]` type is unchecked, so a non-string id reaches `", ".join(engine_order)` and raises `TypeError: sequence item 0: expected str instance, int found` with a traceback (reproduced at HEAD) | skills/use-qwen/scripts/eval_harness/report.py:513 | general | BLAKE |
| R8 | [1/3] | 🟡 | The PRD says to derive required fields from the current writer, but `records.validate_record("run", ...)`/`records_domains._check_run` already encodes that writer contract (run_id, started, config, engines[].id/command, tasks[].id/slug/repo/kind, versions, server) and render ignores it in favour of a 3-key check, which is the "separate incompatible schema" the Solution section forbids | skills/use-qwen/scripts/eval_harness/records_domains.py:74 | general | BLAKE |
| R9 | [1/3] | 🟡 | Four syntax-control tests repeat two bodies, differing only between `"{trunc"` and `""`. Replace them with two parametrized tests, preserving their assertions. | skills/use-qwen/scripts/test_report_audit.py:610 | 1 | BOB |
| R10 | [1/3] | ⚪ | `test_render_rejects_a_truncated_run_json_with_the_malformed_refusal` is a literal clone of the pre-existing `test_render_rejects_a_malformed_run_json_naming_the_run_and_file` (test_report_audit.py:600) with `"{trunc"` swapped for `"{not json"`; the four syntax controls collapse into one `parametrize` over the three texts, matching the new RUN_JSON_WRONG_SHAPE idiom the same diff introduces. | skills/use-qwen/scripts/test_report_audit.py:610 | 1 | ALICE |
| R11 | [1/3] | ⚪ | The raising `fail()` closure departs from this module's established error idiom: `_audit_error` (report.py:79) returns the exception and its 11 callers write `raise _audit_error(...)`. A raising closure makes every `if ...: fail(...)` read as fall-through to humans and type checkers. | skills/use-qwen/scripts/eval_harness/report.py:503 | 1 | ALICE |
| R12 | [1/3] | ⚪ | `not isinstance(engine, dict)` is the one new validation branch with no test; the matrix covers only the `"id" not in engine` half. `pytest.param('{"engines":[3]}', "id", id="engine-not-an-object")` closes it. | skills/use-qwen/scripts/eval_harness/report.py:514 | 1 | ALICE |
| R13 | [1/3] | ⚪ | Fail-first replay adjudication (MECH line): 5 touched tests pass against pre-change code. Four are PRD-mandated preservation controls for the syntax path (two of them add CLI coverage that did not exist), so they are intentional, not tautological; the fifth is the redundant well-formed-render test flagged above. | skills/use-qwen/scripts/test_report_audit.py | general | ALICE, mech-check |
| R14 | [1/3] | ⚪ | Module docstring still lists refusal causes as "a missing or malformed run.json" and was not updated for the new wrong-shape refusal path | skills/use-qwen/scripts/eval_harness/report.py:7 | general | BLAKE |
| R15 | [1/3] | ⚪ | Pre-existing uncontrolled diagnostic survives: an `engines` list that omits an engine present in attempt directory names makes `engine_order.index(...)` raise a bare `ValueError: 'qwen' is not in list`, which the CLI prints as a refusal that names neither run.json nor the invalid field | skills/use-qwen/scripts/eval_harness/report.py:70 | general | BLAKE |

Consolidation note: the consolidator kept R3, R4 and R5 as separate rows because each names a different `file:line`, but all three describe one defect — `_check_run_shape` validates key presence without validating types or element shape. Substantively that row has 3/3 agreement, and the decision gate treats it as one finding.

Mechanical test checks: the one `[MECH]` line (5 touched tests pass against the pre-change code, `skills/use-qwen/scripts/test_report_audit.py`) is absorbed into R13, which adjudicates exactly those tests; `mech-check` is appended to its finders.

## Alice

See R1, R2, R3, R6, R10, R11, R12, R13 above. Alice probed `_check_run_shape` directly at HEAD and confirmed the escapes she reports.

R1: pass
R2: fail
R3: pass
R4: pass
R6: pass
R7: pass
R8: pass
R9: fail
R10: pass
R11: pass
R12: pass
R13: pass

## Blake

Blind lens, PRD-only. See R1, R2, R4, R7, R8, R14, R15 above. Blake reproduced each escape at HEAD without seeing the diff.

B1: fail
B2: pass
B3: pass
B4: pass
B5: fail
B6: pass
B7: pass
B8: pass
B9: pass
B10: fail
B11: pass
B12: pass
B13: pass
B14: pass
B15: fail
B16: pass
B17: pass
B18: pass
B19: pass

## Bob

Doubt lens + de-slop (codex, static-only sandbox, inlined prompt). See R5, R9 above.

FIX:
- R5 (unchecked required field types), R9 (four duplicated syntax-control tests)

VERIFY:
- (none)

KNOWN:
- (none)

R1: fail
R2: pass
R3: pass
R4: pass
R6: pass
R7: fail
R8: pass
R9: fail
R10: pass
R11: pass
R12: pass
R13: pass

D1: pass
D2: pass
D3: pass
D4: pass
D5: pass

## Carl

Carl: unavailable (copilot backend `gemini-3.8-flash`, exit 1 — monthly quota exceeded). No findings this cycle.

Verdict: 15 findings
Tests: 4024 passed, 9 skipped, 0 failed (suite run this cycle)
