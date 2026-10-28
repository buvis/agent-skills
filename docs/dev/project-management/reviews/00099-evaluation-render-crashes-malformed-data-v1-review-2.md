---
prd: docs/dev/project-management/prds/wip/00099-evaluation-render-crashes-malformed-data-v1.md
review: 2
date: 2026-10-28
head_sha: f5e160b121f9ea6747e0710f483ab5919c2fd861
codex_thread_id: 01a18156-660d-7f81-a363-caa9a5140a99
reviewers: alice,blake,bob
agents:
  alice: available
  blake: available
  bob: available
  carl: unavailable
dispatch_rows:
  bob: 88c7285c
  carl: b2c329e0
---

# Review: 00099-evaluation-render-crashes-malformed-data-v1 (cycle 2)

Diff range: `8a281e215f40fb6f44bcccd7b0d6dc834e3923e5..f5e160b121f9ea6747e0710f483ab5919c2fd861` (incremental: the cycle-1 rework commits only)

codex_rung_guard: not fired

carl: runtime failure (exit 1, copilot backend `gemini-3.8-flash`: "You have exceeded your monthly quota"). Same failure as cycle 1 and recorded the same way: exit 1 is a one-off runtime failure, not the exit-4 permanent-unavailability contract, so Carl is NOT latched for the batch. No retry: a monthly quota does not recover within the cycle. Three reviewers produced usable output; the cycle is degraded, not invalid.

pack: ok

Bob resumed his cycle-1 codex thread (`--resume-thread 01a18156-660d-7f81-a363-caa9a5140a99`), so his verdicts are stated against his own cycle-1 critique.

## Consolidated Findings

| Ref | Consensus | Severity | Issue | File | Task | Found By |
|-----|-----------|----------|-------|------|------|----------|
| R1 | [2/3] | 🟠 | `_check_run_shape` still validates only `id` per task and `started` at the root, so the rest of the fields render dereferences still escape as tracebacks through the CLI. This is the cycle-1 R1 defect ("task-container fields and fields needed by rendering") and the PRD must-have "validate the engine and task containers and fields needed by rendering before use". Probed on the r1 round with an otherwise valid run.json: a task without `slug` gives `KeyError 'slug'` (render reads it at report.py:150, 296, 329, 430), a task without `kind` gives `KeyError 'kind'` (report.py:329), a missing `config`, `versions` or `server` gives `KeyError` (report.py:285, 287, 310, 318), `config` as a list gives `AttributeError: 'list' object has no attribute 'items'`, and a list-valued task `id` gives `TypeError: unhashable type: 'list'` at report.py:552. A `repo` omission also escapes at report.py:298, going by the code read (not probed). Fix: in `_check_run_shape`, require `slug`, `repo` and `kind` on each task, require `config`, `versions` and `server` as dicts, and check the task `id` type (render formats it with `%d` at report.py:296). The writer contract for these fields is already encoded at skills/use-qwen/scripts/eval_harness/records_domains.py:74. Add the matching RUN_JSON_WRONG_SHAPE rows. | skills/use-qwen/scripts/eval_harness/report.py:524 | general | ALICE, BOB |
| R2 | [1/3] | 🟡 | Tests cover only the quoted evidence bodies plus a few extra id, tasks and started cases. No case for a missing or wrong-type `config`, `versions`, `server`, `slug`, `repo` or `kind`, or for wrong-type `id` values. That is why the gap above is not caught. | skills/use-qwen/scripts/test_report_audit.py:663 | general | BLAKE |
| R3 | [1/3] | ⚪ | test_report_audit.py is now 799 lines, one short of the 800-line limit, so the next added test breaches it. Split the run.json shape tests into their own module when the field-validation rows above are added. | skills/use-qwen/scripts/test_report_audit.py:799 | general | ALICE |
| R4 | [1/3] | ⚪ | Every body quoted in the accepted evidence (`[]`, `null`, `{}`, `{"engines":3}`, `{"engines":[{}],"tasks":[]}`, `{"engines":[{"id":"qwen"}]}`, `{"engines":[],"tasks":[]}`) is refused with a ValueError naming the run and run.json. The CLI wrapper at skills/use-qwen/scripts/run_eval_harness.py:84 prints `render refused: ...` and returns 1. `_check_run_shape` runs before any output write, and the existing syntax-error and audit paths are unchanged. These parts meet the spec. I did not run the tests (the suite result at HEAD is given). | skills/use-qwen/scripts/test_report_audit.py:703 | general | BLAKE |
| R5 | [1/3] | ⚪ | The new non-object task-item rejection is untested: `tasks:[{}]` exercises only the missing-key case. Add `tasks:[null]` to the existing direct/CLI matrix to cover the other branch. | skills/use-qwen/scripts/test_report_audit.py:671 | 2 | BOB |
| R6 | [1/3] | 🟡 | Fail-first replay (MECH line): 1 touched test passes against the pre-change code — `test_render_refusal_writes_no_output_files_on_a_never_rendered_run`. Alice adjudicated it: the base renderer already wrote nothing on refusal, so the test is the PRD-mandated preservation control cycle-1 R2 asked for, not a tautology. Recorded, not dropped. | skills/use-qwen/scripts/test_report_audit.py | general | mech-check |

