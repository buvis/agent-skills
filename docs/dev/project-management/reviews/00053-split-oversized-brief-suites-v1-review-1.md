---
prd: dev/local/prds/wip/00053-split-oversized-brief-suites-v1.md
review: 1
date: 2026-09-21
head_sha: 2fd6389c7a67ec89d6be2b0a7de96e11c07b842b
consensus_run_id: wf_b2d21c3d-5d4
reviewers: alice,blake,bob,carl
agents:
  alice: available
  blake: available
  bob: available
  carl: available
---

# Review: 00053-split-oversized-brief-suites-v1

Diff range: `94c7aa51b5e30f28c98aafe1a647557908fd9662..2fd6389c7a67ec89d6be2b0a7de96e11c07b842b`

codex_rung_guard: not fired

pack: failed (engram: "not inside a registered repo; register it in ~/.config/gita/repos.csv", twice) — no
pack available this cycle. Prompts carried the `(no pack available this cycle)` sentinel for `{PACK_FILE}`
and `{PACK_FINDINGS}`. Additive retrieval context only; the review is degraded, not invalid.

Diff-scope note: `gather-context.sh` with no `--since` produced an EMPTY diff (it diffs against `master`,
and this repo commits directly on `master`). The run was redone with `--since <work_start_sha>`, giving the
PRD's whole work range (4 commits, 15 files, +1982/-1911). The script labels that "incremental review"; the
label is wrong here. This is cycle 1 and a full review.

consensus_engine: shadow — **the workflow leg ran this cycle** (`consensus_run_id: wf_b2d21c3d-5d4`). The
prior refusal ("scriptPath must be ... a file you can already read") was worked around by copying
`~/.claude/workflows/review-fanout.workflow.js` to `dev/local/tmp/review-fanout.workflow.js` and invoking
that path. Orchestrator deviation, recorded: the `diff` arg was passed TRUNCATED (the package.json,
smoke.harness.js, smoke.harness.test.js and smoke.repos.test.js hunks plus the smoke.test.js deletion
header, ~14 KB of 156 KB) with `diff_bytes: 156277` and `diff_path` set, so every dimension agent was told
to read the full diff file. A 156 KB diff cannot be re-emitted faithfully as a tool argument by the
orchestrator; the shadow is non-gating, so this is an observation-quality trade, not a review-quality one.
Shadow result in the Alice section below and in
`dev/local/tmp/00053-split-oversized-brief-suites-v1-consensus-shadow-1.md` (gated with
`check_review_file.py --reviewers alice`, exit 0).

## Review Summary

Reviewed: 5 completed tasks (task 1 wrote only a gitignored inventory and has no commit; tasks 2-5 are
commits b08a552, f2ad9e7, 9ae839a, 2fd6389). Tasks 4 and 5 never received a per-task review (diffs
85 KB / 74 KB, over the 50 K dispatch budget), so this cycle is their first independent review.
PRDs checked: 00053-split-oversized-brief-suites-v1.md

### Agent Status

- Alice: ✅ Available (Claude subagent, consensus lens; legacy leg gates; shadow workflow ran beside her)
- Blake: ✅ Available (Claude subagent, blind/PRD-only lens; no Filesystem-notes block — `dev/local` is a
  real directory and the root is not a dot-directory)
- Bob: ✅ Available **via Claude fallback**. codex exited 1 twice (first run + one CLI retry, ledger rows
  171afe1b and ead4f766 closed `error`): the codex session log records
  `usage_limit_exceeded` ("You've hit your usage limit ... try again at 6:11 AM"). Neither exit was 3/4,
  so the CLI retry ran first per `agent-invocation.md`; on the second exit 1 the Claude fallback was
  dispatched with Bob's exact assembled prompt (read-only-shell wording swapped for the Read tool).
  `bob-thread-00053-c1-202609210222.txt` holds the failed thread's id; no `codex_thread_id` is stamped.
