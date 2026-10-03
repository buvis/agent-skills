---
prd: dev/local/prds/wip/00017-malformed-memory-half-written-v1.md
review: 1
date: 2026-09-06
head_sha: be34106ac7a4631e835c555d2057ee802106e7b3
codex_thread_id: 01a074f9-752f-7dd0-ad93-0afc047a62b2
reviewers: alice,blake,bob,carl
agents:
  alice: available
  blake: available
  bob: available
  carl: available
---

# Review: 00017-malformed-memory-half-written-v1

Diff range: `e2ff3d4f1da8655416e44b49f6d21f2f551a712c..be34106ac7a4631e835c555d2057ee802106e7b3`

codex_rung_guard: not fired

Scope: FULL review, cycle 1. The range is `state.work_start_sha..HEAD`, this PRD's whole work
range. It was passed to `gather-context.sh` via `--since` because the work is committed straight
onto `master`, so the script's default `merge-base HEAD master` yielded an empty diff — an empty
diff must never reach the reviewers.

pack: skipped (engram refused: "not inside a registered repo; register it in
`~/.config/gita/repos.csv`"). `{PACK_FILE}` and `{PACK_FINDINGS}` were substituted with
`(no pack available this cycle)` in every prompt that takes them. Not retried: the failure is a
deterministic config precondition, not a transient error.

design doc: none (`design: skip` in the PRD frontmatter), so no empty-review-log gate applies.

## Alice (consensus, Claude subagent) — available

Ran `uv run pytest` locally: 1059 passed, 5 skipped, 10 xfailed (all 10 xfails pre-existing and
unrelated to this PRD); the 6 touched test files in isolation: 136 passed. Traced the full control
flow of `write.main()`'s two-stage try/except (naming + snapshot + `write_memory`, then
`append_pointer` + rollback) and `docket.py`'s three guarded read sites against every PRD-stated
contract (exit 1 vs 2 boundary, "read once" ordering, all-or-nothing rollback, stale
`existing_text` handling), confirming each holds. Git-diffed the four MECH-flagged
`pytest.raises(Exception)` tests against the base commit and found them byte-identical,
pre-existing tests relocated by the mandated Task-2 file split.

```
[ALICE] 🟡 New `target.read_text() if target.is_file() else None` snapshot read in `main()` is only guarded by `except (WriteError, KeyError)`; a permission-denied existing target (a real, if narrow, scenario) raises an uncaught `OSError`/`PermissionError` traceback, against the PRD's "no traceback" intent — this line did not exist before this PRD. | File: skills/distil-memory/scripts/write.py:147 | Task: 2
[ALICE] 🟡 `_rollback()`'s "restore" branch (`_atomic_write(target, previous)`, used for update rollback) has no test exercising its own failure; only the "unlink" branch (new-memory rollback failure) is covered by `test_main_write_reports_both_the_pointer_error_and_the_rollback_error_when_the_rollback_itself_fails`, which uses `kind="new"`. | File: skills/distil-memory/scripts/write.py:107 | Task: 2
[ALICE] 🟡 Record dict literals for `proposals.json` entries (7 keys) are duplicated verbatim 5 times across three tests; a small `_record(...)` helper (mirroring `docket_test_helpers.make_proposal`) would cut ~25 duplicated lines. | File: skills/distil-memory/scripts/test_docket_refusals.py:76-93,124-132,170-188 | Task: 3
[ALICE] ⚪ `except (OSError, json.JSONDecodeError)` guarding the plain-text `Path(args.file).read_text()` includes `json.JSONDecodeError`, which a text read can never raise (dead branch); matches the PRD's literal contract text verbatim so not a functional defect. | File: skills/distil-memory/scripts/docket.py:251 | Task: 4
[ALICE] 🟡 4 tests in test_write_crash_safety.py use `pytest.raises(Exception)` (tautological shape) — verified byte-identical to base, pre-existing tests moved by the Task-2 file split, so they pin no new behavior from this PRD; recommend a follow-up (outside this PRD) to narrow them to `pytest.raises(OSError)`. | File: skills/distil-memory/scripts/test_write_crash_safety.py:47,72,92,117 | Task: general
```

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
R13: pass

## Blake (blind lens, PRD-only) — available

Located the code himself from the PRD alone. Ran `uv run pytest skills/distil-memory/scripts -q`:
605 passed, 0 failed, 0 skipped, 0 xfail. Confirmed via `git show --stat` that the five fix
commits touch only `write.py`/`docket.py` and that `SKILL.md`/`CHANGELOG.md` were not modified
(the PRD forbids it). Verified all six "Must have" requirements directly against source.

