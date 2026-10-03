---
prd: dev/local/prds/wip/00036-create-skill-scripts-help-and-union-path-v1.md
review: 1
date: 2026-09-07
head_sha: a1b972ab5e40d33b9af37754bc0798dd97115e04
codex_thread_id: 01a0794a-84c5-7da3-ae11-18f33213e392
reviewers: alice,blake,bob,carl
agents:
  alice: available
  blake: available
  bob: available
  carl: available
---

# Review: 00036-create-skill-scripts-help-and-union-path-v1

Diff range: `35d6a6c538ae474496b9f1f4a5bfdb57b9ecc5cc..a1b972ab5e40d33b9af37754bc0798dd97115e04`

codex_rung_guard: not fired

pack: failed (`engram pack` exited 1 — "not inside a registered repo; register it in
`~/.config/gita/repos.csv`"). Every prompt carried the literal `(no pack available this cycle)`
in place of `{PACK_FILE}` / `{PACK_FINDINGS}`. The review is degraded, not invalid.

Diff-scope note: this is cycle 1, a FULL review. The work landed directly on `master`, so
`gather-context.sh`'s default `master...HEAD` base produced an empty diff; the diff was
re-gathered with `--since <work_start_sha>`, which is exactly the `work_start_sha..HEAD` range the
full-review rule prescribes. The context file's scope label was corrected to say so.

## Review Summary

Reviewed: 4 completed tasks
PRDs checked: 00036-create-skill-scripts-help-and-union-path-v1.md

### Agent Status

- Alice: ✅ Available (Claude subagent)
- Blake: ✅ Available (Claude subagent, blind lens)
- Bob: ✅ Available (codex; consensus + doubt/de-slop lens)
- Carl: ✅ Available (gemini via copilot backend, model `gemini-3.8-flash`)

## Consolidated Findings

Produced by `consolidate_findings.py` over four reviewer outputs.

| Consensus | Severity | Issue | File | Task | Found By |
|-----------|----------|-------|------|------|----------|
| [3/4] | 🟠 | Missing CHANGELOG.md entry for user-visible fix commits (validate_skill.py --help crash fix, init_skill.py stale path fix); the repo's standing rule (rules/changelog.md, restated in this PRD's own "Repository invariants" section) requires an `[Unreleased] > Fixed` entry in the same commit for every fix with user-visible impact, and none was added | CHANGELOG.md | general | ALICE, BOB, CARL |
| [1/4] | 🟡 | test_help_flag_exits_zero_with_usage_line and test_help_flag_prints_usage_and_exits_zero assert the same behavior (run `--help`, check exit 0, check stdout starts with "usage: validate_skill.py") almost verbatim; one is redundant | skills/create-skill/scripts/test_validate_skill.py | 2 | ALICE |
| [1/4] | 🟡 | test_validate_line_uses_interpreter_prefixed_union_path_and_skill_dir and test_printed_validate_step_names_the_union_path both assert the printed "3. Validate:" line contains the union path and omits the Claude-only path; largely overlapping coverage in the same new file | skills/create-skill/scripts/test_init_skill.py | 4 | ALICE |
| [1/4] | 🟡 | FIX: Duplicate `--help` tests cover the same behavior while the required `-h` alias is untested; replace both with the required-name test iterating over `("-h", "--help")` | skills/create-skill/scripts/test_validate_skill.py:99 | 2 | BOB |
| [1/4] | 🟡 | FIX: Two scaffolder tests duplicate the same output contract; keep `test_printed_validate_step_names_the_union_path`, use the existing module import, and fold the exact-line, single-line, and generated-directory assertions into it | skills/create-skill/scripts/test_init_skill.py:10 | 4 | BOB |
| [1/4] | 🟡 | FIX: The missing-argument test checks only exit code 2, leaving the PRD-required argparse diagnostic unpinned; assert stderr names the required `skill_path` argument | skills/create-skill/scripts/test_validate_skill.py:130 | 1 | BOB |
| [1/4] | 🟡 | Redundant test: test_help_flag_exits_zero_with_usage_line (lines 99-106) duplicates test_help_flag_prints_usage_and_exits_zero (lines 109-116); remove the earlier duplicate | skills/create-skill/scripts/test_validate_skill.py | 2 | CARL |
| [1/4] | 🟡 | Redundant test: test_printed_validate_step_names_the_union_path (lines 28-39) duplicates test_validate_line_uses_interpreter_prefixed_union_path_and_skill_dir (lines 10-25) with redundant local import; consolidate into Task 4's test | skills/create-skill/scripts/test_init_skill.py | 4 | CARL |
| [1/4] | ⚪ | FIX: The module docstring still claims this file tests only PRD 00083 bash lints despite the newly added CLI tests; replace it with a general `validate_skill.py` test description | skills/create-skill/scripts/test_validate_skill.py:1 | 2 | BOB |
| [1/4] | ⚪ | VERIFY: Cannot statically verify: run `uv run pytest skills/create-skill/scripts -q`, `uv run python3 skills/create-skill/scripts/validate_skill.py skills/create-skill`, `braid --check`, and the PRD's `--help`, `skills/survey/`, and `skills/sweep-fix/` commands | N/A | general | BOB |