Consolidation note: `consolidate_findings.py` merged Alice's `report.py:524` row with Bob's `report.py:521` row after suffix stripping (its own warning line), so R1 carries both voices.

Mechanical test checks: the one `[MECH]` line is R6. No consolidated row named that test file *and* that test, so it was added as its own row per the absorption rule rather than appended to an existing row's finders.

### Auto-dismissed (ledger)

- [BLAKE] 🟠 Render validation is incomplete. `_check_run_shape` checks only the root object, `engines`/`tasks` lists, the `id` key on each engine and task, and the presence of `run_id` and `started`. `render` then reads fields it never validates: `run["config"]`, `run["versions"]`, `run["server"]` (plus `server[key]` for each key in `records.SERVER_KEYS`), and `task["slug"]`, `task["repo"]`, `task["kind"]`. I ran `{"engines":[],"tasks":[],"run_id":"r1","started":"x"}` through the CLI. It printed a Python traceback ending in `KeyError: 'config'` at skills/use-qwen/scripts/eval_harness/report.py:285 instead of `render refused`. [...] The writer-contract validator `records.validate_record("run", ...)` already exists (skills/use-qwen/scripts/eval_harness/records_domains.py:74). It checks every field render needs, and render does not use it. | File: skills/use-qwen/scripts/eval_harness/report.py:501 — single-voice

**This dismissal is wrong and is recorded here so it is visible rather than silent.** The ledger entry it matched is cycle 1's R7 ("Engine field validation is presence-only: `engine["id"]` type is unchecked", report.py:513), settled as single-voice. Blake's cycle-2 row is not that finding: it is the same defect Alice raises as R1 above, found independently and blind. Substantively R1 has **3/3** agreement (ALICE, BLAKE, BOB), not 2/3. The dismissal changes no outcome — R1 is an unresolved 🟠 either way — but it understates the consensus on the one finding that decided this cycle, and it means the `--ledger-dismiss BLAKE` filter matched on file proximity rather than on the settled issue.

## Alice

See R1, R3 above. Alice probed `report.render` against mutated copies of the `r1` round's `run.json` in a scratch directory outside the repo, and confirmed each escape at HEAD.

Resolved from cycle 1, per Alice: R3, R4, R5 (`tasks` now checked for presence and `list` type, report.py:518, pinned by the `tasks-wrong-type`, `tasks-wrong-type-with-engine` and `tasks-null` rows); the `started` and per-task `id` halves of R1 (report.py:521, 526, pinned by `task-missing-id` and `missing-started`); R2 (`test_render_refusal_writes_no_output_files_on_a_never_rendered_run`, test_report_audit.py:731).

R1: pass
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

## Blake

Blind lens, PRD-only. See R2, R4 above, plus the auto-dismissed 🟠 (which is R1's defect, found blind). Blake reproduced each escape at HEAD through the CLI without seeing the diff, and did not rerun the suite (he was given the gate result).

B1: fail
B2: fail
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

Doubt lens + de-slop (codex, static-only sandbox, inlined prompt, cycle-1 thread resumed). See R1, R5 above.

FIX:
- R1 (cycle-1 R5 residual: `run_id` and task `id` still presence-only, no writer-type check), R5 (the new non-object task-item branch is untested)

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

Verdict: 6 findings
Tests: 4035 passed, 9 skipped, 0 failed (suite run this cycle)

Counts provenance (fail loud): `review-stage`'s gate run and a second independent `autopilot verify --gate-command "uv run pytest" --cycle 2` run both exited 0 and both reported `4035 passed, 9 skipped` in their logs, but the CLI's parser returned `Tests: counts unavailable (suite run this cycle, exit 0, no PASS/FAIL/SKIP/EXIT summary line)` for both, because this project's pytest summary line (`===== 4035 passed, 9 skipped, 236 warnings in 419.36s =====`) carries no `failed` token for the parser to match. The counts above were read from the gate logs (`docs/dev/tmp/gate-00099-c2.log:194` and `docs/dev/tmp/gate-f5e160b.log:194`), not from the parser, and `last-verification.json` was therefore not recorded (`"recorded": false`). The suite is green; the parser gap is a reporting defect in the counts extractor, not a test failure.
