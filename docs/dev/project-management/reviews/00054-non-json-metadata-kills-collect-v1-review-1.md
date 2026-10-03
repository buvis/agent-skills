---
prd: dev/local/prds/wip/00054-non-json-metadata-kills-collect-v1.md
review: 1
date: 2026-09-21
head_sha: 0e3558a041f533569b91669baa9b49d8a16ac4c8
consensus_run_id: wf_6aecb2a9-e56
reviewers: alice,blake,bob,carl
agents:
  alice: available
  blake: available
  bob: available
  carl: available
---

# Review: 00054-non-json-metadata-kills-collect-v1

Diff range: `dd2942c1904ef5928d5364e4b8f67636d24980af..0e3558a041f533569b91669baa9b49d8a16ac4c8`

codex_rung_guard: not fired

pack: failed (engram: "not inside a registered repo; register it in ~/.config/gita/repos.csv", twice) — no
pack available this cycle. Prompts carried the `(no pack available this cycle)` sentinel for `{PACK_FILE}`
and `{PACK_FINDINGS}`. Additive retrieval context only; the review is degraded, not invalid.

Diff-scope note: this repo commits directly on `master`, so `gather-context.sh` without `--since` would diff
against `master` and produce an empty diff (established in the 00053 cycle). The run used
`--since <work_start_sha>` from the start, giving the PRD's whole work range (2 commits, 3 files, +54/-1).
The script labels that "incremental review"; the label is wrong here. This is cycle 1 and a full review.

consensus_engine: shadow — the workflow leg ran this cycle (`consensus_run_id: wf_6aecb2a9-e56`), invoked
via the `dev/local/tmp/review-fanout.workflow.js` copy (byte-identical to `~/.claude/workflows/`, verified
with `git diff --no-index`). The 5217-byte diff was passed in full (`diff_truncated: false`). Shadow result in
the Alice section below and in `dev/local/tmp/00054-non-json-metadata-kills-collect-v1-consensus-shadow-1.md`
(gated with `check_review_file.py --reviewers alice`, exit 0). Non-gating.

## Review Summary

Reviewed: 1 completed task (commits 0ed8813 tests-first, 0e3558a fix + CHANGELOG). Pat's per-task review
left one LOW (duplicated `fake_run`), carried here unfixed.
PRDs checked: 00054-non-json-metadata-kills-collect-v1.md

### Agent Status

- Alice: ✅ Available (Claude subagent, consensus lens; legacy leg gates; shadow workflow ran beside her)
- Blake: ✅ Available (Claude subagent, blind/PRD-only lens; no Filesystem-notes block — `dev/local` is a
  real directory and the root is not a dot-directory)
