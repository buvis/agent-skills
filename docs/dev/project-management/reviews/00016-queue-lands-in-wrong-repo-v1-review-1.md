---
prd: dev/local/prds/wip/00016-queue-lands-in-wrong-repo-v1.md
review: 1
date: 2026-09-06
head_sha: 45a0adf518dc23b250c9d8844f8e91e5b45b3ee8
codex_thread_id: 01a073da-f17c-75c0-9ed6-8ac3c4e05a3a
reviewers: alice,blake,bob,carl
agents:
  alice: available
  blake: available
  bob: available
  carl: available
---

# Review: 00016-queue-lands-in-wrong-repo-v1

Diff range: `985b861a82574ce937c8156d7dfa411c25f1ddb2..45a0adf518dc23b250c9d8844f8e91e5b45b3ee8`

codex_rung_guard: not fired

Scope: FULL review, cycle 1. The range is `state.work_start_sha..HEAD`, this PRD's whole work
range. It was passed to `gather-context.sh` via `--since` because the work is committed straight
onto `master`, so the script's default `merge-base HEAD master` yielded an empty diff — an empty
diff must never reach the reviewers.

pack: unavailable this cycle — `engram pack` exited 1 (`not inside a registered repo; register it
in ~/.config/gita/repos.csv`). Every prompt carrying `{PACK_FILE}`/`{PACK_FINDINGS}` got the
`(no pack available this cycle)` sentinel instead. The review is degraded on retrieval context,
not invalid.

