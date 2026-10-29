---
head_sha: 14474c24c09d47484e6177076d901f63d929f916
reviewers: fanout,blake,eve
---

## Fanout

**00108-mistyped-store-hides-unpublished-work-v1-c1**
`[fast-track-00108-mistyped-store-hides-unpublished-work-v1-c1] ✅ No issues found`

Advisory (non-blocking, already adjudicated by the workflow — `verdict: APPROVE`, `blocking: []`):
- Second store check (`_has_kept_entries_for_store`) runs outside the try/except guarding file I/O errors in `main()`.
- `_has_kept_entries_for_store` duplicates `unpublished()`'s store-matching loop and re-loads the queue.

Rubric: R1-R13 all `pass`.

## Blake

**00108-mistyped-store-hides-unpublished-work-v1-c1**
🟡 The card asks for coverage of "a missing first-run store", but no test has a store directory that does not exist yet while kept entries still point at it. The code probably keeps this case quiet, but no test locks it in. | File: skills/distil-memory/scripts/test_docket_unpublished.py:518
⚪ `_has_kept_entries_for_store` repeats the kept-entry/store-match filter from `unpublished()` and re-loads the queue. | File: skills/distil-memory/scripts/docket.py:242
⚪ The warning tests only check that the store path appears on stderr, never the reason text, so the two messages could be swapped. | File: skills/distil-memory/scripts/test_docket_unpublished.py:506

## Eve

**00108-mistyped-store-hides-unpublished-work-v1-c1**

FIX:
- The "no kept entries belong to store" warning also fires when the queue holds zero kept entries at all (all-dropped, fresh queue, or a mistyped `--queue` path), beyond the card's "kept entries exist but none match" condition. docket.py:242-251,410.
- The missing first-run store case (store absent, a kept entry belongs to it) has no test. Same gap as Blake's finding above.
- The alternate-spelling test never reaches the new branch, because its entry stays unpublished. test_docket_unpublished.py:603-625.
- `_has_kept_entries_for_store` re-runs `load()` and duplicates the own-store derivation from `unpublished()`. Same gap as Blake's finding above.
- Warning tests pin the path but not the reason text. Same gap as Blake's finding above.
- `_snapshot_queue_and_store` snapshots store file names only, not contents.

VERIFY:
- Whether a missing-but-matching (first-run) store should stay silent or warn, per PRD finding 19 option A (local audit artifact, not in this repo checkout).

KNOWN:
- `skills/distil-memory/SKILL.md` step 7 doesn't mention the new stderr warning — out of this PRD's scoped files.
- Full `uv run pytest` is red by one unrelated pre-existing timing-sensitive test (`sweep-fix`); passes alone.
- Commit 521557a (tests) lands before commit 14474c2 (fix), so `uv run pytest` is red at the intermediate commit — expected fail-first history.

D1: pass
D2: pass
D3: pass
D4: pass
D5: pass

## Bob

Missing: codex's own sandbox PreToolUse "Fact-Forcing Gate" hook blocked every file read on both the original dispatch and the one retry, so codex returned all-`fail` R-verdicts with no grounded findings. Environment/tooling failure, not a finding about the diff.

## Carl

Missing: the gemini backend (via `copilot`) returned "You have exceeded your monthly quota" on the single dispatch; not retried (optional lane, quota exhaustion is not transient).

Verdict: converged
Tests: 4110 passed, 1 failed, 9 skipped (fast-track batch suite; the one failure, skills/sweep-fix/scripts/test_sweep_scan.py::test_scan_returns_promptly_past_the_deadline_while_a_repo_still_hangs, is a pre-existing timing-sensitive flake unrelated to this diff, confirmed passing alone)
codex_rung_guard: not fired
