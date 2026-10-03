---
prd: dev/local/prds/wip/00067-remote-url-passes-query-dotdot-v1.md
review: 1
date: 2026-09-26
head_sha: a46a690b1a2f9f7254650cb970ba2c57206cff5a
codex_thread_id: 01a0df05-e9b5-7113-a1a4-aea69f811f1a
reviewers: alice,blake,bob,carl
agents:
  alice: available
  blake: available
  bob: available
  carl: available
---

# Review: 00067-remote-url-passes-query-dotdot-v1

Diff range: `9921133020b69c878fe8822a2806c332be5f1501..a46a690b1a2f9f7254650cb970ba2c57206cff5a`

codex_rung_guard: not fired

Scope: FULL cycle-1 review over the PRD's whole work range (`state.work_start_sha..HEAD`).
`gather-context.sh` was first run without `--since` and produced an EMPTY diff — this
repo's work lands directly on `master`, so its `merge-base HEAD master` base is HEAD
itself. It was re-run with `--since <work_start_sha>` to get the real range; the
context file's scope line was corrected to say so. The diff covers 3 files, 77
insertions, 2 deletions.

pack: failed (`engram pack` exited 1: "not inside a registered repo; register it in
~/.config/gita/repos.csv"). No retry — the cause is a config precondition, not
transience. `{PACK_FILE}` and `{PACK_FINDINGS}` were substituted with
`(no pack available this cycle)` for every reviewer that takes them. The review is
degraded on retrieval context, not invalid.

checks queue: none written. The verification-check queue is sourced from a doubt
lens's VERIFY bucket, which today means Eve or her substitute; Eve was not active
this cycle (the codex doubt-roster guard did not fire) and `source: "bob"` is
reserved by `references/output-formats.md`, so no bucket existed to queue. Bob's
one `Cannot statically verify` line is carried below as an ordinary finding.

## Consolidated Findings

| Consensus | Severity | Issue | File | Task | Found By |
|-----------|----------|-------|------|------|----------|
| [1/4] | 🟡 | The dispatched task's own "Reuse" instruction said to extend `make_fake_run` in `skills/brief-portfolio/scripts/collect_test_helpers.py` (adding an optional custom remote-URL string, default unchanged) for `test_an_unparseable_remote_is_skipped_before_any_gh_call`. Instead the diff defines a bespoke inline `fake_run` closure in both new tests that reimplements the same shape `make_fake_run` already has (dispatch on `cmd[0]`/`cmd[1]`, raise on any `gh` call). `make_fake_run` already raises unconditionally on `gh` calls, so extending it to accept a custom remote would have been a small, reusable change; the diff instead adds ~20 lines of duplicated fixture logic across two closures. Behavior-preserving simplification, not a defect: both new tests pass and the acceptance criteria (which only require "the make_fake_run pattern") are technically met. | skills/brief-portfolio/scripts/test_collect_repo.py:320 | 1 | ALICE |
| [1/4] | 🟡 | KNOWN: Four accepted-URL parameter instances pass against the pre-change code and cannot independently fail-first; fixing that is out of scope because they intentionally pin behavior the PRD requires to remain unchanged, while the four rejected instances provide fail-first coverage | skills/brief-portfolio/scripts/test_collect_repo.py:303 | 1 | BOB, mech-check |
| [1/4] | ⚪ | FIX: The changelog says "word characters," which in Python regex terminology includes Unicode and no longer describes the final ASCII-only `[A-Za-z0-9_]` implementation; replace it with "ASCII letters, digits, underscores, dots, and hyphens" | CHANGELOG.md:77 | 1 | BOB |
| [1/4] | ⚪ | Cannot statically verify: VERIFY with `uv run pytest skills/brief-portfolio/scripts -q` that the required suite reports zero failures and all existing remote-parsing tests pass | N/A | 1 | BOB |

Row 2 absorbed the fail-first replay's `[MECH]` line (same test file, same test), so
`mech-check` is appended to its finders. Consensus stays `[1/4]`: `mech-check` is a
computed finder, not one of the four reviewers.

## Mechanical checks (computed)

- **Tautological test shapes:** none. 17 test functions checked in 1 test file.
- **Fail-first replay:** 9 touched tests ran against `9921133020b6`; **5 failed
  against base, 4 passed**. The 4 that pass are the accepted-URL parameter cases of
  `test_remote_re_accepts_github_slugs_and_rejects_query_and_dotdot` — regression
  guards for behavior the PRD requires to stay unchanged. The 4 rejected-URL cases
  plus `test_an_unparseable_remote_is_skipped_before_any_gh_call` are the 5 that fail
  against base, so the change itself is pinned fail-first.
- **Sizes:** largest changed function `collect_repo` at 46 lines (limit 50);
  `collect.py` 632 lines and `test_collect_repo.py` 335 lines (limit 800).

## Alice

Consensus lens (Claude subagent, `consensus_engine: legacy`). One 🟡 Medium finding,
recorded in the table above.

Verification she performed and reported:

- Traced the tightened `REMOTE_RE` (`skills/brief-portfolio/scripts/collect.py:19`)
  and the dot-segment guard (`collect.py:75`) against all 4 accepted and 4 rejected
  shapes; all resolve as specified. The query-string and `/../` shapes fail to match
  the regex at all; the `..`-owner and `..`-name shapes match the character class and
  are caught by the `in (".", "..")` check.
- Confirmed `collect_repo` (`collect.py:429-435`) still catches `repo_slug`'s
  `RuntimeError` and turns it into a `stub_from_path` skip record, with no `gh` call
  reachable before that point. The pre-existing no-match path is unchanged; only the
  condition that triggers it widened.
- Ran `uv run pytest skills/brief-portfolio/scripts -q`: 115 passed, 0 failed.
- Checked the skill's other remote-shaped fixtures (`test_collect_pipeline.py`,
  `collect_test_helpers.py`) use plain alnum owner/name values, so none relies on a
  character the tightened class now rejects.