- Bob: ✅ Available **via Claude fallback**. codex exited 1 twice (first run + one CLI retry, ledger rows
  2c9210f6 and e60ea2fc closed `error`): the codex session log records `usage_limit_exceeded` ("You've hit
  your usage limit ... try again at 6:11 AM"). Neither exit was 3/4, so the CLI retry ran first per
  `agent-invocation.md`; on the second exit 1 the Claude fallback (`autopilot:bob`, Read tool only) was
  dispatched with Bob's exact assembled prompt (read-only-shell wording swapped for the Read tool).
  `bob-thread-00054-c1-202609210335.txt` holds the failed thread's id; no `codex_thread_id` is stamped.
- Carl: ✅ Available (gemini via `backend=copilot model=gemini-3.8-flash`, exit 0, ledger row 568d32dc
  closed `ok`; 4.53 AI credits, 1m10s; ran `uv run pytest skills/brief-portfolio/scripts -q` himself)
- Eve: ⏸️ Disabled (codex doubt-roster guard not fired — the one task attempt has `implementor: "claude"`)

Watcher subagent dispatched with the CLI reviewers (loop mode), stopped once every reviewer reached a
terminal state. One retry spent (Bob, CLI re-dispatch); no format or verdict retries were needed.

## Consolidated Findings

`consolidate_findings.py` over ALICE, BLAKE, BOB, CARL (no ledger on cycle 1). Six rows, none 🔴/🟠.

| # | Consensus | Severity | Issue | File | Task | Found By |
|---|-----------|----------|-------|------|------|----------|
| F1 | [2/4] | ⚪ Low | fake_run bodies are duplicated (near-identical) across the 3 new tests, and across the pre-existing meta_os_error/meta_timeout tests they extend | skills/brief-portfolio/scripts/test_collect_repo.py:122 | 1 | Alice, Carl |
| F2 | [1/4] | 🟡 Medium | [MECH] `test_collect_repo_records_meta_http_403_without_raising` passes against the pre-change code; it is the PRD-required 403 control ("existing 403 path is unchanged"), so passing at base is its purpose, not a gap | skills/brief-portfolio/scripts/test_collect_repo.py:154 | 1 | Bob, mech-check |
| F3 | [1/4] | ⚪ Low | Cannot statically verify: `uv run pytest skills/brief-portfolio/scripts -q` reports 0 failing, and the PRD success criterion that the gh shim answering an HTML body for one repo yields exit 0 plus a written `data.json` | N/A | 1 | Bob |
| F4 | [1/4] | ⚪ Low | The two new tests assert only `startswith("meta:")` and never pin the exception text, so they are weaker than their 403 sibling (which pins `str(http_403_exc)`) and would still pass if `f"meta: {e}"` degraded to `"meta: "`; the PRD success criterion says the entry "names the decode failure" | skills/brief-portfolio/scripts/test_collect_repo.py:135 | 1 | Bob |
| F5 | [1/4] | ⚪ Low | `fake_run` closure duplicated across the three new tests, differing only in the `gh` branch (return body vs raise); carried from Pat's per-task LOW | skills/brief-portfolio/scripts/test_collect_repo.py:123 | 1 | Bob |
| F6 | [1/4] | ⚪ Low | Catching `AttributeError` at the call site is broader than the failure it targets, and the empty-body row reads `meta: 'NoneType' object has no attribute 'get'`, which tells the digest reader nothing about an empty gh body; the PRD chose symptom-at-one-site over normalising `gh_json` | skills/brief-portfolio/scripts/collect.py:406 | 1 | Bob |

F1 and F5 describe the same defect (the duplicated `fake_run` closure); the script merged Alice's and
Carl's citations (`:122 ~ :123`) but kept Bob's paraphrase apart. Read together it is a 3/4 finding and is
swept as one theme.

No 🔴 Critical and no 🟠 High findings. The Medium/Low tail is handled by the decision gate (ledger
dismissals for the PRD-settled rows, one `[D1]` Tail sweep task for the rest), not carried into another
review cycle.

### Carry-forward and mechanical absorption

- **Carry-forward:** none. Cycle 1; no `…-checks-0.json` exists, which is normal.
- **Tautological shapes:** zero `[MECH]` lines — 11 test functions in 1 test file checked, none flagged.
- **Fail-first replay:** 3 touched tests ran against base `dd2942c`; 2 failed there (the two new
  regression tests, as the PRD requires), 1 passed: `test_collect_repo_records_meta_http_403_without_raising`.
  That `[MECH]` line names the same test file and test as F2, so `mech-check` was appended to F2's finders
  rather than adding a row. Every reviewer who addressed it (Alice, Bob, the shadow's rubric lane) reads it
  the same way: the PRD's acceptance criterion explicitly asks for a 403 control that "preserves today's
  `meta:` error behavior", so a control that passes on both sides of the change is doing its job.

### Verification-check queue

Written: `dev/local/reviews/00054-non-json-metadata-kills-collect-v1-checks-1.json`, one entry, from the
doubt lane's VERIFY bucket (Bob's Claude fallback ran the assembled doubt prompt, which carries eve.md's
FIX/VERIFY/KNOWN sections, and emitted the buckets; `source: "bob"` names the lane that produced them):

- F3 → `uv run pytest skills/brief-portfolio/scripts -q` (a project test command; queued).

Not queued (command shape), stays part of the ordinary finding: the second half of that VERIFY item
("rerun the agoge shim reproduction `run.sh metanonjson` ... confirm exit 0, `data.json` present") is a
procedure over an audit-results shim, not one project verification command. Alice, Blake and Carl each ran
the pytest command at HEAD this cycle (67 passed / 4 xfailed, 0 failed), and the work phase's full-suite run
is the `Tests:` line below.

### Follow-up tasks

None created here. Task creation for this converged cycle is owned by the decision gate's **Tail sweep**
(`run-autopilot/references/phase-review.md` Phase 5), which builds ONE `[D1]` task from the actionable
Medium/Low findings. Creating them here as well would double-create the same work.

## Alice

Consensus lens, implementation-aware (legacy subagent leg; gates the cycle). One ⚪ finding (F1). All
twelve consensus rules pass. Verified the except tuple at collect.py:406 matches the PRD's requested tuple
exactly, `gh_json` and its other 4 call sites (collect.py:91,111,153,169) are untouched, ran the skill suite
(67 passed / 4 xfailed / 0 failed), confirmed `collect_repo` at 47 lines and both files under 800 lines,
and the CHANGELOG entry under `[Unreleased] > Fixed` with the `**brief-portfolio**:` prefix.

```
[ALICE] ⚪ fake_run bodies are duplicated (near-identical) across the 3 new tests, and across the pre-existing meta_os_error/meta_timeout tests they extend | File: skills/brief-portfolio/scripts/test_collect_repo.py:122 | Task: 1
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

**Shadow engine observation (non-gating, `consensus_engine: shadow`, run `wf_6aecb2a9-e56`):**
`_engine: workflow — dimensions 4, raw 5, unique 4, confirmed 0, refuted 0, demoted 0, unverified 0,
diff_bytes 5217_`. Security dimension not armed (no security-ish path or line in the diff); the
requirements dimension returned zero findings. Verdict `APPROVE`, `[ALICE] ✅ No issues found`, all twelve R
rules pass — no divergence from legacy Alice's verdict. Four advisory (non-blocking) notes: 1 MEDIUM, 3
LOW. Overlap with the gating table: the `fake_run` duplication (F1/F5, quality dimension, MEDIUM there with
a concrete `_run_answering_gh(outcome)` factory proposed), the prefix-only assertions (F4, tests
dimension, with the exact `"Expecting value"` / `"NoneType"` content assertions), and the opaque empty-body
message (F6, correctness + quality, suggesting a one-line comment above the except naming the two shapes).
One note the gating table lacks, recorded as an observation only:

- LOW (tests): PRD success criterion 2 (exit 0, `data.json` written, one repo's `errors` names the decode
  failure) has no `main()`-level test — `collect_test_helpers.run_collector` drives `main()` end to end but
  its `make_fake_run` gh stub only ever raises `RuntimeError`, so no pipeline test sees a returned HTML or
  empty body. The unit tests do catch a regression of the except tuple (the replay confirms), so this is a
  documentation-of-intent gap ("and_the_run_continues" in the test names), not a masked failure.

## Blake

Blind lens — PRD only, no diff, no file list, no review history. He located the code himself, confirmed
the widened tuple sits only at the metadata call site (collect.py:398-409) with `gh_json` and its other
callers untouched (`collect_ci`'s `except RuntimeError: return []  # Actions disabled` at :151-155,
`_gh_alerts` at :165-171), matched both new tests and the 403 control to the acceptance bullet, ran the
skill suite (67 passed / 4 xfailed / 0 failed), and found no new dependencies, parameters or unrelated
refactors.

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
assembled prompt (Read tool only, static analysis). Five findings (F2-F6 above), all twelve consensus
rules pass, all five doubt rules pass.

