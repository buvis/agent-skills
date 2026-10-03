---
prd: dev/local/prds/wip/00006-nag-audit-cadence-in-brief-portfolio-v1.md
review: 2
date: 2026-08-30
head_sha: 15228c862135f0dae5a5c3588c2f9193dae2bf11
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

Diff range: `dc7f536f6071d34b007908a4aa637f03e7bf02e1..15228c862135f0dae5a5c3588c2f9193dae2bf11`

codex_rung_guard: fired (1 codex-implemented task(s))

Scope note: this is cycle 2, an **incremental review** of cycle 1's rework only (11 commits,
9 files, 156 insertions / 34 deletions). The diff was scoped with
`gather-context.sh --since dc7f536…`, read from cycle 1's `head_sha`. Bob resumed his cycle-1
codex session via `--resume-thread 01a04f54-df14-7752-ba86-74f0c732b67a`, so he verified fixes
against his own prior critique rather than re-reviewing from zero. Working tree was clean at
`15228c8` throughout, so the reviewed diff is the shipped state.

pack: unavailable this cycle — the repo is not in the gita registry, so `engram pack` cannot
run here. Deterministic config state (identical on PRDs 00003, 00004 and cycle 1 of this PRD),
so no retry. Every implementation-aware prompt received the sentinel
`(no pack available this cycle)` for `{PACK_FILE}`/`{PACK_FINDINGS}`. Blake never receives a
pack by design.

ledger: present (13 entries from cycle 1). `consolidate_findings.py` ran with
`--ledger dev/local/reviews/00006-nag-audit-cadence-in-brief-portfolio-v1-ledger.json
--ledger-dismiss BLAKE`, and Alice, Bob, Carl and Eve each received the
"Settled decisions — do not re-raise" section built from it. Blake did not, by design.

Codex doubt-roster guard: task 4's attempt carries `implementor: "codex"`, so the resolved
doubt reviewer was forced to `fable` in memory and **Eve ran as a fifth lens**. Bob (codex)
still ran and still carried the doubt rubric, so the guard added a voice rather than replacing
one. Both doubt reviewers produced usable output, so the constraint is met with no suffix.

## Agent Status

- Alice: ✅ Available (consensus lens, Claude subagent, `consensus_engine: legacy`)
- Blake: ✅ Available (blind lens, PRD-only)
- Bob: ✅ Available (consensus + doubt lens, codex, static-only, resumed thread)
- Carl: ✅ Available (UI/design lens, gemini via copilot backend)
- Eve: ✅ Available (doubt lens, Fable 5 — added by the codex-rung guard)

## Alice

Verified by running, not by reading: `pytest test_collect.py test_purge_devlocal.py` → 95 passed;
`node --test derive.test.js` → all assertions passed; `git status` clean at `15228c8`.

Reported all 8 prior-cycle findings resolved, correctly and completely: the `externalTodos`
comment (derive.js:336-338), the second `externalTodos(null)` null-guard comment
(derive.test.js:119) with the duplicated overstating block deleted, the `OSError` guard
(collect.py:308-311) plus the guarded `main()` call site via `collect_external_section`
(collect.py:461-472) backed by three new regression tests, the trash-stamp reorder
(purge_devlocal.py:437-439) pinned by
`test_zero_day_retention_does_not_delete_todays_own_fresh_stamp`, `max(..., default=None)`
(collect.py:259), the extracted `row()` helper (derive.js:314-316) emitting byte-identical rows,
the SKILL.md refresh, and the PRD-number comment fix.

Regression check on the rework itself: none found. `collect_external_section`'s extraction
(`15228c8`) is clean — sole call site preserved, `main()` down to 44 lines, no dead imports. The
SPA was rebuilt alongside each derive.js refactor commit (`fde1c18`, `4fb082f` each touch
`template.html`), not left stale.

