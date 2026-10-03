---
prd: dev/local/prds/wip/00021-risks-tile-fake-zero-v1.md
review: 1
date: 2026-09-06
head_sha: f6344c14ebffa40cea518f3729e57ebe88a1127f
codex_thread_id: 01a0784a-4851-72d2-821c-757a87fe3123
reviewers: alice,blake,bob,carl
agents:
  alice: available
  blake: available
  bob: available
  carl: available
---

# Review: 00021-risks-tile-fake-zero-v1

Diff range: `f00c273a0328b4ce747873abc77f740ea7394cf0..f6344c14ebffa40cea518f3729e57ebe88a1127f`

codex_rung_guard: not fired

pack: failed (`engram pack` exited 1 — "not inside a registered repo; register it in the gita repos.csv"). Not retried: the cause is a deterministic configuration fact, not a transient error. `{PACK_FILE}` and `{PACK_FINDINGS}` were substituted with `(no pack available this cycle)` in every prompt that takes them. The review is degraded by the missing retrieval context, not invalid.

## Review Summary

Reviewed: 4 completed tasks (all of PRD 00021), one commit each — `28a221f`, `480826b`, `d7ba072`, `f6344c1`.
PRDs checked: `00021-risks-tile-fake-zero-v1.md`

### Agent Status

- Alice (consensus, Claude subagent): ✅ Available
- Blake (blind lens, PRD-only): ✅ Available
- Bob (doubt lens + de-slop, codex): ✅ Available — after one retry, see "Bob retry" below
- Carl (UI/frontend, Gemini via copilot, `gemini-3.8-flash`): ✅ Available

Eve did not run: the codex doubt-roster guard did not fire (no task carries
`implementor: "codex"` — all four attempts were `claude`), and `doubt_reviewer`
resolves to `codex`, so she is not an active lens this cycle.

### Bob retry

Bob's first dispatch exited 0 but produced no real review. He attempted to read
the context and diff with `tail`, the host's aegis gateguard PreToolUse hook
blocked the command ("Fact-Forcing Gate"), and he therefore defaulted all twelve
consensus rules to `fail` behind a single `⚪ Cannot statically verify` line. That
is a runtime tooling failure, not a review verdict, so it took the one-retry
budget: `[RETRY] bob attempt 1/1`.

The retry re-dispatched a fresh `codex-run.sh` with an amended prompt file that
**inlines** the PRD, the task list, the mechanical blocks, the recorded
verification and the full diff, so no file read is needed. The retry produced a
substantive review, and it is the output consolidated here. One elision is
recorded honestly: the `assets/template.html` hunk (~35 KB of minified bundle on
a single line) was replaced in Bob's inlined diff by a description plus four
mechanically verified facts about that file, because a static reviewer cannot
usefully read minified bundle bytes. Bob's `R`-rule verdicts on that file rest on
those stated facts, not on the bundle text. Alice and Carl each reviewed the real
file directly and both verified it independently.

### Coverage gap in the mechanical blocks (recorded, not hidden)

All three computed blocks — `compute_mech_facts.py`,
`detect_tautological_tests.py`, `replay_tests_against_base.py` — returned no-ops
this cycle, and that is a **tooling limitation, not a clean result**. All three
parse Python only, and every changed file here is JavaScript, Svelte, HTML or
Markdown:

- no function line counts were computed, so there are no computed facts to cite
  or to contradict a countable claim;
- the tautology scan checked 0 test functions in 0 test files;
- the fail-first replay reported `replay: skipped (the diff touches no test
  function)`, which means no *Python* test function — **not** that the diff has
  no tests. The diff extends one test and adds another in
  `skills/debrief-meeting/app/smoke.test.js`.

So the usual mechanical guard against a test that cannot fail was absent. The
gap was stated in the context file and in every reviewer prompt, with an explicit
instruction to judge the two touched tests by hand and state a verdict. Alice,
Bob and Carl each did; their verdicts are recorded below and they agree.

## Consolidated Findings