- Confirmed the work-phase MEDIUM fix (`a46a690`, `[\w.-]` → `[A-Za-z0-9_.-]`) closes
  the Unicode gap `\w` leaves open in Python's default str-pattern mode.
- No TODO/FIXME/debug markers added by the diff.
- CHANGELOG.md carries a matching `[Unreleased]/Fixed` entry.

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
```

## Blake

Blind lens (PRD-only prompt: no diff, no changed-file list, no review history). He
located the code himself.

```
[BLAKE] ✅ No issues found
```

What he independently confirmed:

- `REMOTE_RE` at `collect.py:19` is exactly the character class the PRD specifies.
- `repo_slug` (`collect.py:72-77`) rejects a `.`/`..` owner or name by reusing the
  pre-existing no-match branch rather than duplicating it — the PRD's "re-check and
  preserve it" instruction.
- `collect_repo` (`collect.py:429-435`) catches that `RuntimeError` and skips the repo
  with a reason before any `gh` call.
- Traced all 8 PRD shapes through the final regex plus the dot check; all 8 behave as
  the Must-have list requires.
- Both PRD-mandated tests exist with the mandated names and contents.
- `uv run pytest skills/brief-portfolio/scripts -q`: 115 passed, 0 failed.
- Diff is surgical across the three commits; no unrelated files, no new params, deps
  or features. CHANGELOG entry present.
- No second copy of `REMOTE_RE` or `collect.py` anywhere in the repo, so no stale
  duplicate was left un-tightened.

B15/B16/B17 were judged against the Phase 0 task's acceptance criteria, this PRD
having no Phase 1-3 tasks.

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
```

## Bob

Doubt + de-slop lens on codex (static-only sandbox), thread
`01a0df05-e9b5-7113-a1a4-aea69f811f1a`. Ran once, exit 0; no retry needed.
Three findings, all in the table above.

`R2: fail` is his one failing consensus rule, and it is the same judgment as his own
🟡 KNOWN row: the four accepted-URL parameter cases pass against the pre-change code.
The decision gate discarded that row with a verified reason (below), so R2's failure
is dispositioned rather than carried.

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
D1: pass
D2: pass
D3: pass
D4: pass
D5: pass
```

## Carl

Gemini lens (frontend & design specialist; a generalist pass here, the diff having no
frontend surface). Backend resolved and ran to exit 0 with non-empty reviewer text.
He independently ran `uv run pytest skills/brief-portfolio/scripts -q`, the full
`uv run pytest`, `validate_skill.py skills/brief-portfolio` and `braid --check`.

```
[CARL] ✅ No issues found
```

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
```

