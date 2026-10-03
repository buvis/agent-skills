---
prd: dev/local/prds/wip/00016-queue-lands-in-wrong-repo-v1.md
review: 2
date: 2026-09-06
head_sha: e2ff3d4f1da8655416e44b49f6d21f2f551a712c
codex_thread_id: 01a073da-f17c-75c0-9ed6-8ac3c4e05a3a
reviewers: alice,blake,bob,carl
agents:
  alice: available
  blake: available
  bob: available
  carl: available
---

# Review: 00016-queue-lands-in-wrong-repo-v1

Diff range: `45a0adf518dc23b250c9d8844f8e91e5b45b3ee8..e2ff3d4f1da8655416e44b49f6d21f2f551a712c`

codex_rung_guard: not fired

Scope: INCREMENTAL review, cycle 2. The range is the rework commits only (`29de25f`,
`e2ff3d4`), scoped via `gather-context.sh --since 45a0adf5` from cycle 1's `head_sha`.
Bob resumed his cycle-1 codex session via `--resume-thread`, so he verified his own prior
critique rather than re-reviewing from zero.

pack: unavailable this cycle — `engram pack` exited 1 (`not inside a registered repo; register it
in ~/.config/gita/repos.csv`), the same failure as cycle 1. Every prompt carrying
`{PACK_FILE}`/`{PACK_FINDINGS}` got the `(no pack available this cycle)` sentinel instead. The
review is degraded on retrieval context, not invalid.

Carl backend: copilot, model `gemini-3.8-flash` (from the runner's stderr).

Mechanical checks: the tautological-shapes block found no `[MECH]` lines across 53 test
functions in 2 test files. The fail-first replay reported `replay: skipped (the diff touches no
test function)` — the cycle-2 test edits swap a local `_proposal()` for an imported
`make_proposal` and touch no test function body. No `[MECH]` finding to absorb.

Carry-forward: cycle 1 wrote no `checks-1.json` (no doubt lens emitted a VERIFY bucket), so
there were no prior failed checks to carry into this cycle's table.

## Consolidated Findings

| Consensus | Severity | Issue | File | Task | Found By |
|-----------|----------|-------|------|------|----------|
| [1/4] | ⚪ Low | Cannot statically verify: checks pass after rework. VERIFY: run `uv run pytest`, `uv run python3 skills/create-skill/scripts/validate_skill.py skills/distil-memory`, and `braid --check`. | N/A | 5 | BOB |

Consolidation was run by `consolidate_findings.py` with `--ledger` and `--ledger-dismiss BLAKE`
against the 3-entry settled-decisions ledger. It emitted no `### Auto-dismissed (ledger)` section:
Blake found nothing this cycle, so no Blake finding matched a settled entry.

**All four cycle-1 rework findings are resolved.** Alice, Bob and Carl each verified them
independently in the scoped diff:

- `SKILL.md:271-272` now reads both the cursor **and** the entry count from `<queue-path>`
  (cycle 1: only the cursor did). Closes the [2/4] BOB+CARL finding.
- `CHANGELOG.md` gained both entries — the `--queue` flag under Added, and the `save`
  default-queue-location change under Fixed. Closes the 🟠 High ALICE finding.
- `_proposal()` duplication is gone: `skills/distil-memory/scripts/docket_test_helpers.py`
  exports `make_proposal` (11 lines), imported by both `test_docket.py` and
  `test_docket_cli.py`, matching the existing `funnel_test_helpers.py` precedent. Closes the
  🟡 Medium ALICE finding.
- The obsolete four-line comment at `test_docket_cli.py:13-18` is replaced with an accurate
  one distinguishing `save`'s derived-path tests from the other four subcommands' cwd-walk
  tests. Closes the 🟡 Medium BOB finding.

No reviewer found a regression introduced by the rework.

**Not queued for verification, and no task created.** The single row is Bob's mandated
sandbox output for a criterion needing runtime verification — `agents/bob.md` orders exactly
this line shape when a criterion cannot be checked statically. It defines no FIX/VERIFY/KNOWN
buckets and Eve did not run (the codex doubt-roster guard did not fire), so no doubt lens
emitted a VERIFY bucket and no `checks-2.json` was written. The three commands it names are the
same three `dev/local/autopilot/last-verification.json` records at this exact HEAD, all exit 0
— see the `Tests:` line — and Alice and Carl each re-ran them live this cycle with the same
result. A rework task here would re-run a suite that already ran green at this commit.

## Alice

Consensus lens (Claude subagent). No issues found. She verified each of the four cycle-1
findings resolved in `45a0adf..e2ff3d4`, and confirmed via `uv run pytest
skills/distil-memory/scripts -q` (570 passed, 1 xfailed — pre-existing, in `test_write.py`,
unrelated to this diff), `validate_skill.py skills/distil-memory` (OK), and `braid --check`
(0 drift). She also checked the ruff flags on `test_docket.py`/`test_docket_cli.py` (unused
`json` import, unsorted imports, a few >100-char lines) against `45a0adf`'s blobs and confirmed
every one pre-dates this diff — pre-existing, out of scope for an incremental review, and not
raised as a finding.

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

## Blake

Blind lens (PRD-only; no diff, no file list, no review history). Blake located the code himself
and verified the spec's three must-haves independently, including that all seven actual
`docket.py` command invocations in `SKILL.md` carry `--queue` (he checked that the remaining
`docket.py` mention is prose, not an invocation). No issues found — his first fully clean sheet
on this PRD; his two cycle-1 ⚪ Low findings were settled deferrals and he did not re-raise them.

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

Doubt + de-slop lens (codex, static-only sandbox; resumed thread
`01a073da-f17c-75c0-9ed6-8ac3c4e05a3a` from cycle 1). No issues found. His two cycle-1 `R4` and
`R9` fails — both tracing to the `SKILL.md:272` step-7 finding — are now `pass`: the walkthrough
reads both values from `<queue-path>`, so the changed component integrates with its own caller
and the behavior matches the PRD's intent. His one remaining line is the sandbox
cannot-statically-verify row above, not a defect.

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

Consensus lens (gemini-3.8-flash via copilot). No issues found. He ran `uv run pytest
skills/distil-memory/scripts -q`, `validate_skill.py skills/distil-memory`, `braid --check` and
the full `uv run pytest`, then read `SKILL.md:260-285` and the two `CHANGELOG.md` entries
directly to confirm each cycle-1 finding closed. He reports no regressions in the diff.

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

Verdict: 1 findings
Tests: 1024 passed, 0 failed, 5 skipped (reused from last-verification.json at e2ff3d4f1da8655416e44b49f6d21f2f551a712c)