| Consensus | Severity | Issue | File | Task | Found By |
|-----------|----------|-------|------|------|----------|
| [1/4] | 🟡 Medium | Task 4's new test duplicates existing coverage verbatim: `smoke.test.js:113` (pre-existing, in `opens on the brief with the headline counts`) already asserts `tiles.includes('1liverisks')` against the same default `PAYLOAD`; the new test at `smoke.test.js:221-225` (`brief live-risks tile shows the unresolved count when extraction ran`) reasserts the identical fact with the identical setup. The PRD mandated this test verbatim, and the new name is more intent-revealing than the old one, but the duplication itself is avoidable — simpler shape: drop the redundant `1liverisks` assertion from the pre-existing "opens on the brief" test (or fold its remaining assertions into the new, better-named test) instead of asserting the same fact twice. | skills/debrief-meeting/app/smoke.test.js | 4 | ALICE |
| [1/4] | ⚪ Low | KNOWN — Fail-first verdict: the extended no-extract test would fail against the pre-change template; the added with-extract pin would pass, so R2 fails under its mandated definition. This pin is intentionally required by the PRD to prevent hard-coding `—`, so no corrective change is appropriate. | skills/debrief-meeting/app/smoke.test.js | general | BOB |

### Full Consensus (4/4)

- (none)

### Majority Consensus (>50%)

- (none)

### Minority (<=50%)

- [1/4] 🟡 Duplicate `1liverisks` coverage between `smoke.test.js:113` and `smoke.test.js:224` | skills/debrief-meeting/app/smoke.test.js | Found by: Alice
- [1/4] ⚪ The with-extract pin passes against pre-change code, so R2 fails on its literal wording | skills/debrief-meeting/app/smoke.test.js | Found by: Bob

No CRITICAL and no HIGH finding was raised by any lens.

Alice's finding was verified independently before consolidation:
`rg -n "1liverisks" skills/debrief-meeting/app/smoke.test.js` prints exactly two
lines, 113 and 224, and both render the same default `PAYLOAD`. The duplication
is real.

### Mechanical-check absorption

No `[MECH]` line was produced by either test-check block this cycle (both were
no-ops for the reason recorded above), so nothing was absorbed into the table.

### Carried-forward checks

None. This is cycle 1; there is no prior `checks-0.json`.

### Verification-check queue

No queue file was written for this cycle. The queue is populated from a doubt
lens's **VERIFY** bucket; Eve did not run, and `agents/bob.md` mandates the
`[BOB]` issue-line format plus `R{n}` verdicts and defines no FIX/VERIFY/KNOWN
buckets, so `source: "bob"` is reserved and nothing sources from him. Bob's one
finding is prefixed `KNOWN —` in his own prose but is not an emitted VERIFY
bucket item, so it is a normal consolidated finding and is classified as such.

## Alice

Consensus lens, implementation-aware. One 🟡 Medium finding (the duplicate
coverage above). Everything else clean: the `Brief.svelte` guard matches the PRD
contract verbatim (`extractRan ? unresolvedRisks.length : na`), the not-run note
text matches exactly, and `unresolvedRisks` has no other caller that the guard
could break. She rebuilt the template and confirmed `diff dist/index.html
assets/template.html` exits 0, so the shipped artifact is genuine build output
and was not hand-edited; it carries exactly one `__MEETING_PAYLOAD__` marker and
exactly one instance of the new note text. She ran the smoke suite: 48 pass, 0
fail, 0 skipped. Security, error handling, debug/TODO markers and function/file
sizes all clean.

Her hand-judged fail-first verdicts on the two touched tests:

1. `brief tiles show em dashes and a not-run note when extraction did not run`
   (extended, task 3) — **would FAIL against the pre-change template**. Pre-fix
   the tile was unguarded, so with `extract: {}` it rendered `0liverisks`, not
   `—liverisks`; both the new tile assertion and the new exact-note assertion
   fail on old code. Genuine regression test.
