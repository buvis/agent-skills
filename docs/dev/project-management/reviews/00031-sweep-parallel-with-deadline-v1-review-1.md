---
prd: docs/dev/project-management/prds/wip/00031-sweep-parallel-with-deadline-v1.md
review: 1
date: 2026-10-18
head_sha: 8a5540d4889b9fb719a163804f38e6dc426f963a
reviewers: alice,blake,bob,carl
agents:
  alice: available
  blake: available
  bob: available
  carl: available
dispatch_rows:
  bob: 348ed121
  carl: 0aa6979b
---

# Review: 00031-sweep-parallel-with-deadline-v1

Diff range: `8267e2c5a21cb95a80cb62457b2e20ad9063e3a9..8a5540d4889b9fb719a163804f38e6dc426f963a`

codex_rung_guard: not fired

## Review Summary

Reviewed: 6 completed tasks
PRDs checked: 00031-sweep-parallel-with-deadline-v1.md

### Agent Status

- Alice (consensus, Claude subagent): ✅ Available
- Blake (blind lens, Claude subagent): ✅ Available
- Bob (doubt lens + de-slop, codex): ✅ Available — **after one retry (inlined)**. His first run returned a sandbox refusal (`Review incomplete: the tool sandbox fails before file reads begin`) with every `R{n}` verdict `fail`; the one-retry budget was spent on the inlined-prompt dispatch, which produced a usable review. **Ledger caveat (fail loud):** the first run's dispatch row `79947d24` was closed `--outcome ok` before that refusal was read; it should have been `--outcome error --detail "lack-of-input"`. The row cannot be reopened, so the telemetry under-reports one failed codex dispatch for this cycle.
- Carl (UI/design, gemini via copilot): ✅ Available
- Eve: ⏸️ Disabled: resolved doubt reviewer is `codex`, and the codex doubt-roster guard did not fire (no task has a codex implementor attempt).

Notes:

- `pack: failed (engram pack exit 1: not inside a registered repo)` — this cycle's reviewers ran without the engram context pack (`(no pack available this cycle)` substituted). Degraded, not invalid.
- Consolidation ran via `consolidate_findings.py` (no settled-decisions ledger exists on cycle 1, so the `--ledger` flags were omitted). It merged two citation pairs after suffix stripping: row R1 (`test_sweep_main.py:803 ~ :783`) and row R3 (`test_sweep_scan.py:1456 ~ :275`). The R3 merge is loose — Alice's real-clock-flake finding and Blake's barrier-placement note are different observations sharing one file; both texts are preserved below.
- Carl additionally reported `uv run ruff check skills/sweep-fix skills/glean` → 23 errors, but did not file them as findings. `uv run ruff check` at repo configuration exits clean, so the project's lint gate is not failing; the per-path invocation picks up rules the project does not enforce.

## Consolidated Findings

