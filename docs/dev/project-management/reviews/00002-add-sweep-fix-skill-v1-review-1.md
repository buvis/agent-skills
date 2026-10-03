---
prd: dev/local/prds/wip/00002-add-sweep-fix-skill-v1.md
review: 1
date: 2026-08-29
head_sha: dbca5489649ab9634720db109dd7c8feb99debdf
codex_thread_id: 01a04d2a-010a-7460-8aa5-94f1461122d8
reviewers: alice,blake,bob,carl
agents:
  alice: available
  blake: available
  bob: available
  carl: available
---

# Review: 00002-add-sweep-fix-skill-v1

Diff range: `70b9553f0fdcbec0dbfdd75349cf3fe9fcbf694f..dbca5489649ab9634720db109dd7c8feb99debdf`

codex_rung_guard: not fired

## Review Summary

Reviewed: 8 completed tasks
PRDs checked: 00002-add-sweep-fix-skill-v1.md

Scope: full review of the PRD's whole work range. Three new files, 1437
insertions, no pre-existing code touched:

- `skills/sweep-fix/SKILL.md` (72 lines)
- `skills/sweep-fix/scripts/sweep.py` (408 lines)
- `skills/sweep-fix/scripts/test_sweep.py` (957 lines)

### Agent Status

- Alice (Claude, consensus lens): ✅ Available
- Blake (Claude, blind/PRD-only lens): ✅ Available
- Bob (codex, doubt + de-slop lens): ✅ Available
- Carl (gemini via copilot backend, UI/generalist lens): ✅ Available

All four lenses ran. Eve was not activated: the codex doubt-roster guard did
not fire (zero tasks carry `attempts[].implementor == "codex"`; every task in
this PRD was implemented by Claude Sonnet).

### Run notes (fail loud)

Three degradations in the review scaffolding this cycle. None of them changed
a verdict, and all three are recorded rather than papered over.

1. **`gather-context.sh` produced an empty diff on its first run.** The script
   detects a base branch and diffs `HEAD` against it; this repo's work lands
   directly on `master`, so `git diff master` was empty and the first context
   file carried no `### Changed Files` section at all. Re-run with
   `--since 70b9553f…` (the PRD's `work_start_sha`) to get the correct
   1455-line diff. The `_Diff scope:_` line the script then wrote said
   "incremental review", which is wrong for a cycle-1 full review, and was
   corrected in the context file before dispatch. Reviewers received the
   correct full-range diff.
2. **The engram context pack was not generated.**
   `engram pack` exited 1 with `not inside a registered repo; register it in
   /Users/bob/.config/gita/repos.csv`. `(no pack available this cycle)` was
   substituted for `{PACK_FILE}` and `{PACK_FINDINGS}` in every prompt, per the
   skill's own fallback. The review is degraded on retrieval context, not
   invalid. Worth noting that `agent-skills` being absent from the gita
   registry is the same registry-gap condition this PRD's own `enumerate_repos`
   gap list exists to surface.
3. **The mechanical-facts block lives in its own file, not appended to the
   context file.** aegis's `block_devlocal_redirects.py` hook blocks shell
   redirects into `dev/local/`, and rewriting the whole 790-line context file
   through the Write tool to append 84 lines was not worth the tokens. The
   block was written to
   `dev/local/tmp/review-mechfacts-20260829-c1.md` and named as an explicit
   additional input in Alice's, Bob's and Carl's prompts (not Blake's — his
   lens stays blind). Every implementation-aware reviewer carried it; Carl's
   transcript confirms he read all 84 lines.

Consolidation ran through `consolidate_findings.py` (not model-side). No
`--ledger` flags: cycle 1 had no ledger file yet.

## Consolidated Findings

The script's raw table is reproduced verbatim below the correction. Read the
correction first.

### Consensus correction (fail loud)