```
[BOB] ⚪ Cannot statically verify: `uv run pytest skills/brief-portfolio/scripts -q` reports 0 failing, and the PRD success criterion that the gh shim answering an HTML body for one repo yields exit 0 plus a written `data.json` | File: N/A | Task: 1
[BOB] ⚪ The two new tests assert only `startswith("meta:")` and never pin the exception text, so they are weaker than their 403 sibling (which pins `str(http_403_exc)`) and would still pass if `f"meta: {e}"` degraded to `"meta: "`; the PRD success criterion says the entry "names the decode failure" | File: skills/brief-portfolio/scripts/test_collect_repo.py:135 | Task: 1
[BOB] 🟡 [MECH] `test_collect_repo_records_meta_http_403_without_raising` passes against the pre-change code; it is the PRD-required 403 control ("existing 403 path is unchanged"), so passing at base is its purpose, not a gap | File: skills/brief-portfolio/scripts/test_collect_repo.py:154 | Task: 1
[BOB] ⚪ `fake_run` closure duplicated across the three new tests, differing only in the `gh` branch (return body vs raise); carried from Pat's per-task LOW | File: skills/brief-portfolio/scripts/test_collect_repo.py:123 | Task: 1
[BOB] ⚪ Catching `AttributeError` at the call site is broader than the failure it targets, and the empty-body row reads `meta: 'NoneType' object has no attribute 'get'`, which tells the digest reader nothing about an empty gh body; the PRD chose symptom-at-one-site over normalising `gh_json` | File: skills/brief-portfolio/scripts/collect.py:406 | Task: 1
```

