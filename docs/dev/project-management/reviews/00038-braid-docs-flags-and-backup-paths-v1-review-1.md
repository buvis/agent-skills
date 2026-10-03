---
prd: dev/local/prds/wip/00038-braid-docs-flags-and-backup-paths-v1.md
review: 1
date: 2026-09-07
head_sha: a2cf29c6af040960b2688e24e11262d9675d1aa8
codex_thread_id: 01a0798c-cc4b-7611-9298-17d8ffa0f5c0
reviewers: alice,blake,bob,carl
agents:
  alice: available
  blake: available
  bob: available
  carl: available
---

# Review: 00038-braid-docs-flags-and-backup-paths-v1

Diff range: `7254c47b6649feb03966a63c2f5527506c089b91..a2cf29c6af040960b2688e24e11262d9675d1aa8`

codex_rung_guard: not fired

pack: unavailable this cycle (`engram pack` exited 1: "not inside a registered repo; register it in /Users/bob/.config/gita/repos.csv"). Every prompt that takes `{PACK_FILE}`/`{PACK_FINDINGS}` received the `(no pack available this cycle)` sentinel. The review is degraded on retrieval context, not invalid.

Consolidation: script (`consolidate_findings.py`), 4 agent outputs, no ledger flags (cycle 1 had no prior ledger).

Diff-scope note: this is cycle 1 and a FULL review of the PRD's whole work range. `gather-context.sh` was invoked with `--since <work_start_sha>` rather than bare, because this repo's work commits land directly on `master`, so the script's default "vs master" base produced an empty diff. The label it wrote into the context file was corrected to say full review.

## Reviewer status

- Alice: ✅ Available (Claude subagent, consensus lens)
- Blake: ✅ Available (Claude subagent, blind lens — PRD only, no diff)
- Bob: ✅ Available (codex, doubt + de-slop lens) — **rescued by his one retry**. His first run exited 0 but reported it could not open the context or diff by path ("none is available and shell commands are prohibited") and failed all twelve R rules for lack of input, not for a defect. `[RETRY] BOB attempt 1/1` re-dispatched a fresh `codex-run.sh` with every input inlined into the prompt (diff, PRD, tasks, the computed blocks, the recorded verification). The second run produced a real review. The first attempt's output is kept at `dev/local/tmp/bob-output-00038-c1.attempt1.txt`.
- Carl: ✅ Available (gemini via copilot backend, model `gemini-3.8-flash`)

## Consolidated findings

| Consensus | Severity | Issue | File | Task | Found By |
|-----------|----------|-------|------|------|----------|
| [1/4] | 🟠 | `ruff format --check` fails on this diff: the `--agents-root` and `--claude-root` `add_argument` calls were force-wrapped onto multiple lines even though each fits under the project's 100-col limit on one line; the project's own formatter (used by `.github/workflows/ci.yml` step `uv run ruff format --check`) would collapse them back, so this diff currently breaks the CI formatting gate. Verified by running `uv run ruff format --check src/agent_skills_braid/cli.py` locally: "1 file would be reformatted." | src/agent_skills_braid/cli.py:422-427 | 1 | ALICE |
| [1/4] | 🟠 | `--version` still has no `help=` text, violating the success criterion that all ten options and every parser action have nonempty descriptions; the test's five-option allowlist misses this. | src/agent_skills_braid/cli.py | 1 | BOB |
| [1/4] | ⚪ | The new `--agents-root`/`--claude-root`/`--config-root` help strings ("override the ~/.agents directory", etc.) describe the default path but omit the env-var precedence ("ahead of AGENTS_ROOT") that the PRD contract and the README table both call out; minor inconsistency in level of detail between the CLI help and the README, not a correctness bug. | src/agent_skills_braid/cli.py:422-431 | 1 | ALICE |
| [1/4] | ⚪ | PRD success criterion "no product code is touched" is self-contradictory with its own Phase 0 task, which modifies cli.py; implementation correctly follows the task (help= only, no behavior change) so this is a spec wording issue, not a defect | N/A | general | BLAKE |

### Gate verification of the two 🟠 findings

Both HIGH findings were checked directly at the decision gate rather than taken on the reviewer's word.

**Alice's ruff finding — CONFIRMED.** Run at the gate:

```
$ uv run ruff format --check src/agent_skills_braid/cli.py
unformatted: File would be reformatted
   --> src/agent_skills_braid/cli.py:422:25
421 |     )
    -     parser.add_argument(
    -         "--agents-root", type=Path, help="override the ~/.agents directory"
    -     )
    -     parser.add_argument(
    -         "--claude-root", type=Path, help="override the ~/.claude directory"
    -     )
422 +     parser.add_argument("--agents-root", type=Path, help="override the ~/.agents directory")
423 +     parser.add_argument("--claude-root", type=Path, help="override the ~/.claude directory")
1 file would be reformatted
```

