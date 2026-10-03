---
prd: dev/local/prds/wip/00007-extract-memory-candidates-from-transcripts-v1.md
review: 1
date: 2026-08-30
head_sha: 67fa8989ddd7bf6666d8b088ae3281a7f8220b11
codex_thread_id: 01a05058-78fa-7f21-a9c8-fbdf3449e8d9
reviewers: alice,blake,bob,carl
agents:
  alice: available
  blake: available
  bob: available
  carl: available
---

# Review: 00007-extract-memory-candidates-from-transcripts-v1

Diff range: `f8f4df5419c63dfd51327ba2e627e7972006417d..67fa8989ddd7bf6666d8b088ae3281a7f8220b11`

codex_rung_guard: not fired

## Review Summary

Reviewed: 9 completed tasks
PRDs checked: 00007-extract-memory-candidates-from-transcripts-v1.md
Cycle: 1 of a cap of 2. Consensus engine: `legacy`. Doubt reviewer: `codex` (Bob).

### Agent Status

- Alice: ✅ Available (Claude subagent, consensus lens)
- Blake: ✅ Available (Claude subagent, blind lens — PRD-only)
- Bob: ✅ Available (codex, consensus + doubt/de-slop lens)
- Carl: ✅ Available (gemini via copilot backend)
- Eve: ⏸️ Disabled — `doubt_reviewer` resolved to `codex` and the codex doubt-roster guard did not fire (0 codex-implemented tasks; all 9 ran on `sonnet`), so the opt-in fifth lens was not activated.

### Run conditions worth recording

Three deviations from the clean path. None invalidates the cycle, all are stated so the review does not read as cleaner than it was.

1. **The branch-base diff was empty.** `gather-context.sh` resolves its base to `master`, and this PRD's work was committed directly onto `master`, so the first run produced a 0-byte diff. Re-run with `--since f8f4df5419c63dfd51327ba2e627e7972006417d` (the PRD's recorded `work_start_sha`), which is the correct full-PRD range. The context file therefore labels the scope "incremental review"; it is not one. This is cycle 1 and a full review — every reviewer prompt says so explicitly.
2. **No engram context pack.** `engram pack` exited 1 with `not inside a registered repo; register it in /Users/bob/.config/gita/repos.csv`. Not retried (the failure is deterministic, not transient). Every prompt received the sentinel `(no pack available this cycle)` per the documented fallback. The review is degraded on retrieval context, not invalid. Blake never receives a pack by design, so his lens is unaffected.
3. **Blake's `File:` fields were normalized.** He emitted absolute paths with trailing line-range annotations (`/Users/bob/.../funnel.py (main, lines 238-282)`); Alice and Bob emitted repo-relative paths. `consolidate_findings.py` merges paraphrases only when reviewers name the same file, so no Blake row could ever have merged. The path spelling was normalized to repo-relative before consolidation. Finding text, severity, and task attribution are untouched.

No ledger existed this cycle (cycle 1), so `consolidate_findings.py` ran without `--ledger`/`--ledger-dismiss`. One was created by this cycle's gate at `dev/local/reviews/00007-extract-memory-candidates-from-transcripts-v1-ledger.json`.

## Consolidated Findings

16 findings. Consensus is out of 4 active reviewers.

