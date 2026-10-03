---
prd: dev/local/prds/wip/00006-nag-audit-cadence-in-brief-portfolio-v1.md
review: 1
date: 2026-08-29
head_sha: dc7f536f6071d34b007908a4aa637f03e7bf02e1
codex_thread_id: 01a04f54-df14-7752-ba86-74f0c732b67a
reviewers: alice,blake,bob,carl,eve
agents:
  alice: available
  blake: available
  bob: available
  carl: available
  eve: available
---

# Review: 00006-nag-audit-cadence-in-brief-portfolio-v1

Diff range: `e6545b6b1ac819b6b9e34be3bc38d01e0fa752db..dc7f536f6071d34b007908a4aa637f03e7bf02e1`

codex_rung_guard: fired (1 codex-implemented task(s))

Scope note: this is cycle 1, a **full review** of the PRD's whole work range (12 commits,
8 files, 341 insertions / 69 deletions). The work landed directly on `master`, so
`gather-context.sh`'s branch-base heuristic would have produced an empty diff
(`git diff master` from `master` on a clean tree). The diff was therefore scoped with
`--since <work_start_sha>`, which is exactly the `work_start_sha..HEAD` range the full-review
rule prescribes. The label inside the context file reads "incremental" for that reason; the
content is the full PRD work range. Working tree was clean throughout the review.

pack: unavailable this cycle — `engram pack` exited 1 with "not inside a registered repo;
register it in ~/.config/gita/repos.csv". Deterministic config state, so no retry (same
failure as cycles on PRDs 00003 and 00004 in this batch). Every implementation-aware prompt
received the sentinel `(no pack available this cycle)` for `{PACK_FILE}`/`{PACK_FINDINGS}`.
Blake never receives a pack by design.

ledger: none — cycle 1, so `consolidate_findings.py` ran without `--ledger`/`--ledger-dismiss`.

Codex doubt-roster guard: task 4's attempt carries `implementor: "codex"`, so the resolved
doubt reviewer was forced to `fable` in memory and **Eve joined as a fifth lens**. Bob (codex)
still ran and still carried the doubt rubric, so the guard added a voice rather than replacing
one. Both doubt reviewers produced usable output, so the constraint is met with no suffix.

## Agent Status

- Alice: ✅ Available (consensus lens, Claude subagent, `consensus_engine: legacy`)
- Blake: ✅ Available (blind lens, PRD-only)
- Bob: ✅ Available (consensus + doubt lens, codex, static-only)
- Carl: ✅ Available (UI/design lens, gemini via copilot backend)
- Eve: ✅ Available (doubt lens, Fable 5 — added by the codex-rung guard)

## Alice

Verified by running, not by reading: full pytest suite (435 passed, 5 skipped — pre-existing
`skills/survey` skips), `test_collect.py` 52 passed, `test_purge_devlocal.py` 39 passed,
`npm test` 16/16. Confirmed `template.html` carries `audit_cadence`/`purge_last_run` and no
`claude_maintenance_last`. Confirmed every `allTodos(repos, epics, external)` caller in
`Matrix.svelte`, `Brief.svelte`, `Todos.svelte`, `App.svelte` absorbs the signature change with
no edit needed. `ruff check` on the four touched Python files: all 19 findings pre-existing,
none on lines this diff touched. `git diff --stat` matches the stated 8-file scope — no scope creep.

```
[ALICE] ⚪ Comment above `externalTodos` still describes the old single-nag channel, not the now-repo-scoped one | File: skills/brief-portfolio/app/src/lib/derive.js | Task: 5
[ALICE] ⚪ Second `externalTodos(null)` regression site missing the null-guard comment the task spec required at both sites | File: skills/brief-portfolio/app/src/lib/derive.test.js | Task: 6
[ALICE] 🟡 test_collect.py is 819 lines, over the 800-line file-size limit (758->819 this PRD) | File: skills/brief-portfolio/scripts/test_collect.py | Task: general
[ALICE] 🟡 process_store is 65 lines, over the 50-line function limit (pre-existing at 64, this PRD added 1) | File: skills/purge-devlocal/scripts/purge_devlocal.py | Task: 4

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
R12: fail
R13: fail
```