`consolidate_findings.py` under-merged paraphrases this cycle. It matches on
file string plus description, so the same defect described in different words,
or attributed to `sweep.py` by one reviewer and `sweep.py:97` by another,
landed as separate `[1/4]` rows. Seven groups are affected. The corrected
consensus, used for gate prioritisation:

| True consensus | Severity | Defect | Reviewers |
|----------------|----------|--------|-----------|
| **[4/4]** | 🟡 Medium | `test_sweep.py` is 957 lines, over the 800-line cap | Alice, Blake, Bob, Carl |
| **[3/4]** | 🔴 Critical | buvis-bare enumeration returns FILE paths that `scan()` then uses as a subprocess `cwd` | Alice, Carl, Bob |
| **[3/4]** | 🟠 High | `import yaml` is an undeclared runtime dependency | Alice, Bob, Blake |
| **[3/4]** | 🟠 High | default `--out` resolves against process cwd, not `--cwd` | Carl, Bob, Blake |
| **[2/4]** | 🔴 Critical | `_scan_rg` passes the pattern to `rg` with no `--` separator | Alice, Carl |
| **[2/4]** | 🟠 High | all-zero sweep accepted when the control term is absent | Bob, Blake |
| **[2/4]** | 🟡 Medium | rg/ast-grep flags drift from the design doc's documented shape | Alice, Carl |

The remaining rows stand at the consensus the script computed.

### Full Consensus (4/4)

- [4/4] 🟡 `test_sweep.py` is 957 lines, over the 800-line file cap in
  `rules/coding-style.md` (confirmed against the computed mechanical-facts
  block) | `skills/sweep-fix/scripts/test_sweep.py` | Found by: Alice, Blake,
  Bob, Carl

This is the only finding every reviewer raised. The build's own step-7.0 style
gate already caught it and recorded `style_gate: "failed:FILE | 957 lines"` on
the sanctioned fail-loud-and-proceed path, and the most recent commit
(`dbca548`) claims in its subject to have fixed exactly this. The split was
insufficient.

### Critical (blocking)

- [3/4] 🔴 `enumerate_repos()` appends individual tracked **file** paths for the
  `~/.buvis` bare-cwd case, but `scan()` uses every `repos` entry as a
  subprocess `cwd`. Alice reproduced `NotADirectoryError: [Errno 20] Not a
  directory` directly. Since `--cwd` defaults to `Path.cwd()`, running the CLI
  from `$HOME` — the exact scenario the PRD calls a named special case —
  crashes the whole pipeline. The two buvis-bare tests only exercise
  `enumerate_repos()` in isolation, never through `scan()`. |
  `skills/sweep-fix/scripts/sweep.py:125-138` | Task: 2 | Found by: Alice,
  Carl, Bob
- [2/4] 🔴 `_scan_rg` calls `_run_rg(["--json", pattern, "."], repo)` with no
  `--` before the positional pattern. Alice reproduced it against a real `rg`
  binary: pattern `-x` is consumed as `--line-regexp` and the search silently
  returns 0 hits on content that should match, with no error. This is the
  silent-false-clean-sweep failure class `verify_control()` exists to catch,
  and it is not guaranteed to catch this variant. `verify_control()`'s own
  literal search at line 262 already uses `-F --` correctly, so the fix is a
  one-line change with in-file precedent. The ast-grep path fails loud instead
  (clap rejects it, exit 2), so only the `rg` path misbehaves silently. |
  `skills/sweep-fix/scripts/sweep.py:183-195` | Task: 3 | Found by: Alice, Carl
- [1/4] 🔴 The `~/.buvis` `git ls-files -z` call sets no `cwd=`, so it inherits
  whatever the OS process cwd happens to be. Blake reproduced it live: passing
  `cwd='/Users/bob'` while the real process cwd was the scripts directory
  returned 0 buvis files instead of 293. It works only when the process cwd is
  coincidentally `$HOME`. `test_enumerate_repos_uses_git_ls_files_for_buvis_bare_cwd`
  passes by accident — its fixture `work_tree` is disjoint from pytest's cwd, so
  git applies no prefix restriction. This is precisely the cwd-relative-pathspec
  trap the PRD names as the reason the special case exists. |
  `skills/sweep-fix/scripts/sweep.py:125-138` | Task: 2 | Found by: Blake