**Consensus is understated on the duplicate-test rows.** `consolidate_findings.py` merges
paraphrases only when reviewers name the same file, and Bob's paths carry a `:line` suffix
(`...test_validate_skill.py:99`) while Alice's and Carl's do not. So the two duplicate-test
defects that three reviewers each found independently render as six `[1/4]` rows instead of two
`[3/4]` rows. The decision gate treats them as two findings at 3/4 consensus, matching on issue
text plus file as its own rule prescribes.

**`not queued: command shape`** — Bob's ⚪ VERIFY row names six commands in one line
(`uv run pytest ...`, `validate_skill.py skills/create-skill`, `braid --check`, and three PRD
commands). The verification-check queue takes one runnable command per entry, no chaining, so no
queue entry was written for it and no `dev/local/reviews/...-checks-1.json` exists this cycle.
The commands it names all ran green independently: see the `Tests:` line below and Alice's and
Blake's own executions.

## Alice

Consensus lens, implementation-aware. Ran `uv run pytest skills/create-skill/scripts -q`
(15 passed) and executed `validate_skill.py --help`, with no argument, and against
`skills/survey/` and `skills/sweep-fix/`; confirmed `.github/workflows/ci.yml` still passes a
single positional argument; grepped for stale `~/.claude/skills/create-skill/...` references
(none).