## Blake

Blind lens — spec only, no diff, no file list, no review history. Located the code himself,
ran both suites live (52/52 pytest, 16/16 node), and rebuilt the Svelte bundle to confirm
`dist/index.html` is byte-identical to `assets/template.html`. Confirmed the exports and
signatures match the PRD, the old proxy is fully gone from production code, the seven rows are
wired at the right horizons, row-state tests cover 0 / h-1 / h / h+1 / never for both horizons,
and the brief renders with no prompt.

```
[BLAKE] 🟠 `collect_audit_cadence` doesn't catch `OSError` on `f.read_text()` (unlike sibling `collect_claude_skill_adherence`), and is called unguarded in `main()` unlike `collect_external`; an unreadable-but-present `skills.jsonl` crashes the whole run instead of degrading to "never" rows per the PRD's explicit Error-case scenario, and no test covers it | File: skills/brief-portfolio/scripts/collect.py | Task: general
[BLAKE] ⚪ Phase 0 task 3's literal acceptance criterion ("`rg claude_maintenance_last` over `scripts/` ... returns nothing, and `test_collect.py` has no test referring to it") is not met verbatim — `test_collect.py` still names the string twice in a regression test proving its absence; harmless but a literal spec-text miss | File: skills/brief-portfolio/scripts/test_collect.py | Task: general

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
B16: pass
B17: pass
B18: pass
B19: pass
```

## Bob

Consensus + doubt lens, codex, static-only sandbox (correctly reported the runtime checks it
could not execute as ⚪ rather than as failures).

```
[BOB] 🟠 Unreadable or concurrently removed `skills.jsonl` raises `OSError` and aborts the entire collector instead of returning the seeded never-run map | File: skills/brief-portfolio/scripts/collect.py:304 | Task: 1
[BOB] 🟡 Creating today's stamp before retention means `--empty-trash-days 0` immediately deletes it; create the stamp after `empty_old_trash` and test that case | File: skills/purge-devlocal/scripts/purge_devlocal.py:438 | Task: 4
[BOB] 🟡 The required `rg claude_maintenance_last` acceptance check still returns two test references; rename the test and remove its redundant negative assertion | File: skills/brief-portfolio/scripts/test_collect.py:809 | Task: 3
[BOB] 🟡 `collect_purge_devlocal` sorts every matching directory only to select one; replace the list and indexing with `max(generator, default=None)` | File: skills/brief-portfolio/scripts/collect.py:259 | Task: 2
[BOB] 🟡 `test_collect.py` is 819 lines, exceeding the 800-line limit; move the new cadence tests into a focused test module | File: skills/brief-portfolio/scripts/test_collect.py | Task: general
[BOB] ⚪ The `externalTodos` comment still describes only the machine-scoped `~/.claude` nag although the function now emits repo-scoped purge rows too | File: skills/brief-portfolio/app/src/lib/derive.js:336 | Task: 5
[BOB] ⚪ The second `externalTodos(null)` assertion lacks the explicitly mandated machine-scope null-guard comment | File: skills/brief-portfolio/app/src/lib/derive.test.js:240 | Task: 6
[BOB] ⚪ The changed `process_store` remains 65 lines, above the 50-line limit; it was already 64 lines and correcting it requires an unrelated structural refactor | File: skills/purge-devlocal/scripts/purge_devlocal.py:400 | Task: 4
[BOB] ⚪ Cannot statically verify: required pytest, Node, build, validator, and `braid --check` checks pass | File: N/A | Task: general
[BOB] ⚪ Cannot statically verify: the live collect/build pipeline completes non-interactively and emits due or never-run audit rows | File: N/A | Task: 8
[BOB] ⚪ The prescribed HTML text search can find commands in the compiled bundle without executing JavaScript, so it cannot prove that rows rendered | File: N/A | Task: 8

R1: fail
R2: pass
R3: pass
R4: pass
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

FIX:
- Unhandled metrics-file read errors abort collection — skills/brief-portfolio/scripts/collect.py:304 — catch `OSError` around the read loop, return the seeded result, and add an unreadable-file test
- Zero-day retention removes the newly created cadence stamp — skills/purge-devlocal/scripts/purge_devlocal.py:438 — move the `mkdir` after `empty_old_trash` and add a `--empty-trash-days 0` regression test
- Legacy-key references violate Task 3's literal search acceptance — skills/brief-portfolio/scripts/test_collect.py:809 — rename the test and remove the redundant legacy-key assertion
- Full sorting is unnecessary for newest-directory selection — skills/brief-portfolio/scripts/collect.py:259 — use `max((...), default=None)`
- The collector test module exceeds 800 lines — skills/brief-portfolio/scripts/test_collect.py:1 — move the new cadence-focused tests into a separate test module
- The `externalTodos` comment describes only machine-scoped output — skills/brief-portfolio/app/src/lib/derive.js:336 — document both machine and repo audit rows
- The second null-guard assertion lacks its mandated rationale — skills/brief-portfolio/app/src/lib/derive.test.js:240 — add the machine-scope null-guard comment
VERIFY:
- Required automated checks were not executable in this review — run `uv run pytest`, both `validate_skill.py` checks, `npm --prefix skills/brief-portfolio/app run build`, `npm --prefix skills/brief-portfolio/app test`, and `braid --check`
- Live integration was not executable in this review — run `collect.py`, then `build.py --out dev/local/tmp/brief-check.html`, confirm noninteractive exits, and inspect the resulting audit rows
KNOWN:
- `process_store` remains above 50 lines — it was already 64 lines before this one-line task, and correcting it requires an unrelated purge-devlocal refactor
- Task 8's text-only rendered-HTML check can false-pass — the design explicitly excludes adding a browser/JSDOM execution test from this PRD's scope
```