```
[ALICE] ⚪ test_main_writes_data_json_when_audit_cadence_raises_unexpected_exception's assertion (`"audit_cadence" in new_data["external"] or "audit_cadence" in captured.err`) is a disjunctive OR that doesn't pin the documented fallback value (`_seeded_audit_cadence()`); it wouldn't catch a regression where the outer catch-all in collect_external_section populates audit_cadence with e.g. `{}` instead of the seeded 6-key dict, since the stderr-mentions-the-string branch alone would still pass | File: skills/brief-portfolio/scripts/test_collect.py | Task: 9

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

Blind, PRD-only. Located the code himself and ran both suites live: `pytest
scripts/test_collect.py -q` → 55 passed; `npm test` → 16/16. Confirmed
`collect_audit_cadence(base=None)` and `collect_purge_devlocal(path)` carry the specified
signatures, `MACHINE_AUDIT_SKILLS` lists the six namespaced audits, `collect_claude_maintenance` /
`claude_maintenance_last` are fully removed, `AUDIT_CADENCE` defines exactly seven rows at the
specified 30d/90d split, and the row-state tests pin age-0 / horizon-1 / horizon+1 / never for
both horizons. Confirmed no interactive prompt anywhere in `collect.py` / `build.py`, and that
the command field renders as static text never wired to a click handler — the PRD's
"name the command, run nothing" behaviour.

```
[BLAKE] 🟡 Filtering the brief to a single org sets `external={null}` (App.svelte `ext = org === 'all' ? external : null`), which is passed straight into `Todos`/`Matrix`. Because `auditTodos()` is wired through `externalTodos()` (as the PRD's own structural decomposition mandates), this silently suppresses the per-repo `purge-devlocal` cadence rows for that org's own repos whenever the view is filtered — the one row scope that is genuinely repo-local. | File: skills/brief-portfolio/app/src/App.svelte | Task: general
[BLAKE] ⚪ `collect_audit_cadence`'s "no lookback cutoff" behavior (explicitly required, unlike the 30-day adherence collector) is correct by inspection (no date filter in the code) but has no explicit regression test proving a very old timestamp (e.g. >90d) still wins as "newest." | File: skills/brief-portfolio/scripts/test_collect.py | Task: Phase 0
[BLAKE] 🟠 Pre-existing, out-of-scope for this PRD but data-safety relevant: `purge-devlocal`'s `process_store` loop can destroy freshly trashed files in the same run under `--apply --empty-trash-days 0`, bypassing the trash-first safety net. Flagged for awareness only since this PRD's cadence rows point users at `/purge-devlocal` as the remediation command. | File: skills/purge-devlocal/scripts/purge_devlocal.py | Task: general

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

Resumed codex thread `01a04f54-df14-7752-ba86-74f0c732b67a`. Static analysis only, per his
sandbox. Notably he emitted **no** "Cannot statically verify" lines this cycle — the ledger's two
cycle-1 discards of exactly those lines reached his prompt and suppressed them.

```
[BOB] 🟡 The unexpected-exception test accepts either a fallback key or a warning, so it passes when half the required degrade-and-warn contract is broken; assert both the exact seeded map and stderr warning | File: skills/brief-portfolio/scripts/test_collect.py:901 | Task: 9
[BOB] 🟡 After extracting `row`, the `why` helper has one caller and adds needless indirection; inline its expression into the row builder | File: skills/brief-portfolio/app/src/lib/derive.js:312 | Task: 12
[BOB] 🟡 `_seeded_audit_cadence` has a docstring that only restates its implementation; remove it | File: skills/brief-portfolio/scripts/collect.py:295 | Task: 9
[BOB] ⚪ The public collector docstring omits the newly added unreadable-file fallback behavior | File: skills/brief-portfolio/scripts/collect.py:299 | Task: 9

R1: fail
R2: fail
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

D1: pass
D2: pass
D3: pass
D4: pass
D5: pass

FIX:
- The call-site regression test does not enforce both fallback signals — skills/brief-portfolio/scripts/test_collect.py:901 — assert the exact seeded cadence dictionary and `WARN audit_cadence` stderr text separately
- `why` became a single-caller helper after row-builder extraction — skills/brief-portfolio/app/src/lib/derive.js:312 — inline the expression into `row`
- The private seed-helper docstring paraphrases the next line — skills/brief-portfolio/scripts/collect.py:295 — remove the docstring
- The public collector documentation omits unreadable-file behavior — skills/brief-portfolio/scripts/collect.py:299 — document that missing or unreadable files return the seeded map
VERIFY:
- (none)
KNOWN:
- (none)
```

Note on Bob's `R1: fail` / `R2: fail`: both are his statement of the test-assertion weakness he
files above as a Medium (the `or` disjunction not binding to intent), not a claim that new
behaviour is untested. Alice, Carl and the orchestrator's own run of the suites all read the same
code as R1/R2 pass. The decision gate treats the underlying defect as the finding and sweeps it;
the rubric split is noted, not silently reconciled.

## Carl

Ran `npm --prefix skills/brief-portfolio/app test` (16/16) and
`pytest test_collect.py test_purge_devlocal.py` before reporting. Confirmed the extracted `row`
helper preserves the exact object shape (UI consistency), and that `template.html` was rebuilt to
match.

```
[CARL] ✅ No issues found

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

Note: Carl's `R12: pass` / `R13: pass` contradict the computed mechanical facts
(`process_store` 65 lines, `test_collect.py` 901 lines). Alice's and Bob's `fail` is the correct
reading; both failures are the two settled deferrals recorded in the ledger.

## Eve

Fable 5, doubt + de-slop lens. Independently re-checked: `pytest` 95 passed;
`node --test derive.test.js` green; `npm test` 16/16 green; and a fresh `vite build` producing
`dist/index.html` **byte-identical** to `assets/template.html` — a fresh answer to cycle 1's
settled item 10, now against a template rebuilt twice more in this range. Confirmed the fail-first
ordering of both fixes from the commit graph (`0b455f9`/`77bfe19` precede `d6b84db`; `55cfc4d`
precedes `8a296aa`).

```
FIX:
- Fail-first comment left in future tense plus a weakened `or` assertion: the test cannot fail if a future edit drops the seeded `audit_cadence` fallback but keeps the WARN print — skills/brief-portfolio/scripts/test_collect.py:893-901 — now that the fix has landed both signals hold, so change the disjunction to assert the key (or the exact seeded map) AND the stderr WARN, and reword the comment to present tense.
- `_seeded_audit_cadence` docstring restates its one-line body verbatim ("Seed dict with all MACHINE_AUDIT_SKILLS keys as None.") — skills/brief-portfolio/scripts/collect.py:294-296 — delete the docstring or make it state the reason the helper exists (single-sources the seed between the collector and the crash fallback in collect_external_section).
VERIFY:
- Phase 2's live exit criterion has not been re-exercised since the external-payload path was refactored into `collect_external_section` (commit 15228c8); tests cover it but no live run does — run `python3 skills/brief-portfolio/scripts/collect.py` followed by `python3 skills/brief-portfolio/scripts/build.py --out dev/local/tmp/brief-check.html` on this machine and confirm the run completes with no prompt and the rendered file still carries one row per due/never audit naming its command.
KNOWN:
- A valid-JSON log row whose `ts` is not a string (e.g. an int) raises TypeError in `iso_day` inside `collect_audit_cadence`, and the new outer guard then degrades the ENTIRE cadence map to "never" instead of skipping that one row — out of scope: the parsing loop pre-dates this range (cycle-1 reviewed), the only writer (~/.claude/hooks/track_skills.py) always emits ISO strings, and this range's guard already converts the theoretical crash into a graceful degrade.
- derive.test.js lines 119 and 237 are now assertion- and comment-identical duplicates of each other — out of scope: the task spec behind prior finding #2 explicitly required the null-guard comment at both sites, so deduping further would contradict the settled instruction.

D1: pass
D2: pass
D3: pass
D4: pass
D5: pass
```

## Consolidated Findings

Produced by `consolidate_findings.py` across all five reviewers, with the cycle-1 ledger passed
as `--ledger … --ledger-dismiss BLAKE`.

| Consensus | Severity | Issue | File | Task | Found By |
|-----------|----------|-------|------|------|----------|
| [1/5] | 🟠 | Pre-existing, out-of-scope for this PRD but data-safety relevant: `purge-devlocal`'s `process_store` loop can destroy freshly trashed files in the same run under `--apply --empty-trash-days 0`, bypassing the trash-first safety net | skills/purge-devlocal/scripts/purge_devlocal.py | general | BLAKE |
| [1/5] | 🟡 | Filtering the brief to a single org sets `external={null}` (App.svelte), which allegedly suppresses the per-repo `purge-devlocal` cadence rows for that org's repos | skills/brief-portfolio/app/src/App.svelte | general | BLAKE |
| [1/5] | 🟡 | The unexpected-exception test accepts either a fallback key or a warning, so it passes when half the required degrade-and-warn contract is broken; assert both the exact seeded map and stderr warning | skills/brief-portfolio/scripts/test_collect.py:901 | 9 | BOB |
| [1/5] | 🟡 | After extracting `row`, the `why` helper has one caller and adds needless indirection; inline its expression into the row builder | skills/brief-portfolio/app/src/lib/derive.js:312 | 12 | BOB |
| [1/5] | 🟡 | `_seeded_audit_cadence` has a docstring that only restates its implementation; remove it | skills/brief-portfolio/scripts/collect.py:295 | 9 | BOB |
| [1/5] | 🟡 | Fail-first comment left in future tense plus a weakened `or` assertion: the test cannot fail if a future edit drops the seeded `audit_cadence` fallback but keeps the WARN print | skills/brief-portfolio/scripts/test_collect.py | 9 | EVE |
| [1/5] | 🟡 | `_seeded_audit_cadence` docstring restates its one-line body verbatim; delete it or make it state why the helper exists | skills/brief-portfolio/scripts/collect.py | 9 | EVE |
| [1/5] | ⚪ | test_main_writes_data_json_when_audit_cadence_raises_unexpected_exception's assertion is a disjunctive OR that doesn't pin the documented fallback value (`_seeded_audit_cadence()`) | skills/brief-portfolio/scripts/test_collect.py | 9 | ALICE |
| [1/5] | ⚪ | `collect_audit_cadence`'s "no lookback cutoff" behavior is correct by inspection but has no explicit regression test proving a very old timestamp (e.g. >90d) still wins as "newest" | skills/brief-portfolio/scripts/test_collect.py | Phase 0 | BLAKE |
| [1/5] | ⚪ | The public collector docstring omits the newly added unreadable-file fallback behavior | skills/brief-portfolio/scripts/collect.py:299 | 9 | BOB |
| [1/5] | ⚪ | Phase 2's live exit criterion has not been re-exercised since the external-payload path was refactored into `collect_external_section` (commit 15228c8) | skills/brief-portfolio/scripts/collect.py | 8 | EVE |
| [1/5] | ⚪ | KNOWN (out of scope): a non-string `ts` raises TypeError in `iso_day`, and the new outer guard then degrades the ENTIRE cadence map to "never" instead of skipping that one row | skills/brief-portfolio/scripts/collect.py | general | EVE |
| [1/5] | ⚪ | KNOWN (out of scope): derive.test.js lines 119 and 237 are now assertion- and comment-identical duplicates of each other | skills/brief-portfolio/app/src/lib/derive.test.js | 12 | EVE |

**Consolidation note (fail loud):** the weak-assertion defect in
`test_main_writes_data_json_when_audit_cadence_raises_unexpected_exception` appears as THREE rows
— BOB `[1/5]` (`…test_collect.py:901`), EVE `[1/5]` (`…test_collect.py`) and ALICE `[1/5]`
(`…test_collect.py`) — because Bob's `File:` field carries a `:901` line suffix and the three
descriptions diverge enough that the paraphrase matcher did not merge them. Its **real consensus
is 3/5**, the highest of any finding this cycle. The `_seeded_audit_cadence` docstring likewise
appears twice (BOB with `:295`, EVE without) for the same reason — **real consensus 2/5**. The
decision gate treats each as one finding at its real consensus.

**Auto-dismissal note (fail loud):** the ledger's `--ledger-dismiss BLAKE` filter did **not**
dismiss Blake's 🟠 re-raise of the `--empty-trash-days 0` data-loss item, even though it is
ledger entry 13 (`settled-deferral`, high). Blake reworded it substantially ("Pre-existing,
out-of-scope … flagged for awareness only"), so the matcher saw a different string. The decision
gate excluded it as a settled deferral by judgment, per the Cap check's settled-deferral rule.
No `### Auto-dismissed (ledger)` section was emitted this cycle.

## Verdict and tests

Verdict: 13 findings
Tests: 439 passed, 0 failed, 5 skipped