| Consensus | Severity | Issue | File | Task | Found By |
|-----------|----------|-------|------|------|----------|
| [2/4] | 🟠 High | The yield report is written to `Path("dev/local/audit-results")`, a bare cwd-relative path not anchored to the repo root. Task 9's own real `--dry-run` execution demonstrably wrote its report to `skills/distil-memory/scripts/dev/local/audit-results/distil-memory-20260830T012747Z.md` instead of the repo's `dev/local/audit-results/`. | skills/distil-memory/scripts/funnel.py | 7 | ALICE, BOB |
| [2/4] | 🟠 High | `main()` calls `corpus.resolve_parser()` a second time purely to get the version string, and that second call sits outside the `try/except corpus.StaleParserError` block guarding the first, so a cache change between the two surfaces as an unhandled traceback instead of the documented clean non-zero exit. | skills/distil-memory/scripts/funnel.py | 7 | ALICE, BLAKE |
| [1/4] | 🔴 Critical | `funnel.py:main()` has no exception handling around `triage()`/`judge()`: a `claude` CLI failure raises uncaught and produces **no yield report at all** — not even the counts already known before the crash. Undermines the PRD's first Success Metric and the project's whole reason for existing. | skills/distil-memory/scripts/funnel.py | general | BLAKE |
| [1/4] | 🟠 High | Phase 2 task "Run the funnel over one project with `--dry-run` and record the numbers in `dev/local/audit-results/`" has no evidence of ever being executed. | N/A | general | BLAKE |
| [1/4] | 🟠 High | `slices_matched` counts every regex occurrence while `slices_kept` emits one slice per text block, so an unfiltered block with two markers reports `2 → 1`; this violates the two-markers/two-slices acceptance case and makes stage deltas misleading. | skills/distil-memory/scripts/funnel.py:114 | 5 | BOB |
| [1/4] | 🟡 Medium | `test_funnel.py` is 799 lines, one line under the repo's 800-line hard cap. | skills/distil-memory/scripts/test_funnel.py | 9 | ALICE |
| [1/4] | 🟡 Medium | `out_dir.mkdir(...)` and `out_path.write_text(report)` in `main()` are unguarded; a write failure after the report has printed crashes uncaught with no message that persistence failed. | skills/distil-memory/scripts/funnel.py | general | BLAKE |
| [1/4] | 🟡 Medium | `scan()` defeats `_iter_entries()` streaming by materializing each complete transcript with `list(...)`. | skills/distil-memory/scripts/funnel.py:138 | 5 | BOB |
| [1/4] | 🟡 Medium | `main()` imports and executes the external parser twice, creating needless work and a possible reported/used version mismatch. | skills/distil-memory/scripts/funnel.py:255 | 7 | BOB |
| [1/4] | 🟡 Medium | Tests at `test_corpus.py:62` and `test_funnel.py:358,408` assert an unused base class or private constant literals already covered by behavior tests. | N/A | general | BOB |
| [1/4] | ⚪ Low | The 5-item "enumerated exclusions" list is duplicated verbatim between `funnel.py`'s module docstring and `assistant_only()`'s own docstring. | skills/distil-memory/scripts/funnel.py | 4 | ALICE |
| [1/4] | ⚪ Low | `judge()`'s `subprocess.run(..., timeout=120)` has no handling for `subprocess.TimeoutExpired`. | skills/distil-memory/scripts/funnel.py | 6 | ALICE |
| [1/4] | ⚪ Low | `select_transcripts()` doesn't guard `_PROJECTS_ROOT.iterdir()` the way `resolve_parser()` guards `cache_root.iterdir()`. | skills/distil-memory/scripts/corpus.py | 3 | ALICE |
| [1/4] | ⚪ Low | `judge()` passes transcript-derived slice text as a literal CLI argument rather than via a temp file with `-f`, departing from the documented dispatch convention. | skills/distil-memory/scripts/funnel.py | general | BLAKE |
| [1/4] | ⚪ Low | Cannot statically verify: assistant-role transcripts ever carry truthy `isMeta`; the cited upstream guard applies only to user entries, so exclusion #2 may be defensive-only. | skills/distil-memory/scripts/funnel.py:75 | 4 | BOB |
| [1/4] | ⚪ Low | Cannot statically verify: the recorded 532-test result, skill-validator result, and braid drift result without executing those checks. | N/A | general | BOB |

## Gate decisions

### Verified before routing

Two findings were checked against the filesystem and the real corpus rather than taken on the reviewer's word.

- **The stray report is real.** `skills/distil-memory/scripts/dev/local/audit-results/distil-memory-20260830T012747Z.md` exists; `dev/local/audit-results/` holds no distil-memory report. Alice's High is confirmed.
- **`isMeta` never fires on assistant entries.** Measured across 2,712 transcripts: 201,379 assistant-role entries, **zero** with a truthy `isMeta`; 1,406 non-assistant entries carry one. Bob's VERIFY item resolves as defensive-only — the open question the design doc's own review log left for implementation time.

### Discarded (2)

- **BLAKE 🟠 "Phase 2 dry run never executed"** — contradicted by evidence. It *was* executed; the report is on disk at the stray path above, with the exact timestamp `dev/local/meta/assumptions.md` records. Blake searched only the required destination and the repo root, so he could not see it. The true residual (no report at the required location) is the same defect as the cwd-path High and is tracked there.
- **BOB ⚪ "cannot statically verify runtime results"** — resolved, not deferred. `uv run pytest` ran in the foreground this cycle: 532 passed, 0 failed, 5 skipped. Alice and Blake each independently re-ran the suites and the validator. Bob's sandbox cannot execute, which is his documented constraint, not a defect in the work.

### Deferred (1)

- **BLAKE ⚪ `judge()` inline-argument / ARG_MAX** — deferred to PRD 00008. The inline-argument shape is what this PRD's design doc signed verbatim, and `judge()` is the one cross-PRD contract the design names (00008 imports it and calls it with `tier="strong"`). Changing its subprocess I/O is an 00008 design decision. No injection risk (list-form argv, no `shell=True`); the residual is an ARG_MAX ceiling well above a single assistant text block. Recorded in the ledger as a settled deferral so it is not re-argued next cycle.