Note on Bob's `R1: fail` / `R9: fail` / `R10: fail`: all three trace to the unguarded-`OSError`
finding (R10 error handling, R1 the missing test for it, R9 the PRD error-case behavior not
matching). They are not three independent defects.

## Carl

UI/design lens. This diff's only frontend surface is `derive.js`'s pure derivation and the
compiled bundle — no component, styling, or markup change — so Carl correctly reviewed as a
generalist rather than inventing frontend findings.

```
[CARL] 🟡 Reduce complexity (lines 316-325): deduplicate out.push object literals between scope branches by extracting a helper | File: skills/brief-portfolio/app/src/lib/derive.js | Task: 5
[CARL] ⚪ Stale comment above externalTodos still omits mention of repo-scoped rows | File: skills/brief-portfolio/app/src/lib/derive.js | Task: 5
[CARL] ⚪ Missing null-guard comment at second externalTodos(null) site | File: skills/brief-portfolio/app/src/lib/derive.test.js | Task: 6

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
R12: fail
R13: fail
```

## Eve

Doubt lens (Fable 5), added by the codex-rung guard. Verified the six namespaced audit keys
and the unnamespaced `purge-devlocal` against the real `skills.jsonl`, confirmed the purge stamp
survives `prune_empty_dirs` (which skips `.trash`) and default `empty_old_trash`, and inspected
the live Phase 2 render artifact rather than trusting the text-search acceptance.