2. `brief live-risks tile shows the unresolved count when extraction ran` (new,
   task 4) — **does NOT fail against the pre-change code**. With
   `extractRan: true` the pre-fix and post-fix expressions evaluate identically.
   It is not tautological in the "cannot fail as written" sense — it would catch
   an inverted guard or a lazy always-placeholder fix — which is exactly the pin
   the PRD asked for. She recorded it for the record rather than raising it as a
   separate defect.

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

## Blake

Blind lens — PRD only, no diff, no file list, no review history. He located the
code himself and verified every requirement against the source, the built
template and a live test run (`npm test` in `skills/debrief-meeting/app`: 48
tests, 48 pass, 0 fail). He confirmed lines 19 and 30 of `Brief.svelte` match the
spec text exactly, that `template.html` is rebuilt with one
`__MEETING_PAYLOAD__` marker and one occurrence of the new note, and that
`smoke.test.js` carries both the extended not-run test and the new named test. He
also noted no unrelated dependency changes rode along with the fix.

[BLAKE] ✅ No issues found

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

Doubt lens + de-slop, codex (static-only sandbox), on the retry dispatch
described above. One ⚪ Low finding, raised as a KNOWN with no corrective change
proposed: the extended no-extract test would fail against the pre-change
template, but the added with-extract pin would pass, so R2 fails under the
rule's literal wording. He records that the pin is intentionally required by the
PRD to prevent a hard-coded `—`, and that no corrective change is therefore
appropriate. This is the one rule any lens failed, and Bob and Alice reach the
same factual conclusion about the two tests — they differ only on whether the
literal rule wording should be scored `fail`.

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

## Carl

UI and frontend specialist, Gemini `gemini-3.8-flash` via the copilot backend
(recorded from the runner's stderr: `gemini-run: backend=copilot
model=gemini-3.8-flash`). Exit 0, non-empty reviewer text, no fallback.

[CARL] ✅ No issues found

He verified the acceptance greps directly, ran the smoke suite, ran
`uv run pytest` and `validate_skill.py skills/debrief-meeting`, and rebuilt the
template and compared it with `cmp` against the committed artifact. His frontend
assessment: the change eliminates the misleading "0 live risks" display, all four
extraction-derived tiles now render `—` consistently, and the note accurately
lists live risks. His fail-first reading matches Alice's on both tests — the
extended not-run test fails against the pre-change template on both the
`—liverisks` and the note assertions; the new test pins the with-extract count
against accidental hard-coding, per PRD intent.

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

None created in this step. This cycle converges (no unresolved CRITICAL or HIGH),
so the Medium/Low tail is owned by the decision gate's tail sweep, which builds a
single `[D1]` task carrying the findings verbatim. Creating follow-ups here as
well would duplicate that task. Recorded as an autonomous decision.

## PRD success criteria

All four are met, and each was checked by at least two independent lenses:

- Four tiles render `—decisions`, `—actions`, `—openquestions`, `—liverisks`
  without an extract — pinned by the extended not-run test, which passes.
- Exactly one `main .muted` paragraph with the new exact sentence — asserted by
  the same test with `assert.equal`, which passes.
- A payload with `extract_ran: true` and one unaddressed risk still renders
  `1liverisks` — pinned by the new named test, which passes.
- `npm --prefix skills/debrief-meeting/app test` exits 0 with zero failures and
  the new named regression passing — confirmed by three separate runs (Alice,
  Blake, Carl) and by the orchestrator's own run.

Verdict: 2 findings
Tests: 1073 passed, 0 failed, 5 skipped (reused from last-verification.json at f6344c14ebffa40cea518f3729e57ebe88a1127f)

Supplementary, not the composed line above: the recorded verification covers
`uv run pytest`, `validate_skill.py` and `braid --check`, none of which collect
this PRD's Node smoke suite. Because every acceptance criterion in this PRD is
stated in terms of that suite, it was run once directly at the same HEAD:
`npm --prefix skills/debrief-meeting/app test` → 48 tests, 48 pass, 0 fail, 0
skipped, with `brief live-risks tile shows the unresolved count when extraction
ran` listed as passing. That is a fresh run, stated as such, and it does not
replace the reused counts on the `Tests:` line.