- [1/4] 🔴 `SKILL.md` documents invoking the script as
  `python3 skills/sweep-fix/scripts/sweep.py`, a repo-relative path. The
  installed skill is reached through `~/.agents/skills/sweep-fix/`, so the
  documented invocation fails anywhere outside the `agent-skills` checkout. |
  `skills/sweep-fix/SKILL.md:31` | Task: 7 | Found by: Bob

### High (blocking)

- [3/4] 🟠 `sweep.py:11` imports third-party PyYAML at module load, used only by
  `_render_astgrep_rule_block`, so even an `rg`-kind invocation fails at import
  time without it. Verified independently at the gate: `pyproject.toml` declares
  no `[project].dependencies` at all; `pyyaml>=6` sits only in
  `[dependency-groups].dev` alongside pytest and ruff. `SKILL.md`'s documented
  invocation is a bare `python3`, not `uv run --group dev`. Every other skill
  script in this repo is stdlib-only, and the design doc's own constraint is
  "stdlib only except subprocess calls to external binaries". |
  `skills/sweep-fix/scripts/sweep.py:11` | Found by: Alice, Bob, Blake
- [3/4] 🟠 `main()`'s default `--out` is a relative path resolved against the OS
  process cwd at write time, not against `--cwd`. A caller passing a `--cwd`
  different from the launch directory writes the report into the wrong repo's
  `dev/local/`. Bob adds that nothing confines a resolved `--out` to the
  invoking repo at all. | `skills/sweep-fix/scripts/sweep.py:396-402` |
  Found by: Carl, Bob, Blake
- [1/4] 🟠 `verify_control()` runs before the portfolio scan in `main()`, so it
  can abort a sweep even when the pattern has valid hits elsewhere. This
  contradicts `verify_control()`'s own docstring: "Never called when the
  pattern DID find hits anywhere -- only guards the all-zero case." |
  `skills/sweep-fix/scripts/sweep.py:366` | Task: 6 | Found by: Bob
- [1/4] 🟠 `render_report()`'s "Uncovered languages" line is computed from any
  hit lacking an `AST_GREP_LANGUAGES` mapping regardless of
  `derivation["kind"]`. On a textual `rg`-kind sweep — the PRD's own second
  happy path — `.md`/`.yml`/`.json` hits are normal, yet the report claims
  "Uncovered languages (no ast-grep lang mapping)" when no ast-grep rule was
  ever derived. Blake confirmed by rendering a minimal rg-kind report. It should
  be gated on `kind == "astgrep"` exactly as `_render_astgrep_rule_block`
  already is. No test covers the rg-kind case. |
  `skills/sweep-fix/scripts/sweep.py:274-285` | Task: 5 | Found by: Blake
- [1/4] 🟠 `scan()` has no per-repo error isolation: a `RuntimeError` from any
  single repo propagates through `scan()` and `main()`, no report is written,
  and every hit already collected from the other ~27 repos is lost. No
  subprocess call in the module sets a timeout, so one hung repo blocks the
  sweep indefinitely. The design doc's own review log flagged the missing
  timeout as a non-blocker. |
  `skills/sweep-fix/scripts/sweep.py:217-242` | Task: 3 | Found by: Blake
- [1/4] 🟠 The rendered how-to-proceed block says "If it is a real problem, fix
  it directly", omitting per-hit approval and the current-repo-only
  restriction that is the skill's core safety rule and a named PRD feature. |
  `skills/sweep-fix/scripts/sweep.py:335` | Task: 5 | Found by: Bob