```
[BLAKE] 🟡 Phase 0 acceptance asks for a retry-succeeds regression with an absent MEMORY.md (inject failure, assert absence, remove fault, retry); every test_main_write_* rollback test pre-creates MEMORY.md, and the one test that starts absent (line 412) only exercises rollback failure, not the retry-success half | File: skills/distil-memory/scripts/test_write_crash_safety.py | Task: Phase 0
[BLAKE] ⚪ save()'s own _save_queue write (docket.py:30-34) is called outside the try in _save_from_proposals_dir (docket.py:226) and stays unguarded against OSError; out of this PRD's explicit four-route scope but worth a follow-up ticket | File: skills/distil-memory/scripts/docket.py | Task: general
```

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

## Bob (doubt + de-slop lens, codex) — available

Static-only sandbox. Thread id `01a074f9-752f-7dd0-ad93-0afc047a62b2` captured for cycle-2 resume.

```
[BOB] 🟠 FIX: `read_text()` normalizes CRLF before rollback, violating exact-byte restoration. Snapshot with `read_bytes()`, restore bytes atomically, and add a CRLF regression. | File: skills/distil-memory/scripts/write.py:147 | Task: 2
[BOB] 🟠 FIX: An undecodable `MEMORY.md` raises `UnicodeDecodeError` outside the handler after the memory lands. Catch decoding failures and restore the target; otherwise retry encounters "already exists." | File: skills/distil-memory/scripts/write.py:154 | Task: 2
[BOB] 🟡 FIX: Snapshot reads can raise `OSError`, but the enclosing handler catches only `WriteError` and `KeyError`. Handle snapshot failures with exit 1 and test that both files remain untouched. | File: skills/distil-memory/scripts/write.py:149 | Task: 2
[BOB] 🟡 FIX: The required index snapshot is missing. `write_memory()` mutates the target before index readability is checked; capture index bytes or absence before mutation and test an index snapshot failure. | File: skills/distil-memory/scripts/write.py:148 | Task: 2
[BOB] 🟡 FIX: Recovery tests cover existing indexes, but no successful rollback-and-retry case covers an absent index. Parameterize new/update recovery tests over index presence and assert original absence after failure. | File: skills/distil-memory/scripts/test_write_crash_safety.py:211 | Task: 2
[BOB] 🟡 FIX: Both docket read handlers omit `UnicodeDecodeError`, so undecodable proposal files and `decide --file` inputs still produce tracebacks. Handle decoding failures as exit 1 and add byte-corruption cases. | File: skills/distil-memory/scripts/docket.py:223 | Task: general
[BOB] 🟡 FIX: The append-move regression accepts unrelated exceptions through `raises(Exception)`. Require `OSError` matching the injected "boom" message. | File: skills/distil-memory/scripts/test_write_crash_safety.py:47 | Task: general
[BOB] 🟡 FIX: The replacement-move regression accepts unrelated exceptions through `raises(Exception)`. Require `OSError` matching the injected "boom" message. | File: skills/distil-memory/scripts/test_write_crash_safety.py:72 | Task: general
[BOB] 🟡 FIX: The memory-move regression accepts unrelated exceptions through `raises(Exception)`. Require `write.WriteError` matching "boom" and its `OSError` cause. | File: skills/distil-memory/scripts/test_write_crash_safety.py:92 | Task: general
[BOB] 🟡 FIX: The temporary-write regression accepts unrelated exceptions through `raises(Exception)`. Require `OSError` matching the injected "boom" message. | File: skills/distil-memory/scripts/test_write_crash_safety.py:117 | Task: general
[BOB] 🟡 FIX: `assert exit_code != 2` duplicates the preceding `assert exit_code == 1`. Remove the redundant assertion; the exit-code contract remains fully checked. | File: skills/distil-memory/scripts/test_docket_exit_codes.py:240 | Task: 4
[BOB] ⚪ KNOWN: The four replay-listed success tests pass against base because they protect unchanged success behavior. Requiring these compatibility checks to fail against base is outside their regression purpose. | File: skills/distil-memory/scripts/test_docket_refusals.py | Task: general
[BOB] ⚪ Cannot statically verify: fail-first results for three uncollected write-test modules. VERIFY: overlay their supporting `write_test_helpers.py` onto the base replay checkout and run `uv run pytest skills/distil-memory/scripts/test_write*.py`, distinguishing assertion failures from collection errors. | File: N/A | Task: general
[BOB] ⚪ Cannot statically verify: tests and repository checks pass. VERIFY: run `uv run pytest`, `uv run python3 skills/create-skill/scripts/validate_skill.py skills/distil-memory`, and `braid --check`; the supplied record reports success. | File: N/A | Task: general
```