```
[EVE] 🟡 collect_audit_cadence crashes the whole collect run on an unreadable skills.jsonl: `f.read_text()` has no OSError guard and the call at collect.py:488 is unwrapped, while the PRD error case demands "missing or unreadable -> collectors return None" and the sibling collect_claude_skill_adherence (lines 272-287) does guard OSError | File: skills/brief-portfolio/scripts/collect.py | Task: Phase 0
[EVE] 🟡 external.audit_cadence publishes every skill ever logged (confirmed in the rendered brief: use-gemini, git-ferry:catchup, design-solution, ~36 keys), while the PRD output spec says "{skill: newest ISO day} for the six machine-wide audits"; derive.js reads only 6 of them | File: skills/brief-portfolio/scripts/collect.py | Task: Phase 0
[EVE] 🟡 SKILL.md was never updated: `compatibility:` frontmatter still says "One dashboard row, Claude config maintenance, reads ~/.claude and reports 'never'" (that source was deleted), "Reads per repo" omits dev/local/.trash/ and skills.jsonl, and the step-2 do-not-duplicate list omits the new per-audit nags, so the model step may now duplicate them | File: skills/brief-portfolio/SKILL.md | Task: general
[EVE] ⚪ Stamp dir is created before empty_old_trash, so a legal `--empty-trash-days` value below 1 deletes today's stamp in the same run and silently defeats the fix commit 87334bf claims | File: skills/purge-devlocal/scripts/purge_devlocal.py | Task: general
[EVE] ⚪ Test-comment slop in the new derive tests: the block header attributes this work to "PRD 00081" (it is PRD 00006), and line 151's "null external yields no rows at all, audits included" duplicates line 119 (and pre-existing line 240) while overstating - repo-scope purge rows DO emit with null external when repos are passed, which the comment's claim never tests | File: skills/brief-portfolio/app/src/lib/derive.test.js | Task: Phase 1
[EVE] ⚪ Rebuilt template carries the expected symbols but full build fidelity against current app/src was not proven in-range | File: skills/brief-portfolio/assets/template.html | Task: Phase 2
[EVE] ⚪ Rows fire at exactly the horizon (aged >= horizonDays) while PRD prose says "older than its horizon"; deliberately pinned by the exact-horizon tests and consistent with the old MAINT_DUE_DAYS behavior | File: skills/brief-portfolio/app/src/lib/derive.js | Task: Phase 1
[EVE] ⚪ PRD acceptance letter "rg claude_maintenance_last returns nothing over scripts/" is unmet: test_collect.py:809/819 still reference the literal, as a negative regression guard | File: skills/brief-portfolio/scripts/test_collect.py | Task: Phase 0
[EVE] ⚪ Repos with no dev/local at all still get a "Run /purge-devlocal" never row - the collector cannot distinguish "no dev/local" from "never purged" | File: skills/brief-portfolio/scripts/collect.py | Task: Phase 0
[EVE] ⚪ Pre-migration or --offline-reused data.json (no audit_cadence, no purge_last_run) renders up to 6+N false "never" rows until the next real collect | File: skills/brief-portfolio/app/src/lib/derive.js | Task: Phase 2
[EVE] ⚪ test_main_external_carries_audit_cadence... drives main() without isolating $HOME, so it reads the developer's real skills.jsonl; assertions only check seeded-key presence so it cannot flake, matching the pre-existing main-test pattern | File: skills/brief-portfolio/scripts/test_collect.py | Task: Phase 0

FIX:
- Unreadable skills.jsonl crashes collect.py (PRD error case says return the seeded dict) — skills/brief-portfolio/scripts/collect.py:304 — wrap the read_text/parse loop in try/except OSError returning `result`, mirroring collect_claude_skill_adherence:272-287
- audit_cadence payload ships every skill in the log instead of the PRD's six machine audits — skills/brief-portfolio/scripts/collect.py:318 — only update keys already seeded (`if skill in result`), seeding MACHINE_AUDIT_SKILLS plus "purge-devlocal" so the stated Phase 0 acceptance and existing tests keep passing
- SKILL.md describes the removed one-row ~/.claude mtime design — skills/brief-portfolio/SKILL.md:4 — rewrite the compatibility line, add skills.jsonl and dev/local/.trash/ to Dependencies, and add the per-audit cadence nags to the step-2 do-not-duplicate list
- Stamp mkdir precedes empty_old_trash so --empty-trash-days <1 deletes today's stamp in the same run — skills/purge-devlocal/scripts/purge_devlocal.py:438 — move the mkdir after the empty_old_trash call (one-line reorder; both are behind the same args.apply gate)
- New test block misattributes the work to PRD 00081 and line 151 duplicates the null-external assertion at line 119 under an overstated comment — skills/brief-portfolio/app/src/lib/derive.test.js:106 — change the attribution to PRD 00006 and delete the duplicate assert.deepEqual at 150-151 (line 119 already pins it)
VERIFY:
- assets/template.html may not be a faithful build of current app/src (symbol presence checked, byte fidelity not) — run `npm --prefix skills/brief-portfolio/app install && npm --prefix skills/brief-portfolio/app run build && diff skills/brief-portfolio/app/dist/index.html skills/brief-portfolio/assets/template.html` and require an empty diff
KNOWN:
- Rows fire at exactly the horizon (>=) while PRD prose says "older than" — the PRD's own success metric only pins horizon±1, the >= choice matches the prior MAINT_DUE_DAYS behavior, and the exact-horizon tests pin it deliberately; re-litigating the boundary is out of scope
- PRD acceptance "rg claude_maintenance_last returns nothing" is unmet by test_collect.py:809/819 — the surviving reference is the negative regression guard pinning the key's removal; deleting it to satisfy the letter would weaken the suite
- Repos without any dev/local still get a purge-devlocal "never" row — the collector cannot distinguish the cases, the PRD mandates per-repo "never" rows, and the existing brush nag accepts the identical imprecision for never-brushed repos
- Old or --offline-reused snapshots render up to 6+N "never" rows until the next real collect — transient by construction and "never" is the honest reading of a payload that carries no stamp; snapshot migration is out of this PRD's scope
- test_main_external test reads the real ~/.local/share/agents/metrics/skills.jsonl via main() — pre-existing run_collector pattern (skill_adherence already did this), and the assertions cannot fail on real content; hermetic main() isolation is out of scope

D1: pass
D2: pass
D3: pass
D4: pass
D5: pass
```

