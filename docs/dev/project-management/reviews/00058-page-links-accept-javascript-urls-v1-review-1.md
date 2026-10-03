---
prd: dev/local/prds/wip/00058-page-links-accept-javascript-urls-v1.md
review: 1
date: 2026-09-26
head_sha: d6346a591ade04b4f007c9992576b219de35b7a7
codex_thread_id: 01a0dbf1-4abe-72b3-a02a-beb0df571a96
reviewers: alice,blake,bob,carl
agents:
  alice: available
  blake: available
  bob: available
  carl: available
  eve: disabled
---

# Review: 00058-page-links-accept-javascript-urls-v1

Diff range: `0183537fc3e1ac890b76ec3bf26f33f7399af863..d6346a591ade04b4f007c9992576b219de35b7a7`

codex_rung_guard: not fired

consensus_engine: legacy (single Alice subagent; the PRD sets no `consensus_engine`)
pack: failed (`engram pack` exited 1 twice: "not inside a registered repo; register it in /Users/bob/.config/gita/repos.csv") — every prompt taking `{PACK_FILE}`/`{PACK_FINDINGS}` received the `(no pack available this cycle)` sentinel. The review is degraded (no findings-precedent retrieval), not invalid.

## Diff-scope correction (read this before the findings)

Same defect the 00057 cycle hit, handled the same way. `gather-context.sh` on its
full-review path derives the base as the branch base and runs `git diff master`;
this repo commits PRD work directly onto `master`, so from `master` that diff is
empty by construction and the whole cycle would have reviewed nothing.

Corrected by re-running with `--since 0183537fc3e1ac890b76ec3bf26f33f7399af863`,
which yields the intended `work_start_sha..HEAD` range. The script then labels the
context "incremental review", which is false here and would have told the
reviewers not to re-review unchanged code, so that label was replaced in the
context file with an explicit FULL-review note. This is a defect in the autopilot
pack (`review-work-completion/scripts/gather-context.sh`), not in PRD 00058.

**Generated artifact excluded from the reviewer diff.**
`skills/brief-portfolio/assets/template.html` is a minified build artifact whose
14 changed lines are ~233KB of bytes — it made the diff 248582 bytes against
15740 for the eight source files, and its minified diff blew the 50K subagent
dispatch budget once during this PRD's build. It is never hand-edited, so it was
path-excluded and its freshness proven mechanically instead:
`diff skills/brief-portfolio/app/dist/index.html skills/brief-portfolio/assets/template.html`
exits 0 at this HEAD. Alice, Blake and Carl each independently rebuilt and
re-diffed it; all three confirm byte-identical.

## Mechanical checks: what actually covered this diff

Both shipped mechanical test-check scripts are **python-only and therefore
covered nothing here** — every changed file is JavaScript, Svelte or Markdown.
`detect_tautological_tests.py` checked 0 test functions in 0 files;
`replay_tests_against_base.py` reported `replay: skipped (the diff touches no
test function)`. This PRD's entire evidence base is its two new `node --test`
cases, so leaving that gap unaddressed would have meant converging with no
mechanical opinion on the one thing under test.

The equivalent replay was therefore **run by hand** and its result is a computed
fact, not an impression. A `git worktree` at the base commit `0183537fc3e1`,
HEAD's two changed test files overlaid, `node_modules` symlinked, then
`node --test src/lib/derive.test.js smoke.work.test.js`:

```
ℹ tests 9
ℹ pass 7
ℹ fail 2

✖ no anchor on any tab carries a javascript: or data: URL from the payload
  AssertionError: anchor href "data:text/html,x" has unsafe protocol "data:"
      at assertSafeAnchors (smoke.work.test.js:121:12)

✖ src/lib/derive.test.js
  SyntaxError: The requested module './derive.js' does not provide an export named 'safeUrl'
```

- **Both new tests fail against the pre-change code**, so neither is tautological.
- The other **7** pre-existing `smoke.work.test.js` cases pass at the base with
  HEAD's copy of that file, so HEAD's edits to it weakened no existing test.
- The harness mounts the **committed built artifact**
  (`smoke.harness.js:9`: `new URL('../assets/template.html', import.meta.url)`),
  not `src/`. So the hostile-payload test is evidence about the built page — the
  PRD's second Must-have — and a source fix that was never rebuilt into
  `assets/template.html` would fail it rather than pass silently.

## Consolidated Findings

`consolidate_findings.py`, 4 reviewers. No 🔴 Critical and no 🟠 High.