R1: fail
R2: fail
R3: pass
R4: pass
R6: pass
R7: pass
R8: pass
R9: fail
R10: fail
R11: pass
R12: pass
R13: pass
D1: pass
D2: pass
D3: pass
D4: pass
D5: pass

## Carl (Gemini) — available

Backend `copilot`, model `gemini-3.8-flash` (selected by `gemini-run.sh`, no native fallback).
Exit 0, non-empty reviewer text. No frontend surface in this diff, so reviewed as a generalist.

```
[CARL] 🟡 test_append_pointer_leaves_memory_md_fully_intact_when_the_move_fails_appending_a_new_line accepts any exception via `raises(Exception)` | File: skills/distil-memory/scripts/test_write_crash_safety.py:47 | Task: general
[CARL] 🟡 test_append_pointer_leaves_memory_md_fully_intact_when_the_move_fails_replacing_a_line_in_place accepts any exception via `raises(Exception)` | File: skills/distil-memory/scripts/test_write_crash_safety.py:72 | Task: general
[CARL] 🟡 test_write_memory_update_leaves_the_existing_file_fully_intact_when_the_move_fails accepts any exception via `raises(Exception)` | File: skills/distil-memory/scripts/test_write_crash_safety.py:92 | Task: general
[CARL] 🟡 test_append_pointer_leaves_no_leftover_tmp_file_when_the_write_step_itself_fails accepts any exception via `raises(Exception)` | File: skills/distil-memory/scripts/test_write_crash_safety.py:117 | Task: general
[CARL] 🟡 Unguarded target.read_text() can raise uncaught OSError on unreadable update target | File: skills/distil-memory/scripts/write.py:147 | Task: 2
```

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
R13: pass

## Consolidated Findings

Produced by `consolidate_findings.py` (script path, not model-side). No ledger existed this cycle
(cycle 1), so the `--ledger`/`--ledger-dismiss` flags were omitted and no Blake finding was
auto-dismissed.

