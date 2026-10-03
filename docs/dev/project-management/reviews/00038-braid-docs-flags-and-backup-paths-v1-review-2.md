---
prd: dev/local/prds/wip/00038-braid-docs-flags-and-backup-paths-v1.md
review: 2
date: 2026-09-07
head_sha: 2bca306641dddee0bd8740c52a874f1b1eb45cbd
codex_thread_id: 01a0798c-cc4b-7611-9298-17d8ffa0f5c0
reviewers: alice,blake,bob,carl
agents:
  alice: available
  blake: available
  bob: available
  carl: available
---

# Review: 00038-braid-docs-flags-and-backup-paths-v1

Diff range: `a2cf29c6af040960b2688e24e11262d9675d1aa8..2bca306641dddee0bd8740c52a874f1b1eb45cbd`

codex_rung_guard: not fired

pack: unavailable this cycle (`engram pack` exited 1: "not inside a registered repo; register it in /Users/bob/.config/gita/repos.csv"). Every prompt that takes `{PACK_FILE}`/`{PACK_FINDINGS}` received the `(no pack available this cycle)` sentinel. The review is degraded on retrieval context, not invalid. Same deterministic config failure as cycle 1, so no retry was spent.

Consolidation: script (`consolidate_findings.py`), 4 agent outputs, run with `--ledger dev/local/reviews/00038-braid-docs-flags-and-backup-paths-v1-ledger.json --ledger-dismiss BLAKE`. Nothing was auto-dismissed: Blake raised no findings this cycle.

Diff-scope note: this is cycle 2 and an INCREMENTAL review. `gather-context.sh --since a2cf29c6af040960b2688e24e11262d9675d1aa8` scoped the diff to the single rework commit `2bca306` (task 4, `[D1]`). Tasks 1-3 were reviewed in full in cycle 1 and are outside this range.

Task-creation note: no `task-add` was run here. Under autopilot the decision gate (run-autopilot Phase 5) owns classification and `[D{cycle}]` task creation — that is what created task 4 from cycle 1's findings — so creating tasks in this step too would duplicate them. The two findings below are handed to the gate as-is.

## Reviewer status

- Alice: ✅ Available (Claude subagent, consensus lens)
- Blake: ✅ Available (Claude subagent, blind lens — PRD only, no diff)
- Bob: ✅ Available (codex, doubt + de-slop lens) — **succeeded on his first run this cycle**, unlike cycle 1. Dispatched with `--resume-thread 01a0798c-cc4b-7611-9298-17d8ffa0f5c0` (his own cycle-1 session) and with every input inlined into the prompt from the start, which is what cycle 1 needed a retry to discover.
- Carl: ✅ Available (gemini via copilot backend, model `gemini-3.8-flash`)

## Consolidated findings

| Consensus | Severity | Issue | File | Task | Found By |
|-----------|----------|-------|------|------|----------|
| [1/4] | ⚪ | New CHANGELOG bullet (line 53) uses an em dash ("printed a blank description — the working `--policy` flag..."), violating the user's global writing-style rule ("Never use em dashes"); mitigated because the file already contains four pre-existing em dashes (lines 74, 83, 101, 111) establishing local convention, so this matches existing file style rather than introducing a new one. | CHANGELOG.md | 4 | ALICE |
| [1/4] | ⚪ | The CHANGELOG's second new bullet documents task 2/3's README changes (flag table, backup paths), which shipped as `docs` commits (4420a09, a2cf29c) exempt from the mandatory-CHANGELOG-entry rule per `rules/changelog.md`; task 4's stated scope was only the two cli.py findings (ruff format + env-var text), so this bullet is backfill beyond what task 4's acceptance criteria required. Harmless and accurate, flagged for scope discipline only. | CHANGELOG.md | 4 | ALICE |

No CRITICAL and no HIGH findings. Both cycle-1 HIGH findings are gone: one was fixed by task 4 and independently re-verified below, the other was refuted and discarded at the cycle-1 gate and was not re-raised by anyone.

### Cycle-1 findings — resolution status