| Consensus | Severity | Issue | File | Task | Found By |
|-----------|----------|-------|------|------|----------|
| [1/4] | 🟡 | New hostile-payload test never opens the Brief tab or exercises the Quick Wins strip's window.open() call site, so the PRD's explicit requirement that "Brief's window.open consumer... must never reach it" is verified only by code reading (externalTodos/allTodos route url through safeUrl before Brief.svelte consumes it), not by a regression test on that specific consumer | skills/brief-portfolio/app/smoke.work.test.js | 2 | ALICE |
| [1/4] | 🟡 | Derived-todo sanitization is unpinned: removing the `safeUrl` applications from `todosFor`, both `externalTodos` branches, and `allTodos` would leave the new tests green, including the untested `Brief.svelte` `window.open` path | skills/brief-portfolio/app/src/lib/derive.test.js:252 | 1 | BOB |
| [1/4] | 🟡 | The new test hardcodes the personal repository identifier `buvis/demo`, contrary to the public-repository convention | skills/brief-portfolio/app/smoke.work.test.js:150 | 2 | BOB |
| [1/4] | 🟡 | The new hostile-URL test callback spans 56 lines, exceeding the 50-line function limit | skills/brief-portfolio/app/smoke.work.test.js:128 | 2 | BOB |
| [1/4] | 🟡 | Six component branches redundantly evaluate `safeUrl` for both the condition and `href`; bind the sanitized URL once per row and reuse it | N/A | 2 | BOB |
| [1/4] | 🟡 | Dropped CI run URL in Work tab fallback strips .run badge styling and runClass(w) severity class | skills/brief-portfolio/app/src/components/Work.svelte:151 | 2 | CARL |

### Overlap the consolidator could not merge

Rows 1 (Alice) and 2 (Bob) are **one defect seen from two ends** and were kept
separate only because the script merges on file, and they cite different files
(`smoke.work.test.js` vs `derive.test.js:252`). The shared root cause: nothing
pins the `safeUrl` *application* inside `derive.js`. The components sanitize
again at render time, so deleting every `safeUrl(...)` call in `todosFor`,
`externalTodos` and `allTodos` leaves every anchor safe and both new tests green
— and `Brief.svelte:72`'s `window.open(t.url)`, which has no component-level
guard, is the one consumer that would then be live again. Bob's R1 `fail` is
this. **Confirmed by reading, not by execution:** the claim follows from the
components re-sanitizing at render, which the diff shows directly. It was not
empirically re-run, because doing so means mutating `derive.js`, and the finding
is a Medium that the sweep fixes either way.

### Verified findings, per row

- **Row 4 (56-line callback) — confirmed by count.** The test callback spans
  `smoke.work.test.js:128`–`183` inclusive = 56 lines, over the 50-line limit in
  `rules/coding-style.md`. (The python-only mechanical-facts block does not cover
  this file, so the "contradicts computed facts" discard rule does not apply.)
- **Row 6 (Carl) — confirmed by reading.** `Work.svelte:151` renders
  `<a class="run {runClass(w)}" ...>` on the safe branch but the `{:else}` branch
  emits bare `{runMark(w)} {w.workflow}` with no wrapper, so a dropped CI URL
  loses the `.run` pill and its `sev-*` severity colour while every adjacent CI
  pill keeps both. A real, visible inconsistency.
- **Row 5 (redundant `safeUrl`) — confirmed by reading.** All six branches call
  `safeUrl(x.url)` twice, once in the `{#if}` and once in `href`. `{@const}` is
  legal as an immediate child of a Svelte block, so the fix is available.

### Discarded (verified reason) — 1 finding

- 🟡 **"The new test hardcodes the personal repository identifier `buvis/demo`,
  contrary to the public-repository convention"** (BOB,
  `smoke.work.test.js:150`) — **discarded; both halves of its rationale are
  false.** (1) Not newly hardcoded: `buvis/demo` is the pre-existing fixture
  convention in the sibling smoke test `smoke.repos.test.js:59`
  (`payload.epics.repos['buvis/demo']`), which this diff does not touch — the new
  test reused the established name. (2) Not a convention breach: AGENTS.md bans
  personal paths, usernames, hostnames, employer names and **private** project
  names; `buvis` is this repository's own public GitHub org
  (`github.com/buvis/agent-skills`) and `buvis/demo` is a fictional demo repo
  under it, leaking nothing the public repo does not already publish. Renaming it
  would also diverge the new fixture from the existing one. Recorded in
  `dev/local/reviews/00058-page-links-accept-javascript-urls-v1-ledger.json`.

### Verification-check queue

None written. The doubt lens's `VERIFY:` bucket is `- (none)`, so there is no
queued check for this cycle and no `-checks-1.json` file. An absent queue file
means no checks and is never an error.

## Alice