- Carl: ✅ Available (gemini via `backend=copilot model=gemini-3.8-flash`, exit 0, ledger row 5b9c3f56
  closed `ok`; 75.59 AI credits, 4m44s)
- Eve: ⏸️ Disabled (codex doubt-roster guard not fired — every task attempt has `implementor: "claude"`)

Watcher subagent dispatched with the CLI reviewers (loop mode), stopped once every reviewer reached a
terminal state. One retry spent (Bob, CLI re-dispatch); no format or verdict retries were needed.

## Consolidated Findings

`consolidate_findings.py` over ALICE, BLAKE, BOB, CARL (no ledger on cycle 1). Eleven rows, none 🔴/🟠.

| # | Consensus | Severity | Issue | File | Task | Found By |
|---|-----------|----------|-------|------|------|----------|
| F1 | [1/4] | 🟡 Medium | collect_test_helpers.py docstring is copy-pasted from skills/distil-memory/scripts/docket_test_helpers.py: it justifies the file by "the shape the funnel family removed when `funnel_test_helpers.py` was created", but brief-portfolio has no funnel family and no such file; the citation only resolves inside distil-memory | skills/brief-portfolio/scripts/collect_test_helpers.py:6 | 3 | Bob |
| F2 | [1/4] | ⚪ Low | The shared 8-line jsdom/each_key_duplicate rationale comment (originally atop smoke.test.js) now survives in only one of the three files whose duplicate-rendering tests it explains (kept in smoke.repos.test.js:1, dropped from smoke.brief.test.js and smoke.work.test.js, which each have their own "duplicate ... instead of crashing"/"duplicated issue label" test relying on that same regression). This was flagged as an open, non-blocking question in the design doc's own review log and left to implementor judgment; not a Must-have violation, just a documentation-completeness note for a future maintainer opening smoke.work.test.js in isolation. | skills/brief-portfolio/app/smoke.work.test.js | 4 | Alice |
| F3 | [1/4] | ⚪ Low | The suite-wide header ("Renders the built single-file page in jsdom. Catches the runtime breakage a successful `vite build` cannot...") now lives only atop smoke.repos.test.js; it describes all six smoke.*.test.js files, while smoke.harness.js, the module every one of them imports, has no header. Only the second paragraph (each_key_duplicate) belongs to repos | skills/brief-portfolio/app/smoke.repos.test.js:1 | 4 | Bob |
| F4 | [1/4] | ⚪ Low | test_collect_pipeline.py docstring names "main() pipeline: the registry partition, recovery from an unusable data.json, and the audit-cadence call site" and omits the two strict xfails it also carries; one of them (test_a_capped_commit_list_still_carries_the_true_commit_count) exercises collect_repo, not main() | skills/brief-portfolio/scripts/test_collect_pipeline.py:1 | 5 | Bob |
| F5 | [1/4] | ⚪ Low | Stale cross-reference kept byte-identical on purpose: "(comparable to the existing 1.6s real-wait test above)" now points at a test that lives in smoke.todos.test.js | skills/brief-portfolio/app/smoke.todos.status.test.js:211 | 4 | Bob |
| F6 | [1/4] | ⚪ Low | Comment names the deleted file ("same fixup the Todos-tab tests in smoke.test.js use") inside an inventoried a11y test body | skills/brief-portfolio/app/smoke.a11y.test.js:71 | general | Bob |
| F7 | [1/4] | ⚪ Low | Cannot statically verify: post-split body hashes equal the baseline. No after-inventory is recorded and dev/local/tmp/00053-build-inventory.py is hardcoded to the deleted smoke.test.js / test_collect.py, so the PRD's hash-equality acceptance has no artifact; my line-by-line read of every moved body against the deleted originals found no difference | N/A | general | Bob |
| F8 | [1/4] | ⚪ Low | Cannot statically verify: the recorded pytest line (3476 passed / 0 failed / 6 skipped) omits the xfailed count, so the must-have "same xfail set" has no recorded evidence; both decorators read verbatim in test_collect_pipeline.py:284 and :303 | N/A | 5 | Bob |
| F9 | [1/4] | ⚪ Low | write_report and make_git_repo each have exactly one consuming module (test_collect_local.py, test_collect_pipeline.py) yet were moved to the shared helpers file, while the JS side kept single-file helpers local (backlogListItems, stubClipboard) | skills/brief-portfolio/scripts/collect_test_helpers.py:19 | 3 | Bob |
| F10 | [1/4] | ⚪ Low | node --test runs each file in its own process, so the real-time tests (todos.status 500/1200/500 ms sleeps with 200-300 ms margins, waitFor timeout 60 ms with a 40 ms flush in harness.test) now share CPU with five other jsdom-mounting files instead of one; recorded run was green | skills/brief-portfolio/app/package.json:10 | 4 | Bob |
| F11 | [1/4] | ⚪ Low | Three moved JS test callbacks exceed 50 lines: 'A newer status announcement...' (~90, smoke.todos.status.test.js:204), 'A declined copy...' (~64, :139), 'Todos tab reports success...' (~53, smoke.todos.test.js:68); pre-existing and moved byte-identically as the PRD mandates | skills/brief-portfolio/app/smoke.todos.status.test.js:204 | 4 | Bob |