## Decision gate

No unresolved CRITICAL and no unresolved HIGH. Medium and Low never block
convergence, so this cycle converges; the rework cap (2) is not reached and is
irrelevant on this path.

| # | Severity | Disposition | Reason |
|---|----------|-------------|--------|
| 1 | 🟡 Medium | **discarded** (verified reason) | Initially classified auto-fix on Alice's description; **reversed after reading the code**, which shows her prescribed fix would break the test it targets. `make_fake_run` raises `RuntimeError("gh: not authenticated")` on a `gh` call, and `collect_repo` catches `RuntimeError` at `collect.py:433` and returns a skip stub — so a `gh` call made through that helper is swallowed, not surfaced. `test_an_unparseable_remote_is_skipped_before_any_gh_call` asserts no `gh` call happened, which needs an uncaught `AssertionError` plus a call log; `make_fake_run` has neither, and it derives its remote from `Path(cwd).name` so it cannot return a hostile URL at all. Reusing it would mean adding a call log and an error-mode switch to a helper shared by four test modules, to serve one caller. The two closures are also not duplicates of each other (4 lines asserting on `repo_slug` vs 7 asserting `collect_repo` made no `gh` call, different error modes), so "~20 lines of duplicated fixture logic" does not hold, and a per-test `fake_run` closure is this module's established convention (`_run_answering_gh` plus three existing tests). |
| 2 | 🟡 Medium | **discarded** (verified reason) | The four accepted shapes are regression guards the PRD explicitly requires ("still parse to their owner and name"). A guard for preserved behavior passes against base by design; that is not unpinned behavior. The change itself is pinned fail-first by the other 5 touched tests (replay: 5 of 9 fail against base). Acting on this row would mean deleting coverage the PRD mandates. Bob himself filed it KNOWN/out-of-scope with this justification. |
| 3 | ⚪ Low | auto-fix → tail sweep | Low, any consensus. The CHANGELOG entry says "word characters", which in Python str-pattern terms is Unicode-aware; the shipped class is ASCII-only. One-line accuracy fix to a user-visible entry. |
| 4 | ⚪ Low | **discarded** (verified reason) | The named check ran and passed four independent times at this exact HEAD: Alice 115 passed / 0 failed, Blake 115 passed / 0 failed, Carl the same command plus the full suite, and the work phase's own recorded verification (`last-verification.json` at `a46a690`, 3484 passed / 0 failed / 6 skipped). This is codex's sandbox limitation, not an open question. |

All three discards are appended to
`dev/local/reviews/00067-remote-url-passes-query-dotdot-v1-ledger.json`.

### Tail sweep

1 actionable finding (#3) → one task, `[D1] Tail sweep: correct the CHANGELOG
character-class wording for the tightened REMOTE_RE` (task id 2), run through the
rework-mode micro lane (`work/references/rework-mode.md` § Micro lane: 1 finding,
1 file, tree clean at claim time; `micro_lane_eligible` satisfied). The
orchestrator made the edit with the Edit tool — no subagent. Overrun ceiling
measured clean before staging: 1 file changed, 1 insertion, 1 deletion
(`net_lines` 0, `file_count` 1). Committed as `a30de2d`,
`docs(brief-portfolio): name the exact ASCII class in the REMOTE_RE changelog entry (task 2)`.

Attempt stamps: `implementor: orchestrator`, `red_check: n/a:micro-lane`,
`self_deslop: skipped:trivial`, `style_gate: clean` (no `.py` in the diff),
`split_hygiene: skipped:no-tests`, `review: skipped:docs-only`.

Post-sweep verification (the work phase's own step-7 run at `a30de2d`):
`uv run pytest -q` → 0, `validate_skill.py skills/brief-portfolio` → 0,
`braid --check` → 0 (`0 linked, 76 current, 20 ignored, 0 drift`).
**3484 passed, 0 failed, 6 skipped, 4 xfailed.**

No verify escapes: no queued-check file existed for this cycle, so there was
nothing for step 7 to run. No sweep escapes: step 5.7 was skipped as docs-only,
so it raised nothing.

Verdict: 4 findings
Tests: 3484 passed, 0 failed, 6 skipped (reused from last-verification.json at a46a690b1a2f9f7254650cb970ba2c57206cff5a)