| Cycle-1 finding | Severity | Status this cycle |
|-----------------|----------|-------------------|
| `ruff format --check` fails on the diff (ALICE) | 🟠 High | **RESOLVED.** Verified three ways: Alice re-ran `uv run ruff format --check src/agent_skills_braid/cli.py` ("1 file already formatted"), Carl ran the full chain `uv run ruff format --check && uv run ruff check && uv run pytest && python3 bin/braid.py --help` to exit 0, and the gate re-ran `uv run ruff format --check` over the repo ("10 files already formatted", exit 0). |
| `--version` has no `help=` (BOB) | 🟠 High | **Discarded at the cycle-1 gate**, in the settled-decisions ledger. Bob was fed the settled entry and did not re-raise it; his R9, which failed in cycle 1 solely on this claim, is now `pass`. |
| Root-override help strings omit env-var precedence (ALICE) | ⚪ Low | **RESOLVED.** `--agents-root` now reads "ahead of AGENTS_ROOT", `--claude-root` "ahead of CLAUDE_ROOT", `--config-root` "...holding sources.d, ahead of AGENT_SKILLS_CONFIG". |
| PRD success criterion self-contradiction (BLAKE) | ⚪ Low | **Settled deferral** in the ledger. Blake, who is blind by design and never receives the ledger, did not re-raise it; the `--ledger-dismiss BLAKE` filter therefore dismissed nothing. |

## Alice

Consensus lens, implementation-aware. She verified both cycle-1 findings routed to task 4 are resolved, and confirmed the multi-line shape of `--agents-root`/`--claude-root` is now genuinely what the formatter produces (the longer help strings no longer fit on one line under the 100-col limit), not hand-wrapping — the exact failure mode the cycle-1 finding warned about. Reconfirmed `rg -c "help=" cli.py` → 8, `python3 bin/braid.py --help` exits 0 with non-empty descriptions for all ten options, `python3 bin/braid.py --check` exits 0, and `uv run pytest -q` → 1100 passed, 5 skipped, 9 xfailed with no new failures. Two ⚪ findings, both on the CHANGELOG and both cosmetic.

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

Blind lens — PRD only, no diff, no file list, no review history. He located the code himself and re-verified every acceptance criterion independently, including that `_backup()` (`root / category / path.name`, `category="project"` for Claude and `"compose"` for the union) really does build both documented paths. He also confirmed by diff that PRD 00044's territory (`README.md:26-28`, `README.md:145-148`) is untouched, that no new flags or dependencies appeared (`pyproject.toml`/`uv.lock` unchanged), and that the two backup layouts stay deliberately divergent per the PRD's declared non-goal. No findings. All nineteen blind rules pass.

```
B1: pass    B6: pass    B11: pass   B16: pass
B2: pass    B7: pass    B12: pass   B17: pass
B3: pass    B8: pass    B13: pass   B18: pass
B4: pass    B9: pass    B14: pass   B19: pass
B5: pass    B10: pass   B15: pass
```

## Bob

Doubt + de-slop lens (codex, static-only sandbox), resuming his cycle-1 thread with all inputs inlined. No findings from either lens: no over-abstraction, dead code, defensive guards, or speculative generality in the diff, and no spec gap. His cycle-1 R9 fail is now `pass` — it rested entirely on the `--version` claim the gate refuted.

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

```
[BOB] ✅ No issues found
```

Doubt buckets:

```
FIX:
- (none)

VERIFY:
- (none)

KNOWN:
- (none)
```

```
D1: pass
D2: pass
D3: pass
D4: pass
D5: pass
```

VERIFY bucket is empty, so no verification-check queue file was written for this cycle. Cycle 1's was empty for the same reason, so there was nothing to carry forward either.

## Carl

Gemini via the copilot backend (`gemini-3.8-flash`). He read the context and diff, then ran the project's own gate chain himself — `uv run ruff format --check && uv run ruff check && uv run pytest && python3 bin/braid.py --help` — to exit 0, plus `python3 bin/braid.py --check`, `rg -n -c "help=" src/agent_skills_braid/cli.py`, the `git diff` over the review range, and `wc -l` on both changed files. No findings; the diff has no frontend surface, so he reviewed as a generalist rather than inventing frontend findings.

```
[CARL] ✅ No issues found
```

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

## Mechanical checks

- **Tautological test shapes:** 0 test functions checked in 0 test files, **zero** `[MECH]` lines — this cycle's diff touches no test file.
- **Fail-first replay:** `replay: skipped (the diff touches no test function)`. Cycle 1's replay covered the one test this PRD adds: 1 touched test, 1 failed against base, 0 passed, so the parser-action test genuinely pins the change.
- **Mechanical facts:** no reviewer made a countable claim contradicting the computed `ast` line counts. The only functions over 50 lines (`_sync_links` 58, `main` 55) are pre-existing and untouched by this diff; `_parser` is 43 lines after the rework, and `cli.py` is 508 lines, under the 800-line limit.

Verdict: 2 findings

Tests: 1100 passed, 0 failed, 5 skipped (reused from last-verification.json at 2bca306641dddee0bd8740c52a874f1b1eb45cbd)