F2 and F3 describe the same header-placement question from two angles (Alice: the each_key_duplicate
note is missing from brief/work; Bob: the suite-wide first paragraph belongs on smoke.harness.js). The
script kept them apart because the `File:` strings differ; they are swept together as one theme.

No 🔴 Critical and no 🟠 High findings. The Medium/Low tail is swept by the decision gate (one `[D1]`
task), not carried into another review cycle.

### Independent equivalence verification (the PRD's hard constraint)

Three reviewers re-derived the byte-identical claim rather than trusting the implementor:

- Alice re-ran `dev/local/tmp/00053-verify-task4.mjs` (MULTISET MATCH, 0 missing/extra) and
  `dev/local/tmp/00053-verify-after.py` (names equal: True, 0 hash/byte mismatches); pytest 64 passed /
  4 xfailed; npm test 44/44.
- Blake, blind, found and re-ran the same two scripts (43/43 JS, 63/63 Python, zero differences), confirmed
  both strict xfails with identical `strict=True`/`raises=`/`reason=` in test_collect_pipeline.py, wc -l
  max 293 (JS) / 322 (Python), smoke.browser.test.js untouched, zero `test_collect.py`/`smoke.test.js`
  hits across backlog 00054-00069, no new dependencies in package.json.
- Carl ran both suites, validate_skill.py, `braid --check`, ruff/pyflakes over the five Python files, and
  an acorn function-length scan; all clean.
- The shadow workflow's rubric lane independently confirmed 35 JS callbacks and 63 Python bodies
  hash-identical to base 94c7aa5.

### Carry-forward and mechanical absorption

- **Carry-forward:** none. Cycle 1; no `…-checks-0.json` exists, which is normal.
- **Mechanical test checks:** zero `[MECH]` lines. Tautological shapes: 63 test functions in 4 Python
  files checked, none flagged. Fail-first replay: 0 touched tests ran — all 4 new `test_collect_*.py`
  modules fail to collect at base because `collect_test_helpers.py` does not exist there (expected for a
  file split; the base worktree cannot import the new helper module). Nothing to absorb.

### Verification-check queue

Written: `dev/local/reviews/00053-split-oversized-brief-suites-v1-checks-1.json`, one entry, from the
doubt lane's VERIFY bucket (Bob's Claude fallback ran the assembled doubt prompt, which carries eve.md's
FIX/VERIFY/KNOWN sections, and emitted the buckets; `source: "bob"` names the lane that produced them):

- F8 → `uv run pytest skills/brief-portfolio/scripts -q` (a project test command; queued).

Not queued (command shape), stay ordinary findings:

- F7's VERIFY ("copy the inventory scripts to *-after variants, run them, diff the tuples") names a
  procedure over throwaway `dev/local/tmp` scripts, not one project verification command. Already answered
  this cycle by Alice and Blake (above).
- F10's VERIFY ("run `npm --prefix skills/brief-portfolio/app test` five times consecutively") is a
  repetition, not one command. Four independent green runs at HEAD exist this cycle (work phase, Alice,
  Blake, Carl).

### Follow-up tasks

None created here. Task creation for this converged cycle is owned by the decision gate's **Tail sweep**
(`run-autopilot/references/phase-review.md` Phase 5), which builds ONE `[D1]` task from the actionable
Medium/Low findings. Creating them here as well would double-create the same work.

## Alice

Consensus lens, implementation-aware (legacy subagent leg; gates the cycle). One ⚪ finding (F2). All
twelve consensus rules pass. Independently re-derived equivalence (see above), spot-checked the backlog
rewrites in 00062/00069 for semantic correctness, checked import hygiene (no `import *`, no unused helper
imports), line caps, and debug/TODO markers.

```
[ALICE] ⚪ The shared 8-line jsdom/each_key_duplicate rationale comment (originally atop smoke.test.js) now survives in only one of the three files whose duplicate-rendering tests it explains (kept in smoke.repos.test.js:1, dropped from smoke.brief.test.js and smoke.work.test.js, which each have their own "duplicate ... instead of crashing"/"duplicated issue label" test relying on that same regression). This was flagged as an open, non-blocking question in the design doc's own review log and left to implementor judgment; not a Must-have violation, just a documentation-completeness note for a future maintainer opening smoke.work.test.js in isolation. | File: skills/brief-portfolio/app/smoke.work.test.js | Task: 4
[ALICE] ✅ No blocking issues found
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

**Shadow engine observation (non-gating, `consensus_engine: shadow`, run `wf_b2d21c3d-5d4`):**
`_engine: workflow — dimensions 4, raw 12, unique 11, confirmed 0, refuted 0, demoted 0, unverified 0,
diff_bytes 156277_`. Security dimension not armed (no security-ish path or line in the inlined diff
slice). Verdict `APPROVE`, `[ALICE] ✅ No issues found`, all twelve R rules pass — no divergence from
legacy Alice's verdict. Eleven advisory (non-blocking) notes: 1 MEDIUM, 10 LOW. Overlap with the gating
table: the a11y comment (F6, raised by three dimensions), the status-file "test above" comment (F5, three
dimensions), the funnel-family docstring (F1), the header placement (F2/F3), the pipeline docstring (F4).
Two notes the gating table lacks, recorded as observations only:

- MEDIUM (quality): `test_collect_pipeline.py` houses `test_a_capped_commit_list_still_carries_the_true_commit_count`,
  a `collect_repo` unit test, under a "main() pipeline" docstring, and backlog PRD 00062 (commit cap, a
  collect_repo concern) now says `### Module: test_collect_pipeline.py` while sibling collect_repo PRDs
  00067/00068 say `test_collect_repo.py`. Smallest fix is the F4 docstring clause (in the sweep); the
  cleaner move (test + `make_git_repo` to `test_collect_repo.py`, re-point 00062) is a follow-up call.
- LOW (requirements): held PRDs 00018 (`smoke.test.js:194-211`), 00023 (`Add three tests to ...
  smoke.test.js`) and 00027 (`Add the clientSize option to render() in smoke.test.js`) still name
  `smoke.test.js`. Outside the PRD's must-have (which scopes the rewrite to backlog 00054-00069); `hold/`
  is re-reviewed before resumption. Whoever un-parks them must remap (render() lives in
  smoke.harness.js; 00023's tests belong in smoke.brief.test.js; 00018's cited range is now in
  smoke.brief.test.js).

## Blake