### Routed to cycle-1 rework (13 findings → 5 tasks)

The remaining 13 findings became tasks 10-14, each carrying its source findings verbatim.

1. **Task 10 — [D1] Make `main()` fail loudly without losing the yield report** (🔴 + 🟡 + ⚪, Blake/Alice)
2. **Task 11 — [D1] Anchor the yield report to the repo root and relocate the stray task-9 report** (🟠 ×2, Alice/Bob/Blake)
3. **Task 12 — [D1] Resolve the parser once and keep the version lookup inside the guarded path** (🟠 + 🟡 ×2, Blake/Alice/Bob)
4. **Task 13 — [D1] Restore the design's counting contract in `_raw_marker_hits` and stop materializing transcripts in `scan()`** (🟠 + 🟡, Bob)
5. **Task 14 — [D1] De-slop: docstrings, defensive-only isMeta note, framework test, corpus guard, split `test_funnel.py`** (🟡 ×2 + ⚪ ×3, Alice/Bob)

Five tasks is under the scope alarm's threshold of 10, so no scope-overflow deferral applies.

Three judgment calls inside those tasks, recorded so they are visible rather than silent:

- **Task 13 aligns the counter, not the slice granularity.** Bob proposed emitting one `Slice` per `finditer` match. `Slice.text` is a whole text block and the design names the four `Slice` fields as a cross-PRD contract PRD 00009 consumes, so changing slice granularity is a 00009-affecting decision. Aligning `_raw_marker_hits` back to the per-block `search` the design signed is the smaller change and restores the signed contract.
- **Task 14 partially accepts Bob's framework-test finding**: removes `test_stale_parser_error_is_a_runtime_error` (it verifies Python, not the skill) and keeps the tier-mapping and transient/durable-literal tests, which bind to PRD-level rules.
- **Task 11 adds no CLI flag.** Blake's B7 (no flags beyond the PRD's) passes today; fixing one finding by breaking a passing rule is not a trade worth making. The anchor is resolved internally, and `Path(__file__)` is explicitly forbidden because this skill is reached through the `~/.agents/skills/` symlink farm.

## Alice

Consensus lens, implementation-aware. Ran the scripts/ suite (91 passed) and the skill validator ([OK]) herself rather than trusting the reported numbers, checked the mechanical-facts block against the code, and traced the task-9 output file to the stray path — the finding that anchored this cycle's highest-consensus High.

- 🟠 The yield report is written to `Path("dev/local/audit-results")`, a bare cwd-relative path not anchored to the repo root. | File: skills/distil-memory/scripts/funnel.py | Task: 7
- 🟡 `main()` calls `corpus.resolve_parser()` a second time purely to get the version string, outside the `try/except` guarding the first. | File: skills/distil-memory/scripts/funnel.py | Task: 7
- 🟡 `test_funnel.py` is 799 lines, one line under the repo's 800-line hard cap. | File: skills/distil-memory/scripts/test_funnel.py | Task: 9
- ⚪ The 5-item "enumerated exclusions" list is duplicated verbatim between the module docstring and `assistant_only()`'s. | File: skills/distil-memory/scripts/funnel.py | Task: 4
- ⚪ `judge()`'s `subprocess.run(..., timeout=120)` has no handling for `subprocess.TimeoutExpired`. | File: skills/distil-memory/scripts/funnel.py | Task: 6
- ⚪ `select_transcripts()` doesn't guard `_PROJECTS_ROOT.iterdir()`. | File: skills/distil-memory/scripts/corpus.py | Task: 3

R1: pass
R2: pass
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

Blind lens — PRD only, no diff, no file list, no design doc, no review history. Located the code himself, ran both suites (26 + 65 passed) and the validator, and executed the real tool against the live corpus (`--dry-run --project agent-skills --days 60` → `transcripts_read: 122, slices_matched: 285, slices_kept: 226, survivors: n/a, claude_checkup_version: 0.2.2`). He raised the cycle's only Critical and reproduced it live.

- 🔴 `main()` has no exception handling around `triage()`/`judge()`; a `claude` CLI failure produces no yield report at all. | File: skills/distil-memory/scripts/funnel.py | Task: general
- 🟠 `main()`'s second `corpus.resolve_parser()` sits outside the `try/except corpus.StaleParserError` block, contradicting SKILL.md's documented behavior. | File: skills/distil-memory/scripts/funnel.py | Task: general
- 🟠 Phase 2 dry-run task has no evidence of ever being executed. | File: N/A | Task: general — **discarded, see Gate decisions**
- 🟡 `out_dir.mkdir(...)` and `out_path.write_text(report)` are unguarded. | File: skills/distil-memory/scripts/funnel.py | Task: general
- ⚪ `judge()` passes slice text as a literal CLI argument rather than via `-f`. | File: skills/distil-memory/scripts/funnel.py | Task: general — **deferred to PRD 00008**

