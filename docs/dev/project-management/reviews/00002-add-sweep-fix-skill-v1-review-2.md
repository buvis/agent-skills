---
prd: dev/local/prds/wip/00002-add-sweep-fix-skill-v1.md
review: 2
date: 2026-08-29
head_sha: 52398e2985ee4f48f1ac953f3d53499301be6fef
codex_thread_id: 01a04d2a-010a-7460-8aa5-94f1461122d8
reviewers: alice,blake,bob,carl
agents:
  alice: available
  blake: available
  bob: available
  carl: available
---

# Review: 00002-add-sweep-fix-skill-v1

Diff range: `dbca5489649ab9634720db109dd7c8feb99debdf..52398e2985ee4f48f1ac953f3d53499301be6fef`

codex_rung_guard: not fired

## Review Summary

Reviewed: 17 completed tasks (8 original plan tasks, 9 `[D1]` rework tasks)
PRDs checked: 00002-add-sweep-fix-skill-v1.md

Scope: **incremental** review of the cycle 1 rework. 28 commits, 11 files, 2241
insertions and 1069 deletions:

- `skills/sweep-fix/SKILL.md` (36 changed lines)
- `skills/sweep-fix/scripts/sweep.py` (391 changed lines)
- `skills/sweep-fix/scripts/test_sweep.py` (957 lines, deleted)
- `skills/sweep-fix/scripts/conftest.py`, `sweep_test_helpers.py` and six
  `test_sweep_*.py` modules (new, the split of `test_sweep.py`)

### Agent Status

- Alice (Claude, consensus lens): ✅ Available
- Blake (Claude, blind/PRD-only lens): ✅ Available
- Bob (codex, doubt + de-slop lens): ✅ Available, resumed his cycle 1 codex
  thread `01a04d2a-…` via `--resume-thread`
- Carl (gemini via copilot backend, UI/generalist lens): ✅ Available

All four lenses ran. Eve was not activated: the codex doubt-roster guard did not
fire (zero tasks carry `attempts[].implementor == "codex"`; every task in this
PRD was implemented by Claude Sonnet).

### Run notes (fail loud)

1. **The engram context pack was not generated, again.** `engram pack` exits 1
   with `not inside a registered repo; register it in
   /Users/bob/.config/gita/repos.csv`. `(no pack available this cycle)` was
   substituted for `{PACK_FILE}` and `{PACK_FINDINGS}` in every prompt, per the
   skill's own fallback. No retry was attempted: the failure is deterministic
   (a registry-membership check, not a transient error) and was already
   confirmed in cycle 1. The review is degraded on retrieval context, not
   invalid.