Exit 1. The CI gate is real: `.github/workflows/ci.yml:91` runs `uv run ruff format --check`. `pyproject.toml:33` sets `line-length = 100`, and both collapsed lines fit under it. `uv run ruff check` (the separate lint gate, ci.yml:88) passes. The work phase's own recorded verification ran `uv run pytest` and `python3 bin/braid.py --check` but not the formatter, which is how this escaped.

**Bob's `--version` finding — REFUTED, discarded.** `argparse._VersionAction` supplies a non-empty default help string, so `--version` is described without an explicit `help=`. Dumping every parser action:

```
['-h', '--help']   -> 'show this help message and exit'
['--dry-run']      -> 'report changes without writing'
['--check']        -> 'exit non-zero when links drift'
['--source']       -> 'additional repository root or skills directory (repeatable)'
['--policy']       -> 'additional .braidignore file to load (repeatable)'
['--agents-root']  -> 'override the ~/.agents directory'
['--claude-root']  -> 'override the ~/.claude directory'
['--config-root']  -> 'override the ~/.config/agent-skills directory'
['--no-claude']    -> 'skip projecting skills into claude-root'
['--version']      -> "show program's version number and exit"
```

All ten options carry non-empty help, and `python3 bin/braid.py --help` exits 0 printing a description for each — the PRD success criterion holds. The test's five-option scope is exactly what the PRD's Phase 0 task specifies ("a headless parser-action assertion checks the five newly described options"), so the allowlist is per spec, not a gap. Recorded in `dev/local/reviews/00038-braid-docs-flags-and-backup-paths-v1-ledger.json` as `discarded`.

## Alice

Consensus lens, implementation-aware. Two findings (one 🟠, one ⚪) plus a positive verification pass: `rg -n -c "help=" cli.py` = 8, `python3 bin/braid.py --help` exits 0 with non-empty descriptions for all ten options, the new parser-action test fails against pre-change code and passes now, the README flag table and both corrected backup paths (`.../project/` and `.../compose/`) match the code in `run()`/`_backup()` exactly, PRD-00044-owned README sections untouched, and the suite passes with no regression.

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

Blind lens — PRD only, no diff, no file list, no review history. He located the code himself and verified each acceptance criterion independently, including that `_backup()` (`root / category / path.name`) really does produce both documented paths, so the README now describes actual behavior. One ⚪ finding, on the PRD's own wording. All nineteen blind rules pass.

```
B1: pass    B6: pass    B11: pass   B16: pass
B2: pass    B7: pass    B12: pass   B17: pass
B3: pass    B8: pass    B13: pass   B18: pass
B4: pass    B9: pass    B14: pass   B19: pass
B5: pass    B10: pass   B15: pass
```

## Bob

Doubt + de-slop lens (codex, static-only sandbox), second attempt with inputs inlined. One 🟠 finding, refuted at the gate above. His de-slop lens raised nothing: no over-abstraction, dead code, defensive guards, or speculative generality in the diff.

```
R1: pass
R2: pass
R3: pass
R4: pass
R6: pass
R7: pass
R8: pass
R9: fail
R10: pass
R11: pass
R12: pass
R13: pass
```

R9 (`Implementation matches PRD feature behavior exactly`) is his only fail, and it rests entirely on the `--version` claim the gate refuted.

Doubt buckets:

```
FIX:
- `--version` remains undocumented — src/agent_skills_braid/cli.py:436 — add nonempty `help=` text and include `--version` in the parser-action assertion.

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

VERIFY bucket is empty, so no verification-check queue file was written for this cycle.

## Carl

Gemini via the copilot backend (`gemini-3.8-flash`). He read the context and diff, ran `uv run pytest tests/test_braid.py`, checked `python3 bin/braid.py --help`, inspected the xfail reasons with `-rxX`, and read `_parser()` directly.

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

- **Tautological test shapes:** 15 test functions checked in 1 test file, **zero** `[MECH]` lines. No new or changed test has a shape that cannot fail.
- **Fail-first replay:** 1 touched test ran against the pre-change code at `7254c47b6649`; **1 failed against base, 0 passed**. The new test genuinely pins this change.
- **Mechanical facts:** no reviewer made a countable claim contradicting the computed `ast` line counts. The only functions over 50 lines (`_sync_links` 58, `main` 55) are pre-existing and untouched by this diff; `_parser` is 38 lines after the change.

Verdict: 4 findings

Tests: 1100 passed, 0 failed, 5 skipped (reused from last-verification.json at a2cf29c6af040960b2688e24e11262d9675d1aa8)
