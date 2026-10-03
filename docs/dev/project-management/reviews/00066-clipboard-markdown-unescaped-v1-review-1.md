---
prd: dev/local/prds/wip/00066-clipboard-markdown-unescaped-v1.md
review: 1
date: 2026-09-26
head_sha: d1251ad331f3a96963737b420e495c60d6c7ddc5
codex_thread_id: 01a0dec9-672e-7701-a00f-9162c1fa35d5
reviewers: alice,blake,bob,carl
agents:
  alice: available
  blake: available
  bob: available
  carl: available
---

# Review: 00066-clipboard-markdown-unescaped-v1

Diff range: `42443b2f5ba5006bccf5631956e9e017e246f33a..d1251ad331f3a96963737b420e495c60d6c7ddc5`
(5 commits; 4 files: `skills/brief-portfolio/app/src/components/Todos.svelte`,
`skills/brief-portfolio/app/smoke.todos.test.js`,
`skills/brief-portfolio/assets/template.html`, `CHANGELOG.md`)

codex_rung_guard: not fired

pack: failed (`engram pack` exits 1 — "not inside a registered repo; register it in
`~/.config/gita/repos.csv`"). Deterministic configuration refusal, not transient, so no
retry was spent. `{PACK_FILE}` and `{PACK_FINDINGS}` were substituted with
`(no pack available this cycle)` in every prompt that takes them. The review is degraded
by the missing retrieval context, not invalid.

**Diff-scope note.** This is cycle 1, a full review of the PRD's whole work range.
`gather-context.sh` with no `--since` computes the diff against `master`, and this branch
IS `master` with all five commits already in it, so that run produced a 0-byte diff. It was
re-run as `--since 42443b2f5ba5006bccf5631956e9e017e246f33a` (`state.work_start_sha`), which
is the range the skill mandates for a full autopilot review. The context file therefore
labels itself "incremental review"; it is not one. No prior review file exists for this PRD.

## Mechanical blocks — tooling gap, stated loud

All three computed blocks (`compute_mech_facts.py`, `detect_tautological_tests.py`,
`replay_tests_against_base.py`) are Python-only. This diff is JavaScript and Svelte, so
every block reported "skipped (non-python)" / "Checked 0 test function(s)" /
`replay: skipped (the diff touches no test function)`. **Those lines are the tools finding
no Python, not evidence about these tests.** The prompts carried that warning verbatim.

**The orchestrator ran the JS equivalent of the fail-first replay instead**, and it is the
load-bearing evidence for R2 this cycle:

```
git worktree add dev/local/tmp/00066-base-replay 42443b2f5ba5   # base = pre-change bundle
cp HEAD:skills/brief-portfolio/app/smoke.todos.test.js -> worktree
node --test --test-reporter=tap .../smoke.todos.test.js
-> # tests 8  # pass 6  # fail 2
   not ok 7 - copy open as markdown emits exactly one line per open todo whatever the action contains
             "clipboard text did not have exactly one line per open todo"  4 !== 3
   not ok 8 - copy open as markdown escapes a pre-existing backslash so it cannot cancel the added bracket escaping
             "pre-existing backslash before a bracket was not escaped to the exact expected output"
```

Both new tests fail against the pre-change code; the six pre-existing copy-button tests
still pass there. Neither new test is tautological. Worktree removed afterwards.
(Alice independently ran the same replay and reached the same result.)

## Consolidated Findings

| Consensus | Severity | Issue | File | Task | Found By |
|-----------|----------|-------|------|------|----------|
| [1/4] | 🟡 | FIX: The two new tests duplicate fixture cleanup, rendering, button lookup, clipboard capture, click, and flush setup; extract a local `captureOpenMarkdown(payload)` helper shared by both tests | skills/brief-portfolio/app/smoke.todos.test.js:186 | 1 | BOB |
| [1/4] | 🟡 | FIX: The three-line comment merely restates the test name, hostile fixture, and assertions; delete it | skills/brief-portfolio/app/smoke.todos.test.js:183 | 1 | BOB |
| [1/4] | ⚪ | VERIFY: Cannot statically verify required checks; run `npm --prefix skills/brief-portfolio/app test`, `uv run pytest`, `uv run python3 skills/create-skill/scripts/validate_skill.py skills/brief-portfolio`, and `braid --check`, requiring exit 0 from each | N/A | 1 | BOB |

No 🔴 Critical and no 🟠 High finding was raised by any lens.

**Verification-check queue: none written this cycle.** Bob's ⚪ line carries the `VERIFY:`
word because his assembled prompt includes the doubt lens's two-lens section, but
`agents/bob.md` defines no FIX/VERIFY/KNOWN buckets and `references/output-formats.md`
reserves `source: "bob"` for exactly that reason; Eve did not run (the codex rung guard did
not fire). The item is therefore **not queued** — it stays an ordinary finding. The
orchestrator ran all four named commands first-hand this cycle instead (results under
`Tests:` below and in the decision record), so the check is answered by evidence rather
than deferred to a runner.

## Alice (consensus, Claude subagent)

`[ALICE] ✅ No issues found`

Verified first-hand: the `copy()` sanitisation chain at `Todos.svelte:67-75`; that
backslash-escaping precedes bracket-escaping (the PRD's security-relevant ordering); that
collapsing whitespace before escaping backslashes is byte-equivalent to the PRD's literal
ordering because the two act on disjoint character classes; `npm test` 51/51; the fail-first
replay above; that `assets/template.html` carries the same chain and is byte-identical to
`app/dist/index.html` (the rebuild+copy step really ran); the CHANGELOG entry's placement,
prefix and user-visible wording; `validate_skill.py` → `[OK]`; `Todos.svelte` 173 lines,
`smoke.todos.test.js` 265 lines, `copy()` 27 lines — all within limits; no TODO/FIXME/
console.log/debugger; and the test-first commit order (test → fix → docs).

Considered and deliberately did not raise: merging the backslash and bracket `.replace()`
calls into one `/[\\[\]]/g` pass. Equivalent, but the PRD gives the transform as literal
code and folding two of its three steps would diverge from that contract to save one line.

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

## Blake (blind lens, PRD-only)

`[BLAKE] ✅ No issues found`

Blake received the PRD and the blind rubric only — no diff, no file list, no history — and
found the code himself. He independently confirmed the same sanitisation chain and ordering,
the preserved `- [ ] <repo>: <action>` format with no added URL suffix, both required test
cases (hand-tracing each expected string character-by-character against the replace chain),
`npm test` 51/51, `dist/index.html` identical to `assets/template.html`, the CHANGELOG
entry, and — via `git show --stat` on the four in-scope commits — no scope creep, no new
dependencies, no new parameters or exports. Working tree clean.

Non-blocking observation he recorded rather than filed: the one-line-per-todo test derives
its expected count from `doc.querySelectorAll('main .todo').length`, which counts rendered
todo rows rather than filtered-open ones. He judged it a test-robustness nit, not a defect,
because `Todos.svelte:62` filters on `!done.has(t.id)` before building the markdown. (The
orchestrator's replay run above happened to render 3 todos, not 1, and the assertion still
discriminated correctly — `4 !== 3` against base.)

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

## Bob (doubt + de-slop lens, codex)

Ran on codex, exit 0, first attempt, no retry. Thread id captured for the next cycle.

```
[BOB] 🟡 FIX: The two new tests duplicate fixture cleanup, rendering, button lookup, clipboard capture, click, and flush setup; extract a local `captureOpenMarkdown(payload)` helper shared by both tests | File: skills/brief-portfolio/app/smoke.todos.test.js:186 | Task: 1
[BOB] 🟡 FIX: The three-line comment merely restates the test name, hostile fixture, and assertions; delete it | File: skills/brief-portfolio/app/smoke.todos.test.js:183 | Task: 1
[BOB] ⚪ VERIFY: Cannot statically verify required checks; run `npm --prefix skills/brief-portfolio/app test`, `uv run pytest`, `uv run python3 skills/create-skill/scripts/validate_skill.py skills/brief-portfolio`, and `braid --check`, requiring exit 0 from each | File: N/A | Task: 1
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

## Carl (UI & design lens, Gemini)

Ran on backend `copilot`, model `gemini-3.8-flash`, exit 0, non-empty output, no fallback.

`[CARL] ✅ No issues found`

He read the diff and context, ran the app suite and the repo-level checks himself, read
`Todos.svelte`, the smoke test and `derive.js`, and diffed `app/dist/index.html` against
`assets/template.html` (identical). No accessibility, responsive, visual-consistency, UX or
component-structure finding: the change is a string transform inside an existing handler
with no markup, styling or interaction surface touched.

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

Verdict: 3 findings
Tests: 3526 passed, 0 failed, 6 skipped (suite run this cycle — `uv run pytest -q` → 3475 passed, 6 skipped, 4 xfailed, 264s; `npm --prefix skills/brief-portfolio/app test` → 51 passed, 0 failed, 0 skipped. The recorded `last-verification.json` was NOT reused: its `sha` is 42443b2f, this cycle's reviewed HEAD is d1251ad3. Also run first-hand this cycle: `uv run python3 skills/create-skill/scripts/validate_skill.py skills/brief-portfolio` → `[OK]`; `~/.agents/bin/braid --check` → `76 current, 0 drift`.)