Blind lens — PRD only, no diff, no file list, no review history. He located the code himself, re-ran
the equivalence scripts and both suites, checked every backlog PRD 00054-00069, and confirmed the
`test_collect_ci.py` → `test_collect_pipeline.py` rename is covered by the PRD's own "the design step may
regroup where a boundary does not fit" clause.

```
[BLAKE] ✅ No issues found
```

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

Doubt + de-slop lens. codex unavailable (usage limit, exit 1 twice); **Claude fallback** ran Bob's exact
assembled prompt (Read tool only, static analysis). Ten findings (F1, F3-F11 above), all twelve consensus
rules pass, all five doubt rules pass. His line-by-line read of every moved body against the deleted
originals found no difference.

```
[BOB] 🟡 collect_test_helpers.py docstring is copy-pasted from skills/distil-memory/scripts/docket_test_helpers.py: it justifies the file by "the shape the funnel family removed when `funnel_test_helpers.py` was created", but brief-portfolio has no funnel family and no such file; the citation only resolves inside distil-memory | File: skills/brief-portfolio/scripts/collect_test_helpers.py:6 | Task: 3
[BOB] ⚪ The suite-wide header ("Renders the built single-file page in jsdom. Catches the runtime breakage a successful `vite build` cannot...") now lives only atop smoke.repos.test.js; it describes all six smoke.*.test.js files, while smoke.harness.js, the module every one of them imports, has no header. Only the second paragraph (each_key_duplicate) belongs to repos | File: skills/brief-portfolio/app/smoke.repos.test.js:1 | Task: 4
[BOB] ⚪ test_collect_pipeline.py docstring names "main() pipeline: the registry partition, recovery from an unusable data.json, and the audit-cadence call site" and omits the two strict xfails it also carries; one of them (test_a_capped_commit_list_still_carries_the_true_commit_count) exercises collect_repo, not main() | File: skills/brief-portfolio/scripts/test_collect_pipeline.py:1 | Task: 5
[BOB] ⚪ Stale cross-reference kept byte-identical on purpose: "(comparable to the existing 1.6s real-wait test above)" now points at a test that lives in smoke.todos.test.js | File: skills/brief-portfolio/app/smoke.todos.status.test.js:211 | Task: 4
[BOB] ⚪ Comment names the deleted file ("same fixup the Todos-tab tests in smoke.test.js use") inside an inventoried a11y test body | File: skills/brief-portfolio/app/smoke.a11y.test.js:71 | Task: general
[BOB] ⚪ Cannot statically verify: post-split body hashes equal the baseline. No after-inventory is recorded and dev/local/tmp/00053-build-inventory.py is hardcoded to the deleted smoke.test.js / test_collect.py, so the PRD's hash-equality acceptance has no artifact; my line-by-line read of every moved body against the deleted originals found no difference | File: N/A | Task: general
[BOB] ⚪ Cannot statically verify: the recorded pytest line (3476 passed / 0 failed / 6 skipped) omits the xfailed count, so the must-have "same xfail set" has no recorded evidence; both decorators read verbatim in test_collect_pipeline.py:284 and :303 | File: N/A | Task: 5
[BOB] ⚪ write_report and make_git_repo each have exactly one consuming module (test_collect_local.py, test_collect_pipeline.py) yet were moved to the shared helpers file, while the JS side kept single-file helpers local (backlogListItems, stubClipboard) | File: skills/brief-portfolio/scripts/collect_test_helpers.py:19 | Task: 3
[BOB] ⚪ node --test runs each file in its own process, so the real-time tests (todos.status 500/1200/500 ms sleeps with 200-300 ms margins, waitFor timeout 60 ms with a 40 ms flush in harness.test) now share CPU with five other jsdom-mounting files instead of one; recorded run was green | File: skills/brief-portfolio/app/package.json:10 | Task: 4
[BOB] ⚪ Three moved JS test callbacks exceed 50 lines: 'A newer status announcement...' (~90, smoke.todos.status.test.js:204), 'A declined copy...' (~64, :139), 'Todos tab reports success...' (~53, smoke.todos.test.js:68); pre-existing and moved byte-identically as the PRD mandates | File: skills/brief-portfolio/app/smoke.todos.status.test.js:204 | Task: 4
```