- [2/4] 🟠 `SKILL.md`'s dependency references use repo-relative, Claude-only and
  plugin-cache paths that do not resolve across the hosts this cross-agent
  skills repo targets. | `skills/sweep-fix/SKILL.md:60-72` | Task: 7 |
  Found by: Carl, Bob

### Medium

- [2/4] 🟡 rg/ast-grep invocation flags drift from the design doc's documented
  shape (`-n --no-heading`, `--json=compact`; code uses `--json` for both) —
  **settled this cycle, see ledger** | Found by: Alice, Carl
- [1/4] 🟡 `main()` never prints the report path that `SKILL.md` step 3 tells the
  agent to read from stdout | `skills/sweep-fix/SKILL.md:48` | Found by: Bob
- [1/4] 🟡 The skill neither implements nor documents the PRD's stated `HEAD`
  default when no sha or range is supplied | `skills/sweep-fix/SKILL.md:15` |
  Found by: Bob
- [1/4] 🟡 Negative `--cap` values are accepted: `cap=-1` makes the cap
  comparison always true, yielding a suppressed count of `len+1` and silently
  dropping the last hit via `repo_hits[:-1]` |
  `skills/sweep-fix/scripts/sweep.py:366` | Found by: Bob
- [1/4] 🟡 Resolver tests depend on host PATH state: one fails when a real `rg`
  exists, and another does not force the fallback its name claims to test |
  `skills/sweep-fix/scripts/test_sweep.py:25` | Found by: Bob
- [1/4] 🟡 The how-to-proceed test only asserts a non-empty tail, so it cannot
  detect missing or unsafe required instructions (R2: does not bind to intent) |
  `skills/sweep-fix/scripts/test_sweep.py:691` | Found by: Bob
- [1/4] 🟡 `verify_control()` and the main `scan()` both scan `control_repo`,
  duplicating subprocess work | `skills/sweep-fix/scripts/sweep.py` |
  Found by: Alice — **not swept this cycle**; task D1-T5 changes this call site
  and may resolve it incidentally
- [1/4] 🟡 `scan()`/`render_report()` signatures carry extra parameters beyond
  the PRD's Exports list — **settled this cycle, see ledger** | Found by: Blake
- [1/4] 🟡 `verify_control()` proceeds silently when both pattern and control
  term are absent — **settled this cycle, see ledger** | Found by: Blake

### Low

- [1/4] ⚪ `verify_control` message uses `--` rather than the design doc's em
  dash — **discarded, see ledger** | Found by: Carl
- [1/4] ⚪ "Cannot statically verify: full pytest, skill-validator and braid
  checks pass" — **discarded, see ledger**; this is Bob's sandbox note, and the
  orchestrator ran the checks | Found by: Bob

## Alice

Consensus lens, implementation-aware. Ran the code directly rather than reading
only: reproduced both criticals with live execution (`NotADirectoryError` for
the buvis-bare `cwd` case; a real `rg --json -x` returning 0 matches on content
that should match). Ran the skill's own suite: 45 passed, 0 skipped.

Verified as working correctly: `resolve_rg`/`resolve_ast_grep` caching and
fallback logic, `enumerate_repos`'s two-level gap depth filter, `scan()`'s
per-repo cap and suppressed-count logic, `render_report()`'s pure-string
guarantee and ast-grep rule-block round-trip, the read-only regression test, and
`SKILL.md` (validator passes, description 242/250 chars).

Findings: 2 🔴, 1 🟠, 3 🟡.

```
R1: fail
R2: pass
R3: pass
R4: fail
R6: pass
R7: fail
R8: fail
R9: fail
R10: pass
R11: pass
R12: pass
R13: fail
```

## Blake

Blind lens — PRD only, no diff, no file list, no review history. Found the code
himself and reproduced his critical live (`enumerate_repos()` returning 0 buvis
files instead of 293 when the process cwd is not `$HOME`). Confirmed 45 tests
pass and the create-skill validator passes.