| Ref | Consensus | Severity | Issue | File | Task | Found By |
|-----|-----------|----------|-------|------|------|----------|
| R1 | [3/4] | 🟡 | `skills/sweep-fix/scripts/test_sweep_main.py` is now 803 lines, over the 800-line limit. The diff added about 100 lines to a file that was about 702. Move the new deadline tests (or an older group) into a sibling test module. | skills/sweep-fix/scripts/test_sweep_main.py:803 | 5 | ALICE, BOB, CARL |
| R2 | [2/4] | 🟡 | `_collect_scan_results` rebuilds the deadline key inline with `repo["cwd"] if isinstance(repo, dict) else repo`. That duplicates `_repo_cwd_and_targets`, which the design says to reuse (key is `_repo_cwd_and_targets(repo)[0]`). Replace it with `str(_repo_cwd_and_targets(repo)[0])`. | skills/sweep-fix/scripts/sweep.py:314 | 4 | ALICE, BLAKE |
| R3 | [2/4] | ⚪ | `test_scan_deadline_budget_runs_from_scan_start_not_per_repo` has only about 0.3s of margin between `repo_a` finishing at 0.6s, the deadline at 1.0s and `repo_b` finishing at 1.3s. It runs against the real clock and can flake on a loaded CI runner. Widen the gaps (for example 1.0s, 2.0s and 3.0s) or patch the clock. (Merged with BLAKE's separate note that `test_scan_runs_repo_searches_concurrently` places its barrier at the `subprocess.run` boundary rather than stubbing `_scan_repo` — stricter than the spec, still binds to overlap.) | skills/sweep-fix/scripts/test_sweep_scan.py:1456 | 4 | ALICE, BLAKE |
| R4 | [1/4] | 🟡 | `test_scan_never_silently_drops_a_repo_whose_search_raises` is an either-or hedge. It returns early if `scan()` raises, and only otherwise asserts the repo is in `failed`. It also passes against the pre-change serial loop, so it pins no new behavior. Pick the one outcome the code has (the exception escapes, per the assumptions ledger) and assert it with `pytest.raises`. | skills/sweep-fix/scripts/test_sweep_scan.py:1338 | 1 | ALICE, mech-check |
| R5 | [1/4] | 🟡 | Unrelated formatting churn is in the diff: `skills/glean/scripts/glean.py` and `skills/glean/scripts/test_glean.py` (82 and 64 lines changed, including `re.I` to `re.IGNORECASE` and re-wrapped calls). It has nothing to do with PRD 00031, and the project capsule records it as pre-existing uncommitted work. Keep it out of this PRD's commit. | skills/glean/scripts/glean.py | general | ALICE |
| R6 | [1/4] | 🟡 | The existing `test_main_rejects_cap_of_zero` and `test_main_rejects_negative_cap` had their assertions edited. The task and design said they must keep passing unmodified, because the old `"cap"` substring check already covered them. The tightened assertion passes against the pre-change code (the old hardcoded message was already `--cap must be a positive integer`), so the fail-first replay flags both. Revert the edits, or keep them and say so as a deliberate scope addition. | skills/sweep-fix/scripts/test_sweep_main.py:438 | 5 | ALICE, mech-check |
| R7 | [1/4] | 🟡 | Success criterion "two `sweep.main` runs over the same fixture registry, each with explicit `--out`, write byte-identical reports" has no test. Ordering is covered only at `scan()` level. | skills/sweep-fix/scripts/test_sweep_main.py | general | BLAKE |
| R8 | [1/4] | 🟡 | `--deadline` is not a hard wall-clock ceiling for the process. After a deadline hit, `scan()` returns at once (`shutdown(wait=False, cancel_futures=True)`). Worker threads already running are still joined by the interpreter's exit hook. Process exit can then trail the deadline by up to the per-call 30s timeout. The `scan()` return is bounded, which is what the spec asks for. | skills/sweep-fix/scripts/sweep.py:385 | 4 | BLAKE |
| R9 | [1/4] | 🟡 | One-shot `repos` iterators silently lose all results: submission exhausts the iterator before collection iterates it again. | skills/sweep-fix/scripts/sweep.py:380 | 1 | BOB |
| R10 | [1/4] | 🟡 | Formatting expands `cmd_scan` to 54 lines, exceeding the 50-line limit. | skills/glean/scripts/glean.py:191 | general | BOB |
| R11 | [1/4] | 🟡 | Replace duplicate deadline rejection tests with pytest.mark.parametrize across 0 and -1 to cut lines under 800 | skills/sweep-fix/scripts/test_sweep_main.py:456 | 5 | CARL |
| R12 | [1/4] | ⚪ | `except FutureTimeoutError` in `_collect_scan_results` treats any `TimeoutError` as a deadline hit. On Python 3.11 and later this is the builtin `TimeoutError`. If a worker ever re-raised one through `future.result()`, it would be mislabelled as `DEADLINE_REASON`. `_scan_repo` catches `Exception` today, so this is latent. Raising the timeout check apart from the `result()` call would remove the ambiguity. | skills/sweep-fix/scripts/sweep.py:313 | 4 | ALICE |
| R13 | [1/4] | ⚪ | With the `_positive_int` factory, `int(value)` still raises a bare `ValueError` for input like `abc`. argparse then reports "invalid _parse value", where it used to say "invalid _positive_int value". Catch `ValueError` and raise `ArgumentTypeError(f"{flag_name} must be a positive integer")`, as the design docstring describes. | skills/sweep-fix/scripts/sweep.py:565 | 5 | ALICE |
| R14 | [1/4] | ⚪ | SKILL.md only gains `[--deadline N]` in the usage line. It does not say that the default is 300 seconds, that the deadline covers the whole sweep, or what the new `Partial:` line means in the report. This meets the PRD's literal wording, but a reader of the skill cannot learn what the flag does. | skills/sweep-fix/SKILL.md:38 | 5 | ALICE |
| R15 | [1/4] | ⚪ | Several tests go beyond the PRD's named ones: negative deadline, deadline passthrough to `scan`, `verify_control` not deadline-bound, real-clock deadline tests, and a no-Partial-line test. They are tests only, and the production code adds no extra flags or features. | skills/sweep-fix/scripts/test_sweep_main.py | general | BLAKE |
| R16 | [1/4] | ⚪ | Unrelated uncommitted working tree edits to glean bundled into review diff | skills/glean/scripts/glean.py:37 | general | CARL |
| R17 | [1/4] | 🟡 | 1 touched test(s) pass against the pre-change code: test_render_report_omits_partial_line_when_no_repo_hit_the_deadline | skills/sweep-fix/scripts/test_sweep_render_report.py | general | mech-check |
| R18 | [1/4] | 🟡 | 2 touched test(s) pass against the pre-change code: test_scan_waits_for_a_slow_repo_when_no_deadline_is_set, test_scan_never_silently_drops_a_repo_whose_search_raises | skills/sweep-fix/scripts/test_sweep_scan.py | general | mech-check |

The three `[MECH]` fail-first-replay lines from the context file are absorbed above: the `test_sweep_main.py` one onto R6 (same two tests), the other two as R17 and R18. The tautological-shape detector reported nothing.

No CRITICAL (🔴) and no HIGH (🟠) finding was raised by any lens.

## Alice

See the table above (rows R1-R6, R12-R14). Rubric verdicts:

R1: pass
R2: fail
R3: pass
R4: pass
R6: pass
R7: pass
R8: pass
R9: pass
R10: pass
R11: pass
R12: pass
R13: fail

## Blake

Blind lens, PRD-only prompt. Rows R2, R3, R7, R8, R15. He confirmed the thread pool, the deadline accounting, the CLI wiring, the `Partial:` line, the SKILL.md usage line and all five PRD-named tests, and ran `uv run pytest skills/sweep-fix/scripts -q`: 270 passed. Rubric verdicts:

B1: pass
B2: pass
B3: pass
B4: pass
B5: pass
B6: pass
B7: pass
B8: pass
B9: pass
B10: pass
B11: pass
B12: pass
B13: pass
B14: pass
B15: pass
B16: pass
B17: pass
B18: pass
B19: pass

## Bob

Doubt lens + de-slop, codex, after one retry (inlined). Rows R1, R9, R10.

FIX:
- Preserve iterator inputs — skills/sweep-fix/scripts/sweep.py:380 — Materialize `repos` once before submission; add a regression test using `iter(repos)`.
- Restore the function-size limit — skills/glean/scripts/glean.py:191 — Remove unnecessary formatting expansion within `cmd_scan`.
- Restore the file-size limit — skills/sweep-fix/scripts/test_sweep_main.py:783 — Move deadline CLI tests into a separate test module.

VERIFY:
- (none)

KNOWN:
- (none)

Rubric verdicts:

R1: fail
R2: pass
R3: pass
R4: fail
R6: pass
R7: pass
R8: pass
R9: fail
R10: fail
R11: pass
R12: fail
R13: fail

D1: pass
D2: pass
D3: pass
D4: pass
D5: pass

No verification-check queue was written for this cycle: Bob's VERIFY bucket is empty, and `source: "bob"` is reserved in any case.

## Carl

UI/design specialist, gemini via the copilot backend. Rows R1, R11, R16. He read the context and diff, re-ran `uv run pytest skills/sweep-fix/scripts`, `validate_skill.py skills/sweep-fix` and the full suite, and inspected the glean working-tree edits. Rubric verdicts:

R1: pass
R2: pass
R3: pass
R4: pass
R6: pass
R7: pass
R8: pass
R9: pass
R10: pass
R11: pass
R12: pass
R13: fail

Verdict: 18 findings
Tests: 3852 passed, 0 failed, 6 skipped (suite run this cycle)