```
[ALICE] 🟠 Missing CHANGELOG.md entry for user-visible fix commits (validate_skill.py --help crash fix, init_skill.py stale path fix); the repo's standing rule (rules/changelog.md, restated in this PRD's own "Repository invariants" section) requires an `[Unreleased] > Fixed` entry in the same commit for every fix with user-visible impact, and none was added | File: CHANGELOG.md | Task: general
[ALICE] 🟡 test_help_flag_exits_zero_with_usage_line and test_help_flag_prints_usage_and_exits_zero assert the same behavior (run `--help`, check exit 0, check stdout starts with "usage: validate_skill.py") almost verbatim; one is redundant | File: skills/create-skill/scripts/test_validate_skill.py | Task: 2
[ALICE] 🟡 test_validate_line_uses_interpreter_prefixed_union_path_and_skill_dir and test_printed_validate_step_names_the_union_path both assert the printed "3. Validate:" line contains the union path and omits the Claude-only path; largely overlapping coverage in the same new file | File: skills/create-skill/scripts/test_init_skill.py | Task: 4
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

Blind lens (PRD-only prompt; no diff, no file list, no review history). Located the code himself
and executed every PRD success-criterion command: `uv run pytest skills/create-skill/scripts -q`
→ 15 passed; `--help` → exit 0 with `usage: validate_skill.py`; no argument → exit 2 with
argparse's own message; `skills/survey/` and `skills/sweep-fix/` (trailing slash, the CI loop's
exact shape) → both exit 0 with `[OK] Skill is valid!`; `init_skill.py` → printed the
interpreter-prefixed union path with no `~/.claude/skills/` literal. Confirmed the change set is
exactly the four files the PRD names, and that no new dependency was introduced.

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

Consensus + doubt/de-slop lens, codex, static-only sandbox.

```
[BOB] 🟡 FIX: Duplicate `--help` tests cover the same behavior while the required `-h` alias is untested; replace both with the required-name test iterating over `("-h", "--help")` | File: skills/create-skill/scripts/test_validate_skill.py:99 | Task: 2
[BOB] 🟡 FIX: Two scaffolder tests duplicate the same output contract; keep `test_printed_validate_step_names_the_union_path`, use the existing module import, and fold the exact-line, single-line, and generated-directory assertions into it | File: skills/create-skill/scripts/test_init_skill.py:10 | Task: 4
[BOB] 🟡 FIX: The missing-argument test checks only exit code 2, leaving the PRD-required argparse diagnostic unpinned; assert stderr names the required `skill_path` argument | File: skills/create-skill/scripts/test_validate_skill.py:130 | Task: 1
[BOB] ⚪ FIX: The module docstring still claims this file tests only PRD 00083 bash lints despite the newly added CLI tests; replace it with a general `validate_skill.py` test description | File: skills/create-skill/scripts/test_validate_skill.py:1 | Task: 2
[BOB] 🟡 FIX: The user-visible `create-skill` fixes have no entry under `[Unreleased]` → `Fixed`, contrary to the repository's changelog rule | File: CHANGELOG.md:49 | Task: general
[BOB] ⚪ VERIFY: Cannot statically verify: run `uv run pytest skills/create-skill/scripts -q`, `uv run python3 skills/create-skill/scripts/validate_skill.py skills/create-skill`, `braid --check`, and the PRD's `--help`, `skills/survey/`, and `skills/sweep-fix/` commands | File: N/A | Task: general
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
R12: pass
R13: pass
D1: pass
D2: pass
D3: pass
D4: pass
D5: pass
```

Bob's `R1: fail` is his only rubric failure and is explained by his own findings: he judges the
`-h` alias (a PRD must-have) and argparse's required-argument diagnostic as new behavior the diff
leaves untested. Alice and Carl passed R1. The rework tasks below close both gaps, so R1 is
re-evaluated next cycle rather than argued here.

## Carl

Gemini via copilot backend, model `gemini-3.8-flash`. Ran the full `uv run pytest` suite,
`validate_skill.py skills/create-skill`, and `braid --check`; read `CHANGELOG.md` and grepped for
surviving `~/.claude/skills/create-skill` references (none found).

```
[CARL] 🟡 Redundant test: test_help_flag_exits_zero_with_usage_line (lines 99-106) duplicates test_help_flag_prints_usage_and_exits_zero (lines 109-116); remove the earlier duplicate | File: skills/create-skill/scripts/test_validate_skill.py | Task: 2
[CARL] 🟡 Redundant test: test_printed_validate_step_names_the_union_path (lines 28-39) duplicates test_validate_line_uses_interpreter_prefixed_union_path_and_skill_dir (lines 10-25) with redundant local import; consolidate into Task 4's test | File: skills/create-skill/scripts/test_init_skill.py | Task: 4
[CARL] ⚪ Missing [Unreleased] entries in CHANGELOG.md for user-visible create-skill script fixes | File: CHANGELOG.md | Task: general
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

- **Tautological test shapes**: 15 test functions across 2 test files checked, no `[MECH]` line.
- **Fail-first replay** against `35d6a6c538ae`: 2 touched tests ran, 2 failed against base,
  0 passed; 1 test file could not be collected at base (its tests fail there). No test passes
  against the pre-change code, so nothing is unpinned by shape.
- **Mechanical facts**: largest changed function is `validate_skill.validate_skill` at 160 lines
  (pre-existing, untouched by this diff); `validate_skill.main` is 35 lines. Largest changed file
  is 402 lines. No countable claim in any finding contradicts the block.

## Follow-up Tasks Created

1. `[D1] Add CHANGELOG [Unreleased] > Fixed entries for the two create-skill CLI fixes` (S) —
   🟠 3/4 consensus — addresses the CHANGELOG finding (task id 5)
2. `[D1] De-duplicate and tighten test_validate_skill.py's new CLI tests` (S) — 🟡/⚪ —
   addresses the duplicate `--help` tests, the untested `-h` alias, the unpinned argparse
   diagnostic, and the stale module docstring (task id 6)
3. `[D1] Fold test_init_skill.py's two overlapping scaffolder tests into one` (S) — 🟡 —
   addresses the duplicated scaffolder tests and the shadowing function-local import (task id 7)

Verdict: 10 findings
Tests: 1100 passed, 0 failed, 5 skipped (reused from last-verification.json at a1b972ab5e40d33b9af37754bc0798dd97115e04)