2. **The mechanical-facts block lives in its own file, not appended to the
   context file.** aegis's `block_devlocal_redirects.py` hook blocks shell
   redirects into `dev/local/`, and rewriting the whole 869-line context file
   through the Write tool to append 134 lines was not worth the tokens. The
   block was written to `dev/local/tmp/review-mechfacts-20260829-c2.md` and
   named as an explicit additional input in Alice's, Bob's and Carl's prompts
   (not Blake's, whose lens stays blind). Bob cited it directly in one finding.
3. **`gather-context.sh` needed `--since` again.** This repo's work lands
   directly on `master`, so the script's base-branch detection yields an empty
   diff. Run with `--since dbca548…` (cycle 1's `head_sha`), which is the
   correct scope for an incremental cycle anyway.

Consolidation ran through `consolidate_findings.py` (not model-side), with
`--ledger dev/local/reviews/00002-add-sweep-fix-skill-v1-ledger.json
--ledger-dismiss BLAKE`.

## Consolidated Findings

### Consensus correction (fail loud)

`consolidate_findings.py` under-merged one group again: it matches on file
string plus description, so Bob's `sweep.py:312` spelling of the duplicated
control-repo scan landed as a separate `[1/4]` row from the `[2/4]` row it
belongs to. Corrected consensus, used for gate prioritisation:

| True consensus | Severity | Defect | Reviewers |
|----------------|----------|--------|-----------|
| **[3/4]** | 🟡 Medium | `verify_control()` rescans `control_repo` after the portfolio scan already covered it | Alice, Carl, Bob |

Every other row stands at the consensus the script computed.

### Cycle 1 findings: all nine rework tasks verified resolved

Alice and Blake each independently confirmed the rework landed. No cycle 1
finding reproduces:

- the `~/.buvis` bare-repo entry is now a single `{"cwd", "files"}` scan scope
  with `cwd=` pinned on the `ls-files` call (tested with `monkeypatch.chdir`);
- `_scan_rg` inserts `--` before the pattern;
- `import yaml` is gone, replaced by a round-trip-tested hand-rolled scalar
  quoter;
- `--out` is anchored under `--cwd` and refuses escapes;
- `verify_control()` runs only after `scan()`, only on an all-zero result;
- the uncovered-languages line is gated on `kind == "astgrep"`;
- the how-to-proceed block states both the current-repo-only rule and the
  approval requirement, and its test binds to both;
- `SKILL.md` uses the portable `~/.agents/skills/sweep-fix/scripts/sweep.py`
  invocation, states the `HEAD` default, and `main()` prints the report path;
- `--cap` rejects non-positive values, and `test_sweep.py` is split into eight
  files all under 800 lines with no loss of test count.

### Critical (blocking)

None. Zero critical findings this cycle, down from four.

### High (blocking)

- [1/4] 🟠 `verify_control()`'s fallback literal-search call is wrapped in a
  broad `try/except Exception` that prints a warning to stderr and returns
  `None` on any failure, including the `resolve_rg()` `RuntimeError` this same
  cycle introduced. Alice reproduced it live: with `rg`, `ast-grep` and the
  claude-binary fallback all unresolvable, `sweep.main()` returns 0 and writes a
  report instead of aborting loud. `verify_control()` also discards `scan()`'s
  `failed` channel (bound to `_failed`), so it cannot tell "genuinely 0 hits"
  from "could not scan at all". Contradicts the PRD's resolver "loud failure"
  contract and task D1-T2's own "do not swallow the per-repo error silently".
  The one new test for this branch covers only a nonexistent `control_repo` in
  isolation, not the tool-unresolvable case wired through `main()`. |
  `skills/sweep-fix/scripts/sweep.py:329-337` | Task: 10 | Found by: Alice
- [1/4] 🟠 `enumerate_repos()` compares `--cwd` to on-disk repo paths by exact
  equality with no walk-up to the git root. Blake reproduced it live from
  `skills/sweep-fix/scripts/`: the repo root appears as a false registry gap
  while only the invoking subdirectory is actually scanned, so the current repo
  is simultaneously partially swept and reported as un-swept. Contradicts the
  PRD's "the current repo, registered or not" plus "never swept silently"
  contract. No `git rev-parse --show-toplevel`-style normalization exists
  anywhere in the module. | `skills/sweep-fix/scripts/sweep.py` |
  Task: Phase 0 (enumerate_repos) | Found by: Blake

### Medium

- [3/4] 🟡 `verify_control()` rescans `control_repo` with the same pattern after
  the portfolio scan already covered it, duplicating subprocess work; extract
  the independent literal-control check and reuse it from `main()` and
  `verify_control()` | `skills/sweep-fix/scripts/sweep.py:312` | Found by:
  Alice, Carl, Bob — carried over from cycle 1, where it was recorded as
  "not swept this cycle"
- [1/4] 🟡 `main()`'s `except RuntimeError` handler is dead code: `scan()`'s
  per-repo isolation and `verify_control()`'s own `try/except` now catch every
  `RuntimeError` the resolvers can raise before it reaches `main()`, and
  `enumerate_repos()` never raises one. Alice confirmed by forcing all three
  resolutions to fail: the handler never fires. |
  `skills/sweep-fix/scripts/sweep.py:576-583` | Task: 10 | Found by: Alice
- [1/4] 🟡 `enumerate_repos()` opens the registry CSV unguarded inside a list
  comprehension; a missing or unreadable `--registry` path raises
  `FileNotFoundError`/`OSError` that `main()`'s `except RuntimeError` does not
  catch, surfacing as a raw traceback rather than the loud-failure pattern used
  everywhere else | `skills/sweep-fix/scripts/sweep.py` | Found by: Blake
- [1/4] 🟡 `SKILL.md` still describes control verification before the portfolio
  scan, contradicting `main()`'s corrected all-zero-only ordering |
  `skills/sweep-fix/SKILL.md:40` | Task: D1-T5 | Found by: Bob
- [1/4] 🟡 The `brief-portfolio` dependency reference remains repo-relative and
  does not resolve when the installed skill runs outside this checkout |
  `skills/sweep-fix/SKILL.md:62` | Task: D1-T8 | Found by: Bob
- [1/4] 🟡 Resolver tests remain host-dependent through real `mise` calls and
  assumptions about `/usr/bin:/bin` |
  `skills/sweep-fix/scripts/test_sweep_resolvers.py:102` | Task: D1-T9 |
  Found by: Bob — note Alice judged the same tests host-independent after the
  D1-T9 split, so the two reviewers disagree on whether this still reproduces
- [1/4] 🟡 Conditional YAML scalar classification is needless complexity
  (`_needs_yaml_quoting` at 34 lines, `_yaml_scalar` at 7, per the computed
  mechanical-facts block); always serialize caller values with stdlib
  `json.dumps()` | `skills/sweep-fix/scripts/sweep.py:402` | Task: D1-T3 |
  Found by: Bob
- [1/4] 🟡 YAML round-trip tests repeat the same render, parse and equality
  assertions across adjacent functions; consolidate into one parametrized test |
  `skills/sweep-fix/scripts/test_sweep_render_report.py:429` | Task: D1-T3 |
  Found by: Bob
- [1/4] 🟡 The dash-pattern test retains a fail-first comment claiming the
  current code lacks `--`, which is no longer true |
  `skills/sweep-fix/scripts/test_sweep_scan.py:105` | Task: D1-T10 |
  Found by: Bob

### Low

- [1/4] ⚪ The PRD's "registry parsing reuses `collect.py:429`" is satisfied by
  duplicating the shape rather than importing it (that line is inline in a
  function body, not an importable helper). Documentation nuance, no functional
  defect. | `skills/sweep-fix/scripts/sweep.py:142` | Found by: Blake
- [1/4] ⚪ The report path is deterministic from `--reason` plus today's date
  with no collision check, so rerunning a sweep with the same reason on the same
  day silently overwrites the earlier report. Not addressed either way by the
  PRD. | `skills/sweep-fix/scripts/sweep.py` (`_resolve_report_path`) |
  Found by: Blake

### Auto-dismissed (ledger)

- [BLAKE] ⚪ PRD's "Exports" list documents `scan(pattern, repos, cap=20)` and
  `render_report(derivation, hits, gaps)`; shipped signatures are
  `scan(pattern, kind, repos, cap=20, timeout=DEFAULT_SCAN_TIMEOUT)` and
  `render_report(derivation, hits, gaps, suppressed, failed)` — functionally
  justified and well tested, but the literal interface contract in the PRD's
  Structural Decomposition is not preserved. |
  File: `skills/sweep-fix/scripts/sweep.py` — dismissed: the extra parameters
  are functionally required to satisfy other literal PRD requirements
  (kind-based dispatch, suppressed-count reporting), so this is an internal
  inconsistency in the PRD's own Exports list, not an implementation defect.
  Removing either parameter would break a stated Success Metric.

The dismissal is correct. Blake re-raised the exact call settled in cycle 1, and
his prompt is PRD-only by design, so he could not have known.

## Alice

Consensus lens, implementation-aware. Verified all nine cycle 1 rework items
resolved in the code, then hunted the rework itself for regressions. Ran the
suites: `uv run pytest` repo-wide 420 passed / 5 skipped;
`uv run pytest skills/sweep-fix` 96 passed; `validate_skill.py skills/sweep-fix`
OK; no em dashes in the changed files.

Her one High is a genuine new regression introduced by this cycle's own rework,
reproduced live rather than argued: the broad `except Exception` added to
`verify_control()`'s fallback path swallows the `RuntimeError` the same cycle
introduced in the resolvers.

Findings: 0 🔴, 1 🟠, 1 🟡, 1 ⚪.

```
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
R12: pass
R13: pass
```

## Blake

Blind lens — PRD only, no diff, no file list, no review history. Found the code
himself and reproduced his High live by running `enumerate_repos()` from a
subdirectory of the repo. Confirmed 96 tests pass and the create-skill validator
passes. He again flagged the phase-numbering mapping explicitly (this PRD
numbers phases 0/1/2, so B15→Phase 0, B16→Phase 1, B17→Phase 2), which is the
same reasonable reading accepted in cycle 1.

One of his five findings was auto-dismissed against the ledger (see above).

Findings: 0 🔴, 1 🟠, 1 🟡, 3 ⚪ (one dismissed).

```
B1: fail
B2: pass
B3: fail
B4: pass
B5: pass
B6: pass
B7: fail
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

Doubt + de-slop lens, codex, static-only sandbox, resumed from his cycle 1
thread so he verified his own prior critique rather than re-reviewing from zero.
No critical or high findings this cycle — a notable drop from 1 🔴 and 6 🟠 in
cycle 1. His seven mediums are mostly de-slop: over-built YAML quoting,
duplicated round-trip test bodies, a stale fail-first comment, and the SKILL.md
documentation drift the D1-T5 reorder created.

He raised no "cannot statically verify" line this cycle: the prompt carried the
orchestrator's already-run check results.

Doubt buckets: 7 FIX, 0 VERIFY, 0 KNOWN.

Findings: 0 🔴, 0 🟠, 7 🟡, 0 ⚪.

```
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
```

```
D1: pass
D2: pass
D3: pass
D4: pass
D5: pass
```

## Carl

Gemini via the copilot backend. Read the code directly across 30-odd targeted
reads and ran the skill's own suite. He raised a single finding, the duplicated
control-repo scan, which is the third voice on that medium. Every R-rule passes
in his judgment — the only reviewer with a clean rubric sheet this cycle.

Findings: 0 🔴, 0 🟠, 1 🟡, 0 ⚪.

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

## Gate outcome

Cycle 2 is the rework cap (`rework_cap: 2`). Two High findings remain
unresolved, so this cycle did not converge, and the loop-mode cap-out branch
applies: no Critical finding remains, so the PRD is not stalled. All 13
unresolved findings are recorded in `state.deferred_decisions` as
`cap-overflow` and surface at batch end; the PRD finalizes as
converged-with-deferrals.

Verdict: 13 findings
Tests: 420 passed, 0 failed, 5 skipped