Ran `npm test` (45/45), `diff dist/index.html assets/template.html` (exit 0),
`validate_skill.py skills/brief-portfolio` (OK) and `braid --check` (0 drift)
herself rather than taking the recorded facts on faith. Traced every
`href={...}` binding across Work, Todos, Matrix, RepoDetail and Activity plus
the sole `window.open` call site (`Brief.svelte:72`); confirms all six
originally-vulnerable sinks now route through `safeUrl`, and that the anchors
left untouched (`RepoDetail.svelte:29`'s header link and the `slug()`-built
PR/issue/release/commit anchors) are correctly out of scope because they are
built from trusted local constants, never from a stored `url`. Confirmed
`allTodos` applies `safeUrl(t.url)` **after** the `...t` spread
(`derive.js:368`), which is the PRD's named highest-risk case. One Medium
finding, above.

```
[ALICE] 🟡 New hostile-payload test never opens the Brief tab or exercises the Quick Wins strip's window.open() call site, so the PRD's explicit requirement that "Brief's window.open consumer... must never reach it" is verified only by code reading (externalTodos/allTodos route url through safeUrl before Brief.svelte consumes it), not by a regression test on that specific consumer | File: skills/brief-portfolio/app/smoke.work.test.js | Task: 2
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

## Blake

Blind lens: PRD only, no diff, no file list, no review history. Found the code
himself, ran the suite and the build independently, and diffed the rebuilt
`dist/index.html` against the committed template (byte-identical). Confirms
`safeUrl` at `derive.js:166` is character-for-character the spec's expression;
confirms all three derived-todo assignment sites apply it after the spread, and
identifies from `git show 50f5f3e` that moving `url: safeUrl(...)` after
`...extra`/`...t` is the actual bug fixed (the raw spread previously clobbered
the `url: null` default). Independently checked that every remaining raw-string
`href` in the app is built from the trusted `https://github.com/${slug(repo)}`
constant and cannot carry a foreign scheme. Also verified the minified template
contains the `https?` regex literal — the fix shipped in the built artifact, not
only in source. No findings at any severity.

```
[BLAKE] ✅ No issues found
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
B17: fail
B18: pass
B19: pass

**B17 is not a defect.** The PRD defines only Phase 0 (Foundation) and Phase 1
(Core); B17 asks about Phase 3 acceptance criteria, which do not exist. The
rubric mandates `fail` for a rule that cannot be evaluated and forbids omitting
the line, so `fail` here means "unevaluable", not "criteria unmet". B15 and B16
cover the PRD's two real phases and both pass.

## Bob

Doubt + de-slop lens on codex (`gemini`-free path), plus the consensus rubric.
Ran once, no retry needed. Four Medium findings, one of which this gate
discarded (above). His `R1: fail` and `R12: fail` are both about the tests, not
the fix: R1 for the unpinned `safeUrl` application, R12 for the 56-line test
callback. Both are accurate.

**Note on the run:** codex's first shell read was denied by aegis's
Fact-Forcing Gate (`gateguard`) — `error=Command blocked by PreToolUse hook:
[Fact-Forcing Gate]` on its opening `wc -l && sed -n ... && sed -n ...` call.
Codex recovered on its own and read the inputs another way, so the review is
complete and no inlined-retry was triggered. This is the known first-run
friction for this reviewer, not a failure.

```
[BOB] 🟡 Derived-todo sanitization is unpinned: removing the `safeUrl` applications from `todosFor`, both `externalTodos` branches, and `allTodos` would leave the new tests green, including the untested `Brief.svelte` `window.open` path | File: skills/brief-portfolio/app/src/lib/derive.test.js:252 | Task: 1
[BOB] 🟡 The new test hardcodes the personal repository identifier `buvis/demo`, contrary to the public-repository convention | File: skills/brief-portfolio/app/smoke.work.test.js:150 | Task: 2
[BOB] 🟡 The new hostile-URL test callback spans 56 lines, exceeding the 50-line function limit | File: skills/brief-portfolio/app/smoke.work.test.js:128 | Task: 2
[BOB] 🟡 Six component branches redundantly evaluate `safeUrl` for both the condition and `href`; bind the sanitized URL once per row and reuse it | File: N/A | Task: 2
```

R1: fail
R2: pass
R3: pass
R4: pass
R6: pass
R7: pass
R8: pass
R9: pass
R10: pass
R11: pass
R12: fail
R13: pass
D1: pass
D2: pass
D3: pass
D4: pass
D5: pass

### Bob's doubt buckets

```
FIX:
- Derived-todo sanitization and the Brief consumer are not regression-pinned — skills/brief-portfolio/app/src/lib/derive.test.js:252 — assert unsafe and allowed URLs returned by `todosFor`, both `externalTodos` branches, and manual `allTodos`; add a Brief smoke check using an external authored quick win to exercise `window.open`.
- Personal repository identifier is newly hardcoded — skills/brief-portfolio/app/smoke.work.test.js:150 — derive the repository slug from the payload fixture instead of repeating `buvis/demo`.
- Hostile-URL test callback exceeds 50 lines — skills/brief-portfolio/app/smoke.work.test.js:128 — extract the payload construction into a focused fixture builder.
- Sanitizer calls are duplicated — skills/brief-portfolio/app/src/components/Matrix.svelte:55, skills/brief-portfolio/app/src/components/RepoDetail.svelte:79, skills/brief-portfolio/app/src/components/RepoDetail.svelte:132, skills/brief-portfolio/app/src/components/Todos.svelte:102, skills/brief-portfolio/app/src/components/Work.svelte:56, skills/brief-portfolio/app/src/components/Work.svelte:151 — bind `safeUrl(...)` once with a local `{@const href = ...}` and reuse `href`.