B1: fail
B2: pass
B3: pass
B4: pass
B5: fail
B6: pass
B7: pass
B8: pass
B9: pass
B10: pass
B11: pass
B12: pass
B13: pass
B14: fail
B15: pass
B16: fail
B17: pass
B18: pass
B19: pass

## Bob

Consensus + doubt/de-slop lens, codex, static-only sandbox. He alone caught the `slices_matched`/`slices_kept` unit mismatch, which is a drift from the design doc's own signed `_raw_marker_hits` body.

- 🟠 `main()` writes reports relative to CWD; task 9's report landed under `skills/distil-memory/scripts/dev/local/audit-results/`. | File: skills/distil-memory/scripts/funnel.py:275 | Task: general
- 🟠 `slices_matched` counts every regex occurrence while `slices_kept` emits one slice per text block. | File: skills/distil-memory/scripts/funnel.py:114 | Task: 5
- 🟡 `scan()` defeats `_iter_entries()` streaming by materializing each transcript with `list(...)`. | File: skills/distil-memory/scripts/funnel.py:138 | Task: 5
- 🟡 `main()` imports and executes the external parser twice. | File: skills/distil-memory/scripts/funnel.py:255 | Task: 7
- 🟡 Framework-verification tests at `test_corpus.py:62` and `test_funnel.py:358,408`. | File: N/A | Task: general — **partially accepted**
- ⚪ Cannot statically verify assistant `isMeta`. | File: skills/distil-memory/scripts/funnel.py:75 | Task: 4 — **resolved by measurement**
- ⚪ Cannot statically verify the recorded runtime results. | File: N/A | Task: general — **discarded, resolved by running the suite**

### Doubt-lens buckets

FIX:
- Report output depends on CWD — `skills/distil-memory/scripts/funnel.py:275` — resolve the target repository root before building the output path, test invocation from a subdirectory, move the recorded report to root `dev/local/audit-results/`, and remove the stray nested tree.
- Funnel stages use incompatible counting units — `skills/distil-memory/scripts/funnel.py:114` — emit one `Slice` per `_MARKER_RE.finditer()` match so two retained markers produce two retained slices, then correct the multi-marker test.
- `scan()` eagerly materializes transcripts — `skills/distil-memory/scripts/funnel.py:138` — update matched and kept accumulators while iterating `_iter_entries(path)` directly.
- Parser is resolved twice — `skills/distil-memory/scripts/funnel.py:247` — resolve and contract-check once, then reuse the same module/version for selection and reporting while preserving the public selection API.
- Redundant declaration-verification tests — `skills/distil-memory/scripts/test_corpus.py:62; skills/distil-memory/scripts/test_funnel.py:358,408` — delete them and retain the existing behavior-level tests.

VERIFY:
- `isMeta` assistant exclusion may be defensive-only — parse the transcript corpus and count entries where `type == "assistant"` and `isMeta` is truthy; if zero, document it explicitly as defensive or remove the branch and test.
- Runtime results are unavailable statically — run `uv run pytest`, `uv run python3 skills/create-skill/scripts/validate_skill.py skills/distil-memory`, and `braid --check`.

KNOWN:
- (none)

Both VERIFY items were executed by the gate this cycle rather than carried forward. See Gate decisions.

R1: fail
R2: fail
R3: pass
R4: fail
R6: pass
R7: pass
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

Gemini via the copilot backend. Read the context file and the full diff in four passes, then returned a clean sheet. This change has no frontend surface, so he reviewed as a generalist, which his persona prescribes.

- ✅ No issues found

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

## Follow-up Tasks Created

1. [D1] Make `main()` fail loudly without losing the yield report (M) — 🔴 — task 10
2. [D1] Anchor the yield report to the repo root and relocate the stray task-9 report (M) — 🟠 2/4 consensus — task 11
3. [D1] Resolve the parser once and keep the version lookup inside the guarded path (S) — 🟠 2/4 consensus — task 12
4. [D1] Restore the design's counting contract in `_raw_marker_hits` and stop materializing transcripts in `scan()` (M) — 🟠 — task 13
5. [D1] De-slop: docstrings, isMeta note, framework test, corpus guard, split `test_funnel.py` (M) — 🟡 — task 14

Verdict: 16 findings
Tests: 532 passed, 0 failed, 5 skipped