| Consensus | Severity | Issue | File | Task | Found By |
|-----------|----------|-------|------|------|----------|
| [1/4] | 🟠 | FIX: `read_text()` normalizes CRLF before rollback, violating exact-byte restoration. Snapshot with `read_bytes()`, restore bytes atomically, and add a CRLF regression. | skills/distil-memory/scripts/write.py:147 | 2 | BOB |
| [1/4] | 🟠 | FIX: An undecodable `MEMORY.md` raises `UnicodeDecodeError` outside the handler after the memory lands. Catch decoding failures and restore the target; otherwise retry encounters "already exists." | skills/distil-memory/scripts/write.py:154 | 2 | BOB |
| [1/4] | 🟡 | New `target.read_text() if target.is_file() else None` snapshot read in `main()` is only guarded by `except (WriteError, KeyError)`; a permission-denied existing target raises an uncaught `OSError`/`PermissionError` traceback, against the PRD's "no traceback" intent — this line did not exist before this PRD. | skills/distil-memory/scripts/write.py:147 | 2 | ALICE |
| [1/4] | 🟡 | `_rollback()`'s "restore" branch (`_atomic_write(target, previous)`, used for update rollback) has no test exercising its own failure; only the "unlink" branch is covered. | skills/distil-memory/scripts/write.py:107 | 2 | ALICE |
| [1/4] | 🟡 | Record dict literals for `proposals.json` entries (7 keys) are duplicated verbatim 5 times across three tests; a small `_record(...)` helper would cut ~25 duplicated lines. | skills/distil-memory/scripts/test_docket_refusals.py:76-93,124-132,170-188 | 3 | ALICE |
| [1/4] | 🟡 | 4 tests in test_write_crash_safety.py use `pytest.raises(Exception)` (tautological shape) — byte-identical to base, pre-existing tests moved by the Task-2 file split, so they pin no new behavior from this PRD. | skills/distil-memory/scripts/test_write_crash_safety.py:47,72,92,117 | general | ALICE, mech-check |
| [1/4] | 🟡 | Phase 0 acceptance asks for a retry-succeeds regression with an absent MEMORY.md; every test_main_write_* rollback test pre-creates MEMORY.md, and the one test that starts absent (line 412) only exercises rollback failure, not the retry-success half. | skills/distil-memory/scripts/test_write_crash_safety.py | Phase 0 | BLAKE |
| [1/4] | 🟡 | FIX: Snapshot reads can raise `OSError`, but the enclosing handler catches only `WriteError` and `KeyError`. Handle snapshot failures with exit 1 and test that both files remain untouched. | skills/distil-memory/scripts/write.py:149 | 2 | BOB |
| [1/4] | 🟡 | FIX: The required index snapshot is missing. `write_memory()` mutates the target before index readability is checked; capture index bytes or absence before mutation and test an index snapshot failure. | skills/distil-memory/scripts/write.py:148 | 2 | BOB |
| [1/4] | 🟡 | FIX: Recovery tests cover existing indexes, but no successful rollback-and-retry case covers an absent index. Parameterize new/update recovery tests over index presence and assert original absence after failure. | skills/distil-memory/scripts/test_write_crash_safety.py:211 | 2 | BOB |
| [1/4] | 🟡 | FIX: Both docket read handlers omit `UnicodeDecodeError`, so undecodable proposal files and `decide --file` inputs still produce tracebacks. Handle decoding failures as exit 1 and add byte-corruption cases. | skills/distil-memory/scripts/docket.py:223 | general | BOB |
| [1/4] | 🟡 | FIX: The append-move regression accepts unrelated exceptions through `raises(Exception)`. Require `OSError` matching the injected "boom" message. | skills/distil-memory/scripts/test_write_crash_safety.py:47 | general | BOB, mech-check |
| [1/4] | 🟡 | FIX: `assert exit_code != 2` duplicates the preceding `assert exit_code == 1`. Remove the redundant assertion; the exit-code contract remains fully checked. | skills/distil-memory/scripts/test_docket_exit_codes.py:240 | 4 | BOB |
| [1/4] | 🟡 | test_append_pointer_leaves_memory_md_fully_intact_when_the_move_fails_appending_a_new_line accepts any exception via `raises(Exception)` | skills/distil-memory/scripts/test_write_crash_safety.py:47 | general | CARL, mech-check |
| [1/4] | 🟡 | Unguarded target.read_text() can raise uncaught OSError on unreadable update target | skills/distil-memory/scripts/write.py:147 | 2 | CARL |
| [1/4] | ⚪ | `except (OSError, json.JSONDecodeError)` guarding the plain-text `Path(args.file).read_text()` includes `json.JSONDecodeError`, which a text read can never raise (dead branch); matches the PRD's literal contract text verbatim so not a functional defect. | skills/distil-memory/scripts/docket.py:251 | 4 | ALICE |
| [1/4] | ⚪ | save()'s own _save_queue write (docket.py:30-34) is called outside the try in _save_from_proposals_dir (docket.py:226) and stays unguarded against OSError; out of this PRD's explicit four-route scope but worth a follow-up ticket | skills/distil-memory/scripts/docket.py | general | BLAKE |
| [1/4] | ⚪ | KNOWN: The four replay-listed success tests pass against base because they protect unchanged success behavior. Requiring these compatibility checks to fail against base is outside their regression purpose. | skills/distil-memory/scripts/test_docket_refusals.py | general | BOB, mech-check |
| [1/4] | ⚪ | Cannot statically verify: fail-first results for three uncollected write-test modules. VERIFY: overlay their supporting `write_test_helpers.py` onto the base replay checkout and run `uv run pytest skills/distil-memory/scripts/test_write*.py`, distinguishing assertion failures from collection errors. | N/A | general | BOB |
| [1/4] | ⚪ | Cannot statically verify: tests and repository checks pass. VERIFY: run `uv run pytest`, `uv run python3 skills/create-skill/scripts/validate_skill.py skills/distil-memory`, and `braid --check`; the supplied record reports success. | N/A | general | BOB |

### Mechanical test checks absorbed

Both computed blocks were appended to the context file and reached every implementation-aware
reviewer. Every `[MECH]` line matched an existing consolidated row naming the same test file and
tests, so `mech-check` was appended to those rows' finders rather than adding new rows:

- tautological shapes at `test_write_crash_safety.py:47,72,92,117` → Alice's row (all four), Bob's
  `:47` row, Carl's `:47` row.
- fail-first replay (4 touched tests pass against base, `test_docket_refusals.py`) → Bob's KNOWN row.

Replay run: 16 touched tests ran, 12 failed against base, 4 passed; 3 test files could not be
collected at base. Command: `uv run python -m pytest`.

### Verification-check queue

**Not written this cycle.** The queue is fed from a doubt lens's VERIFY *bucket*. Eve did not run
(the codex doubt-roster guard did not fire — no task has a `codex` implementor, so the resolved
doubt reviewer stayed `codex`), and `agents/bob.md` defines no FIX/VERIFY/KNOWN buckets: it emits
`[BOB]` issue lines and `R{n}` verdicts. `source: "bob"` is reserved precisely for this case, so
no entries were invented from his `VERIFY:`-prefixed issue text. `dev/local/reviews/
00017-malformed-memory-half-written-v1-checks-1.json` does not exist; an absent queue file means
no checks and is never an error.

Verdict: 20 findings

Tests: 1059 passed, 0 failed, 5 skipped (reused from last-verification.json at be34106ac7a4631e835c555d2057ee802106e7b3)