He flagged one rubric-mapping assumption explicitly: this PRD numbers its phases
0/1/2, not 1/2/3, so he mapped B15→Phase 0, B16→Phase 1, B17→Phase 2. Accepted
as a reasonable reading; it does not change any verdict.

Findings: 1 🔴, 2 🟠, 3 🟡, 2 ⚪.

```
B1: fail
B2: pass
B3: fail
B4: pass
B5: fail
B6: pass
B7: pass
B8: fail
B9: pass
B10: pass
B11: pass
B12: pass
B13: pass
B14: pass
B15: fail
B16: fail
B17: pass
B18: pass
B19: pass
```

## Bob

Doubt + de-slop lens, codex, static-only sandbox. The broadest finding set: 1 🔴,
6 🟠, 7 🟡, 1 ⚪. He is the only reviewer who caught the `SKILL.md` repo-relative
script path, the `verify_control`-before-`scan` ordering bug, the how-to-proceed
block's missing approval requirement, the unprinted report path, the missing
`HEAD` default, and the negative-`--cap` arithmetic.

Doubt buckets: 14 FIX, 1 VERIFY, 0 KNOWN. The single VERIFY item is the sandbox
limitation ("run `uv run pytest`, the validator, and `braid --check`"), which the
orchestrator discharged this cycle.

```
R1: fail
R2: fail
R3: pass
R4: fail
R6: pass
R7: fail
R8: pass
R9: fail
R10: fail
R11: pass
R12: pass
R13: fail
```

```
D1: pass
D2: pass
D3: pass
D4: pass
D5: pass
```

## Carl

Gemini via the copilot backend. Independently reproduced both of Alice's
criticals, and was the second voice on the `--out` process-cwd bug and the
`SKILL.md` plugin-cache path. His one low finding (em dash) was discarded at the
gate for contradicting `rules/writing.md`.

Findings: 2 🔴, 2 🟠, 3 🟡, 1 ⚪.

```
R1: fail
R2: pass
R3: pass
R4: fail
R6: pass
R7: fail
R8: fail
R9: fail
R10: pass
R11: pass
R12: pass
R13: fail
```

## Follow-up Tasks Created

Nine themed `[D1]` rework tasks, all at tier `sonnet` (the PRD carries no
frontmatter, so the `default_model` floor passes through). Under the 10-task
scope alarm, so no `scope-overflow` deferral.

1. D1-T1 `sweep.py`: fix the `~/.buvis` bare-repo enumeration (M) — 🔴 3/4 + 🔴 1/4
2. D1-T2 `sweep.py`: `--` separator and per-repo scan error isolation (M) — 🔴 2/4 + 🟠 1/4
3. D1-T3 `sweep.py`: drop the undeclared PyYAML runtime dependency (S) — 🟠 3/4
4. D1-T4 `sweep.py`: anchor and confine the report output path (S) — 🟠 3/4
5. D1-T5 `sweep.py`: only run `verify_control` on an all-zero sweep (S) — 🟠 1/4
6. D1-T6 `sweep.py`: gate the uncovered-languages line on `astgrep` kind (S) — 🟠 1/4
7. D1-T7 `sweep.py` + test: how-to-proceed block carries the safety rule (S) — 🟠 1/4 + 🟡 1/4
8. D1-T8 `SKILL.md` + `sweep.py`: portable invocation contract (M) — 🔴 1/4 + 🟠 2/4 + 🟡 2/4
9. D1-T9 `sweep.py` + `test_sweep.py`: `--cap` validation, split the 957-line test module, de-couple resolver tests from host PATH (M) — 🟡 4/4 + 🟡 2/4

Five findings were settled or discarded at the gate rather than reworked; each
carries its reason in
`dev/local/reviews/00002-add-sweep-fix-skill-v1-ledger.json`.

Verdict: 32 findings
Tests: 369 passed, 0 failed, 5 skipped