Buckets (verbatim):

```
FIX:
- Docstring cites a distil-memory-only file and family — skills/brief-portfolio/scripts/collect_test_helpers.py:6 — delete the sentence "importing one test module from another is the shape the funnel family removed when `funnel_test_helpers.py` was created" (end the paragraph at "a test module is not a fixture library"), or replace it with "same shape as skills/distil-memory/scripts/docket_test_helpers.py".
- Suite-wide header stranded on one of six files — skills/brief-portfolio/app/smoke.repos.test.js:1 — move the first paragraph (lines 1-2, "Renders the built single-file page in jsdom..." through "a dead tab.") to the top of skills/brief-portfolio/app/smoke.harness.js:1; leave the each_key_duplicate paragraph on smoke.repos.test.js. No test body changes.
- Module docstring omits the strict-xfail defect records it hosts — skills/brief-portfolio/scripts/test_collect_pipeline.py:1 — append one clause to the docstring, e.g. "plus the two agoge strict xfails (missing registry, capped commit count)".
VERIFY:
- Body-hash equality after the split — copy dev/local/tmp/00053-build-inventory.py and 00053-scan-js.mjs to *-after variants that read the six smoke.*.test.js + smoke.a11y.test.js and the four test_collect_*.py, run them at HEAD 2fd6389, and diff the (name, body_sha256, xfail) tuples as a multiset against dev/local/tmp/00053-inventory-before.txt: expect 43 JS + 63 Python identical, zero differences.
- Same xfail set — run `uv run pytest skills/brief-portfolio/scripts -q` at HEAD and confirm the summary reads "... 4 xfailed" (2 from test_collect_pipeline.py, 2 from test_build_page.py), matching the baseline's "64 passed, 4 xfailed".
- Timing stability under wider node --test parallelism — run `npm --prefix skills/brief-portfolio/app test` five times consecutively on the dev machine; expect "fail 0" all five times (any failure in smoke.todos.status.test.js or smoke.harness.test.js means the split widened contention past the 200-300 ms margins, and PRD 00069 should be pulled forward).
KNOWN:
- Stale "1.6s real-wait test above" comment in smoke.todos.status.test.js:211 — the PRD's byte-identical-body constraint forbids editing it here; PRD 00069 rewrites that exact test body (replacing the sleeps) and should reword the comment then.
- smoke.a11y.test.js:71 names the deleted smoke.test.js — the file is listed Untouched by the design and its test bodies are hashed in the 00053 inventory, so editing it would break this PRD's own equivalence check; a one-line `test:` commit after 00053 closes (or PRD 00058/00066, which touch the app) should reword it.
- write_report / make_git_repo are single-consumer helpers in the shared module — task 3's contract lists all 8 helpers by name and the design review logged this as a non-blocker; moving them back would contradict the reviewed contract for no behavioral gain.
- Three moved JS test callbacks over 50 lines — verbatim moves the PRD mandates (no reformatting, no rewording); the 90-line one is the exact test PRD 00069 shortens.
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
D1: pass
D2: pass
D3: pass
D4: pass
D5: pass
```

## Carl

Gemini via `backend=copilot`, `model=gemini-3.8-flash`. Generalist review — the diff has no frontend
surface, and he did not invent frontend findings. He ran both suites, validate_skill.py, `braid --check`,
`uv run pytest tests/`, ruff and pyflakes over the five Python files, an acorn function-length scan of the
JS files, the backlog reference greps, and `git show 94c7aa5:...` spot-checks of `waitFor` and the helper
definitions before answering.

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

Verdict: 11 findings
Tests: 3476 passed, 0 failed, 6 skipped (reused from last-verification.json at 2fd6389c7a67ec89d6be2b0a7de96e11c07b842b)