Carl backend: copilot, model `gemini-3.8-flash` (from the runner's stderr).

## Consolidated Findings

| Consensus | Severity | Issue | File | Task | Found By |
|-----------|----------|-------|------|------|----------|
| [2/4] | 🟡 Medium | FIX: Step 7 reads the cursor from `<queue-path>` but the entry count from cwd-relative `dev/local/audit-results/distil-memory-queue.json`. From another repo, this misreports drained versus capped or reads a missing file. Read both from `<queue-path>`. | skills/distil-memory/SKILL.md:272 | 4 | BOB, CARL |
| [2/4] | 🟡 Medium | 10 touched test(s) pass against the pre-change code: test_main_save_prints_added_n_of_m_counting_m_as_every_record_read_not_just_new_ones, test_main_start_returns_zero, test_main_next_prints_the_next_undecided_entry_as_one_line_of_json_and_returns_zero, test_main_next_prints_nothing_and_returns_one_when_nothing_is_available, test_main_decide_kept_records_the_decision_and_returns_zero, test_main_decide_dropped_records_the_decision_and_returns_zero +4 more. BOB's reading: unchanged relocations preserving existing behavior; rewriting their intent is outside this routing change, and all original CLI tests remain present. | skills/distil-memory/scripts/test_docket_cli.py | general | BOB, mech-check |
| [1/4] | 🟠 High | No CHANGELOG.md entry for this fix; the queue's default location changes for any `save` call without `--queue` (was `_report_dir()`'s cwd walk, now `--proposals-dir`'s parent), a user-visible behavior change, and none of this PRD's commits (985b861a..45a0adf5) touch CHANGELOG.md. Every other fix in this file's `[Unreleased] > Fixed` section carries an entry; this one does not. | CHANGELOG.md | general | ALICE |
| [1/4] | 🟡 Medium | `_proposal()` (11 lines) is duplicated byte-for-byte between test_docket.py:11-21 and the newly created test_docket_cli.py:11-21 — the split introduced this duplication; extract to a shared conftest.py fixture instead. | skills/distil-memory/scripts/test_docket_cli.py | 1 | ALICE |
| [1/4] | 🟡 Medium | FIX: Remove the obsolete four-line comment claiming every CLI test uses cwd-derived queues without explicit paths; the migrated save assertions now do the opposite. | skills/distil-memory/scripts/test_docket_cli.py:24 | 3 | BOB |
| [1/4] | ⚪ Low | PRD's Implementation section cites `test_docket.py:402-727` as the home of the `main()` CLI tests, but those tests now live in a separate `test_docket_cli.py`/`test_docket_exit_codes.py` (split before this PRD's commits) — spec-to-layout drift only, all required scenarios are still covered and passing. | skills/distil-memory/scripts/test_docket_cli.py | general | BLAKE |
| [1/4] | ⚪ Low | `_save_from_proposals_dir` reads `proposals.json` and each proposal's referenced file with unguarded `.read_text()` calls (no try/except), so a missing/unreadable proposals file surfaces as a raw traceback instead of the clean stderr+exit-code pattern used everywhere else in `docket.py`'s `main()`. Pre-existing (unchanged by this PRD's diff) and mitigated by the funnel's atomic proposals-directory publish, so low likelihood, but real. | skills/distil-memory/scripts/docket.py:203-211 | docket | BLAKE |
| [1/4] | ⚪ Low | Cannot statically verify: reported checks pass. VERIFY: run `uv run pytest`, `uv run python3 skills/create-skill/scripts/validate_skill.py skills/distil-memory`, and `braid --check`. | N/A | general | BOB |

Consolidation was run by `consolidate_findings.py` (no `--ledger` flags: cycle 1, no settled-decisions
ledger existed yet). The second row is the mechanical fail-first replay `[MECH]` line absorbed onto
BOB's row, which names the same file and the same relocated tests; its 🟡 severity is kept so the
finding stays visible rather than being folded down to BOB's ⚪.

**Not queued for verification.** BOB's last row names exact commands, but `agents/bob.md` defines no
FIX/VERIFY/KNOWN buckets and Eve did not run this cycle (the codex doubt-roster guard did not fire),
so no doubt lens emitted a VERIFY bucket and no `checks-1.json` was written. The three commands he
names all ran green at this exact HEAD anyway — see the `Tests:` line and Blake's and Carl's own runs
below.

## Alice

Consensus lens (Claude subagent). Two findings, both listed above: the missing CHANGELOG entry
(🟠 High) and the byte-for-byte `_proposal()` duplication between `test_docket.py` and the newly
created `test_docket_cli.py` (🟡 Medium).

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

Blind lens (PRD-only; no diff, no file list, no review history). Blake located the code himself and
ran `uv run pytest skills/distil-memory/scripts -q` → 570 passed, 1 xfailed, plus `rg` checks against
the three acceptance criteria: `--queue` count of 7 in `SKILL.md`, the `queue-path` derivation
sentence present, and `save`'s default derived from `--proposals-dir`'s parent. He reports the
implementation matches the PRD: all five subcommands accept `--queue`, `save` derives its default
unconditionally, existing CLI tests were repointed, and PRD 00015's exit-code coverage
(`test_docket_exit_codes.py`) is untouched and still passing. Two ⚪ Low findings, both listed above.

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

Doubt + de-slop lens (codex, static-only sandbox; thread `01a073da-f17c-75c0-9ed6-8ac3c4e05a3a`).
Four findings, all listed above. His `R4` and `R9` fails both trace to the `SKILL.md:272` finding —
the walkthrough's step 7 still reads the entry count from the cwd-derived path while every command
around it now takes `--queue`, so the changed component does not fully integrate with its own caller
and the behavior does not match the PRD's intent exactly.

```
R1: pass
R2: pass
R3: pass
R4: fail
R6: pass
R7: pass
R8: pass
R9: fail
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

Consensus lens (gemini-3.8-flash via copilot). Ran `uv run pytest skills/distil-memory/scripts/ -q`,
`validate_skill.py skills/distil-memory`, `test_docket_exit_codes.py`, and the two PRD acceptance
`rg` commands, and probed `Path('repo_a/proposals/').parent` for the trailing-slash case. One 🟡
Medium finding, independently matching Bob's `SKILL.md` step-7 finding.

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

Verdict: 8 findings
Tests: 1024 passed, 0 failed, 5 skipped (reused from last-verification.json at 45a0adf518dc23b250c9d8844f8e91e5b45b3ee8)