## Consolidated Findings

Produced by `consolidate_findings.py` across all five reviewers.

| Consensus | Severity | Issue | File | Task | Found By |
|-----------|----------|-------|------|------|----------|
| [3/5] | ⚪ | Comment above `externalTodos` still describes the old single-nag channel, not the now-repo-scoped one | skills/brief-portfolio/app/src/lib/derive.js | 5 | ALICE, BOB, CARL |
| [3/5] | ⚪ | Second `externalTodos(null)` regression site missing the null-guard comment the task spec required at both sites | skills/brief-portfolio/app/src/lib/derive.test.js | 6 | ALICE, BOB, CARL |
| [2/5] | 🟠 | `collect_audit_cadence` doesn't catch `OSError` on `f.read_text()` (unlike sibling `collect_claude_skill_adherence`), and is called unguarded in `main()` unlike `collect_external`; an unreadable-but-present `skills.jsonl` crashes the whole run instead of degrading to "never" rows per the PRD's explicit Error-case scenario, and no test covers it | skills/brief-portfolio/scripts/collect.py | general | BLAKE, EVE |
| [2/5] | 🟡 | test_collect.py is 819 lines, over the 800-line file-size limit (758->819 this PRD) | skills/brief-portfolio/scripts/test_collect.py | general | ALICE, BOB |
| [2/5] | 🟡 | process_store is 65 lines, over the 50-line function limit (pre-existing at 64, this PRD added 1) | skills/purge-devlocal/scripts/purge_devlocal.py | 4 | ALICE, BOB |
| [2/5] | 🟡 | Creating today's stamp before retention means `--empty-trash-days 0` immediately deletes it; create the stamp after `empty_old_trash` and test that case | skills/purge-devlocal/scripts/purge_devlocal.py:438 | 4 | BOB, EVE |
| [2/5] | ⚪ | Phase 0 task 3's literal acceptance criterion ("`rg claude_maintenance_last` over `scripts/` ... returns nothing, and `test_collect.py` has no test referring to it") is not met verbatim — `test_collect.py` still names the string twice in a regression test proving its absence; harmless but a literal spec-text miss | skills/brief-portfolio/scripts/test_collect.py | general | BLAKE, EVE |
| [1/5] | 🟠 | Unreadable or concurrently removed `skills.jsonl` raises `OSError` and aborts the entire collector instead of returning the seeded never-run map | skills/brief-portfolio/scripts/collect.py:304 | 1 | BOB |
| [1/5] | 🟡 | The required `rg claude_maintenance_last` acceptance check still returns two test references; rename the test and remove its redundant negative assertion | skills/brief-portfolio/scripts/test_collect.py:809 | 3 | BOB |
| [1/5] | 🟡 | `collect_purge_devlocal` sorts every matching directory only to select one; replace the list and indexing with `max(generator, default=None)` | skills/brief-portfolio/scripts/collect.py:259 | 2 | BOB |
| [1/5] | 🟡 | Reduce complexity (lines 316-325): deduplicate out.push object literals between scope branches by extracting a helper | skills/brief-portfolio/app/src/lib/derive.js | 5 | CARL |
| [1/5] | 🟡 | external.audit_cadence publishes every skill ever logged (confirmed in the rendered brief: use-gemini, git-ferry:catchup, design-solution, ~36 keys), while the PRD output spec says "{skill: newest ISO day} for the six machine-wide audits"; derive.js reads only 6 of them | skills/brief-portfolio/scripts/collect.py | Phase 0 | EVE |
| [1/5] | 🟡 | SKILL.md was never updated: `compatibility:` frontmatter still says "One dashboard row, Claude config maintenance, reads ~/.claude and reports 'never'" (that source was deleted), "Reads per repo" omits dev/local/.trash/ and skills.jsonl, and the step-2 do-not-duplicate list omits the new per-audit nags, so the model step may now duplicate them | skills/brief-portfolio/SKILL.md | general | EVE |
| [1/5] | ⚪ | Cannot statically verify: required pytest, Node, build, validator, and `braid --check` checks pass | N/A | general | BOB |
| [1/5] | ⚪ | Cannot statically verify: the live collect/build pipeline completes non-interactively and emits due or never-run audit rows | N/A | 8 | BOB |
| [1/5] | ⚪ | The prescribed HTML text search can find commands in the compiled bundle without executing JavaScript, so it cannot prove that rows rendered | N/A | 8 | BOB |
| [1/5] | ⚪ | Test-comment slop in the new derive tests: the block header attributes this work to "PRD 00081" (it is PRD 00006), and line 151's "null external yields no rows at all, audits included" duplicates line 119 (and pre-existing line 240) while overstating - repo-scope purge rows DO emit with null external when repos are passed, which the comment's claim never tests | skills/brief-portfolio/app/src/lib/derive.test.js | Phase 1 | EVE |
| [1/5] | ⚪ | Rebuilt template carries the expected symbols but full build fidelity against current app/src was not proven in-range | skills/brief-portfolio/assets/template.html | Phase 2 | EVE |
| [1/5] | ⚪ | Rows fire at exactly the horizon (aged >= horizonDays) while PRD prose says "older than its horizon"; deliberately pinned by the exact-horizon tests and consistent with the old MAINT_DUE_DAYS behavior | skills/brief-portfolio/app/src/lib/derive.js | Phase 1 | EVE |
| [1/5] | ⚪ | Repos with no dev/local at all still get a "Run /purge-devlocal" never row - the collector cannot distinguish "no dev/local" from "never purged" | skills/brief-portfolio/scripts/collect.py | Phase 0 | EVE |
| [1/5] | ⚪ | Pre-migration or --offline-reused data.json (no audit_cadence, no purge_last_run) renders up to 6+N false "never" rows until the next real collect | skills/brief-portfolio/app/src/lib/derive.js | Phase 2 | EVE |
| [1/5] | ⚪ | test_main_external_carries_audit_cadence... drives main() without isolating $HOME, so it reads the developer's real skills.jsonl; assertions only check seeded-key presence so it cannot flake, matching the pre-existing main-test pattern | skills/brief-portfolio/scripts/test_collect.py | Phase 0 | EVE |

**Consolidation note (fail loud):** the unguarded-`OSError` defect appears as TWO rows — `[2/5]`
(BLAKE, EVE) and `[1/5]` (BOB) — because Bob's `File:` field carries a `:304` line suffix that
the paraphrase matcher treats as a different file. Its real consensus is **3/5**, the highest
of any substantive finding this cycle. The decision gate treats it as one finding at 3/5.

Similarly, the `rg claude_maintenance_last` literal-acceptance miss appears three times
(`[2/5]` BLAKE+EVE, `[1/5]` BOB) for the same reason — real consensus 3/5.

## Verdict and tests

Verdict: 22 findings
Tests: 451 passed, 0 failed, 5 skipped
