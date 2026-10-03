---
prd: dev/local/prds/wip/00036-create-skill-scripts-help-and-union-path-v1.md
review: 2
date: 2026-09-07
head_sha: 7254c47b6649feb03966a63c2f5527506c089b91
codex_thread_id: 01a0794a-84c5-7da3-ae11-18f33213e392
reviewers: alice,blake,bob,carl
agents:
  alice: available
  blake: available
  bob: available
  carl: available
---

# Review: 00036-create-skill-scripts-help-and-union-path-v1

Diff range: `a1b972ab5e40d33b9af37754bc0798dd97115e04..7254c47b6649feb03966a63c2f5527506c089b91`

codex_rung_guard: not fired

pack: failed (`engram pack` exited 1 — "not inside a registered repo; register it in
`~/.config/gita/repos.csv`"), the same deterministic precondition failure as cycle 1. Every
implementation-aware prompt carried the literal `(no pack available this cycle)` in place of
`{PACK_FILE}` / `{PACK_FINDINGS}`. The review is degraded, not invalid.

Diff-scope note: this is cycle 2, an INCREMENTAL review. `gather-context.sh` ran with
`--since a1b972ab5e40d33b9af37754bc0798dd97115e04` (cycle 1's `head_sha`), so the diff covers only
the three `[D1]` rework commits: `0359f43` (CHANGELOG), `a2818a9` (`test_validate_skill.py`),
`7254c47` (`test_init_skill.py`). Bob resumed his cycle-1 codex session via
`--resume-thread 01a0794a-84c5-7da3-ae11-18f33213e392`, so he verified his own critique rather than
re-reviewing from zero.

## Review Summary

Reviewed: 7 completed tasks (4 original-plan, 3 `[D1]` rework)
PRDs checked: 00036-create-skill-scripts-help-and-union-path-v1.md

### Agent Status

- Alice: ✅ Available (Claude subagent, consensus lens)
- Blake: ✅ Available (Claude subagent, blind lens — PRD-only prompt)
- Bob: ✅ Available (codex, resumed thread; consensus + doubt/de-slop lens)
- Carl: ✅ Available (gemini via copilot backend, model `gemini-3.8-flash`)

## Consolidated Findings

`consolidate_findings.py` over all four reviewer outputs returned
**`✅ No issues found - all agents passed`** — zero reviewer findings this cycle. The two rows below
are the mechanical fail-first replay lines, absorbed as findings per the step-6 absorption rule.

| Consensus | Severity | Issue | File | Task | Found By |
|-----------|----------|-------|------|------|----------|
| [1/4] | 🟡 | 1 touched test(s) pass against the pre-change code: test_printed_validate_step_names_the_union_path | skills/create-skill/scripts/test_init_skill.py | general | mech-check |
| [1/4] | 🟡 | 3 touched test(s) pass against the pre-change code: test_help_flag_prints_usage_and_exits_zero, test_short_help_flag_exits_zero_with_usage_line, test_missing_skill_path_argument_exits_two | skills/create-skill/scripts/test_validate_skill.py | general | mech-check |

**Both rows were discarded at the decision gate** (ledger entries written, cycle 2). Reason: the
replay's base for an INCREMENTAL cycle is `a1b972ab5e40` — cycle 1's HEAD, at which both production
fixes had ALREADY landed. This cycle's diff is test-only plus a CHANGELOG entry, so a touched test
passing against that base is the expected shape of a behavior-preserving test refactor, not an
unpinned test. Cycle 1's replay, against the true pre-PRD base `35d6a6c538ae`, reported 2 touched
tests run and **2 failed** against base with 0 passing — the tests do pin the change. See the
Mechanical checks section below.

**No verification-check queue was written this cycle.** The queue is fed from a doubt lens's VERIFY
bucket. Eve did not run (the codex doubt-roster guard did not fire — no task carries
`attempts[].implementor == "codex"`), and `agents/bob.md` defines no FIX/VERIFY/KNOWN buckets, so
`source: "bob"` does not apply. Bob raised no findings at all this cycle, so there was nothing to
queue regardless. No `-checks-2.json` exists.

**Nothing carried forward from cycle 1.** Cycle 1 wrote no `-checks-1.json` (its single ⚪ VERIFY row
was `not queued: command shape` — six commands on one line), so the carry-forward read found no
file, which is never an error.

### Auto-dismissed (ledger)

None. The one cycle-1 ledger entry (Bob's un-runnable VERIFY line) was not re-raised by any
reviewer, so `--ledger-dismiss BLAKE` had nothing to filter.

## Alice

Consensus lens, implementation-aware. Verified each of the five cycle-1 findings closed in the code,
then checked the scoped diff for regressions. Ran `uv run pytest -q` (1099 passed, 5 skipped, 9
xfailed, 0 failed) and `uv run pytest skills/create-skill/scripts -q` (14 passed); live-ran
`validate_skill.py --help`, `-h`, and the no-argument case.

Her per-finding verification:

1. **CHANGELOG (🟠, task 5)** — resolved. Both `**create-skill**:` bullets are inside the single
   `[Unreleased] > Fixed` section; no other section touched.
2. **Duplicate `--help` tests / untested `-h` (🟡, task 6)** — resolved.
   `test_help_flag_prints_usage_and_exits_zero` keeps the two PRD-verbatim asserts and tests
   `--help` only; `test_short_help_flag_exits_zero_with_usage_line` covers `-h`. Confirmed live:
   `-h` exits 0 and prints usage.
3. **Argparse diagnostic unpinned (🟡, task 6)** — resolved.
   `test_missing_skill_path_argument_exits_two` now asserts `"skill_path" in result.stderr`.
   Confirmed live: stderr reads `validate_skill.py: error: the following arguments are required:
   skill_path`, exit 2.
4. **Stale module docstring (⚪, task 6)** — resolved.
5. **Duplicate scaffolder tests / shadowing local import (🟡, task 7)** — resolved.
   `test_init_skill.py` holds one test, imports `init_skill` once at module level, and folds in the
   exact-line, single-line, and skill-dir assertions.

```
[ALICE] ✅ No issues found
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

Blind lens (PRD-only prompt; no diff, no file list, no review history). Located the code himself and
executed every PRD success-criterion command: `uv run pytest skills/create-skill/scripts -q` → 14
passed; `--help` → exit 0 with `usage: validate_skill.py`; `skills/survey/` and `skills/sweep-fix/`
(trailing slash, the CI loop's exact shape) → both exit 0 with `[OK] Skill is valid!`; no argument →
exit 2 with argparse's own message naming `skill_path`. Also ran the full CI-shaped loop over
`skills/*/` (all exit 0), `uv run ruff check` and `ruff format --check` (clean), and the whole-repo
suite (1099 passed, 5 skipped, 9 xfailed). Confirmed argparse is stdlib (no new dependency), no
extra flags beyond the required positional, and every pre-existing `~/.claude/skills/`
compatibility literal left untouched — only the one targeted print line changed.

```
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
```

## Bob

Consensus + doubt/de-slop lens, codex, static-only sandbox. Resumed his cycle-1 thread
(`01a0794a-84c5-7da3-ae11-18f33213e392`), so he judged the rework against his own prior critique.
All five of his cycle-1 findings are closed, and his cycle-1 `R1: fail` — the one rubric failure of
that cycle, resting on the untested `-h` alias and the unpinned argparse diagnostic — is now
`R1: pass`.

```
[BOB] ✅ No issues found
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

Bob emitted no FIX/VERIFY/KNOWN section this cycle because he raised no residual findings; D1-D5
pass vacuously over an empty finding set.

## Carl

Gemini via copilot backend, model `gemini-3.8-flash` (recorded from the runner's stderr:
`gemini-run: backend=copilot model=gemini-3.8-flash`), exit 0 with non-empty reviewer text. Read the
scoped diff and context, re-read `CHANGELOG.md`, both test files, and ran `uv run pytest
skills/create-skill/scripts -q`, `validate_skill.py skills/create-skill`, `braid --check`, and the
full `uv run pytest` suite.

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

## Mechanical checks

- **Tautological test shapes**: 14 test functions across 2 test files checked, no `[MECH]` line.
- **Fail-first replay** against `a1b972ab5e40`: 4 touched tests ran, 0 failed against base, 4
  passed; 0 test files failed to collect at base. Both resulting `[MECH]` lines are in the
  consolidated table above and were discarded at the decision gate — see the reason recorded there
  and in the ledger. The short version: this cycle's base already contains both production fixes,
  so the replay is measuring a test-only refactor against post-fix code. Cycle 1's replay, against
  the real pre-PRD base `35d6a6c538ae`, showed 2 run / 2 failed / 0 passed.
- **Mechanical facts**: largest changed function is
  `test_printed_validate_step_names_the_union_path` at 16 lines; largest changed file is
  `test_validate_skill.py` at 137 lines. No countable claim in any finding contradicts the block.

## Follow-up Tasks Created

✅ No follow-up tasks needed. All four reviewers passed the implementation; the only two table rows
are computed replay facts that the decision gate discarded with a verified reason, so there is
nothing actionable to sweep.

Verdict: 2 findings
Tests: 1099 passed, 0 failed, 5 skipped (reused from last-verification.json at 7254c47b6649feb03966a63c2f5527506c089b91)