VERIFY:
- (none)

KNOWN:
- (none)
```

## Carl

Ran on the copilot backend, model `gemini-3.8-flash` (from the runner's stderr:
`gemini-run: backend=copilot model=gemini-3.8-flash`). Exit 0, non-empty output,
no fallback. He read the components, `derive.js`, `Brief.svelte`, the collector
(`scripts/collect.py`) to check the normalized `url` schema claim, and ran the
npm suite, the repo verifications and the template diff himself. As the panel's
frontend specialist he produced the one finding no other reviewer saw — the
styling regression in the rejected-URL fallback.

```
[CARL] 🟡 Dropped CI run URL in Work tab fallback strips .run badge styling and runClass(w) severity class | File: skills/brief-portfolio/app/src/components/Work.svelte:151 | Task: 2
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

## Reviewer run notes

The Watcher's first 50-minute budget (30 runs) expired with both CLI outputs
still pending. Rather than apply the "treat that reviewer as failed" rule
blindly, the live state was checked: Carl had just read the 264-line diff and
Bob was mid-turn, so both were working, not stalled. A second Watcher was
dispatched and both files completed on its runs 3 and 4. Declaring them failed
would have discarded two complete reviews, including the only UI finding and the
whole doubt lens.

## Review Summary

Reviewed: 2 completed tasks
PRDs checked: 00058-page-links-accept-javascript-urls-v1

### Agent Status

- Alice: ✅ Available
- Blake: ✅ Available
- Bob: ✅ Available
- Carl: ✅ Available (copilot backend, `gemini-3.8-flash`)
- Eve: ⏸️ Disabled: `doubt_reviewer` is `codex` and the codex doubt-roster guard
  did not fire (no task was implemented by codex — implementors were claude and
  gemini), so the opt-in fifth lens was not activated.

### Consolidated Findings

#### Full Consensus (4/4)
- none

#### Majority Consensus (>50%)
- none

#### Minority (<=50%)
- [1/4] 🟡 Brief `window.open` consumer not covered by a regression test | skills/brief-portfolio/app/smoke.work.test.js | Found by: Alice
- [1/4] 🟡 Derived-todo `safeUrl` application unpinned by tests | skills/brief-portfolio/app/src/lib/derive.test.js:252 | Found by: Bob
- [1/4] 🟡 Hostile-URL test callback is 56 lines, over the 50-line limit | skills/brief-portfolio/app/smoke.work.test.js:128 | Found by: Bob
- [1/4] 🟡 Six component branches evaluate `safeUrl` twice | N/A | Found by: Bob
- [1/4] 🟡 Rejected CI URL fallback loses `.run` and severity styling | skills/brief-portfolio/app/src/components/Work.svelte:151 | Found by: Carl
- _(discarded)_ [1/4] 🟡 `buvis/demo` fixture identifier | skills/brief-portfolio/app/smoke.work.test.js:150 | Found by: Bob

### The fix itself

Every reviewer that saw the diff, and the blind reviewer who did not, agree the
PRD's substance is correctly implemented: the `safeUrl` contract matches the
spec expression exactly, all six named sinks route through it, sanitization is
applied after the spreads (the actual bug), the plain-text fallback branches
exist, HTTP(S) positive controls are present at each surface, the template was
rebuilt rather than hand-edited, CHANGELOG.md carries a matching entry, and the
scope is surgical with no creep. Every surviving finding is about **test
coverage depth, a test's length, a double function call, and one fallback's CSS
classes** — not about whether hostile URLs still reach the page.

### Follow-up Tasks Created

None here, deliberately. This cycle converges (no unresolved CRITICAL or HIGH),
so the five surviving Medium findings belong to the review gate's **Tail sweep**,
which creates ONE `[D1] Tail sweep` task carrying every finding verbatim, rather
than the six separate per-finding tasks this step would otherwise create. Making
both sets would double-fix the same findings. No finding is lost: the sweep
task's `### Findings (verbatim)` block reproduces each one's own words.

Verdict: 6 findings
Tests: 3496 passed, 0 failed, 6 skipped (reused from last-verification.json at d6346a591ade04b4f007c9992576b219de35b7a7)