Buckets (verbatim):

```
FIX:
- New tests do not pin the decode text — skills/brief-portfolio/scripts/test_collect_repo.py:135 — add `assert "Expecting value" in result["errors"][0]` to the non-JSON test (and, if wanted, `assert "NoneType" in result["errors"][0]` at :151 for the empty-body test) so the entry is proven to carry the exception text, matching the 403 control's assertion shape at :170
VERIFY:
- Runtime acceptance and success criteria — run `uv run pytest skills/brief-portfolio/scripts -q` and confirm 0 failing; then rerun the agoge shim reproduction (`run.sh metanonjson` from `dev/local/audit-results/agoge-2026-09-05.md` finding 1) and confirm exit 0, `data.json` present, and that repo's `errors` holding one `meta: Expecting value...` entry
KNOWN:
- 403 control passes at base — the PRD acceptance criterion explicitly asks for "an explicit metadata HTTP-403 control preserves today's `meta:` error behavior"; a control that pins unchanged behavior must pass on both sides of the change, so it is not a tautology and not a regression pin
- `fake_run` duplicated in the three new tests — the six pre-existing tests in this file use the same one-closure-per-test convention, the PRD names both new tests verbatim (parametrizing would rename them), and `collect_test_helpers.make_fake_run` hard-codes the gh branch; extending it or introducing a factory for 3 of 9 tests is a refactor of the surrounding tests, out of this PRD's surgical scope
- Broad `AttributeError` catch and opaque empty-body message — the PRD's Solution section decides this deliberately ("No change to `gh_json`'s contract and none to its other callers ... because `collect_ci` reads `RuntimeError` as 'Actions disabled' and PRD 00056 owns that branch"); the error is still recorded in `errors` and printed as `WARN` on stderr by `main`, so nothing is swallowed
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
surface, and he did not invent frontend findings. He read the context, the diff, both changed Python
files, ran `uv run pytest skills/brief-portfolio/scripts -q` and `wc -l` on the changed files before
answering. One ⚪ finding (F1).

```
[CARL] ⚪ Duplicated fake_run stub structure across new metadata tests | File: skills/brief-portfolio/scripts/test_collect_repo.py:123 | Task: 1
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

Verdict: 6 findings
Tests: 3435 passed, 0 failed, 6 skipped (reused from last-verification.json at 0e3558a041f533569b91669baa9b49d8a16ac4c8)
