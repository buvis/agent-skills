---
prd: dev/local/prds/wip/00008-distil-memory-proposals-v1.md
review: 1
date: 2026-08-30
head_sha: b4011f0e405b6d90270a0d880a6a5cc2ff4710e9
codex_thread_id: 01a053a2-b231-7c21-a576-51e01c0fba06
reviewers: alice,blake,bob,carl
agents:
  alice: available
  blake: available
  bob: available
  carl: available
---

# Review: 00008-distil-memory-proposals-v1

Diff range: `df39b15..b4011f0` (32 commits, 19 files, 6151 insertions / 553 deletions)

codex_rung_guard: not fired

pack: failed (engram: "not inside a registered repo" — this repo is absent from the gita registry, 26 entries, none matching `agent-skills`). `{PACK_FILE}` and `{PACK_FINDINGS}` were substituted with `(no pack available this cycle)` in every prompt that takes them. Not retried: the failure is a deterministic config condition, not a transient one.

## Review Summary

Reviewed: 11 completed tasks
PRDs checked: 00008-distil-memory-proposals-v1.md

### Agent Status

- Alice (consensus, Claude): ✅ Available — 6 findings, 12 R verdicts
- Blake (blind, PRD-only): ✅ Available — 2 findings, 19 B verdicts
- Bob (doubt + de-slop, codex): ✅ Available — 11 findings, 12 R verdicts, 5 D verdicts
- Carl (UI/generalist, gemini via copilot): ✅ Available — 3 findings, 12 R verdicts

Consensus engine: `legacy` (single Alice subagent). Consolidation ran via
`consolidate_findings.py` (script, not model-side). **The script's paraphrase
matcher merged one pair; four further cross-reviewer duplicates were merged by
the gate**, because the matcher requires a matching `File:` string and the
reviewers wrote the same file at different granularity (`dedup.py` vs
`dedup.py:41`). The merges are named in the table's Found By column and raised
three findings' consensus above what the raw script output showed.

### Diff-scope note

`gather-context.sh` computed its own range and produced an **empty** diff (this
branch is `master` with no upstream divergence, so its merge-base fallback
resolved to HEAD). The diff was regenerated at the range this PRD's state
mandates — `work_start_sha..HEAD` = `df39b15..b4011f0` — before any prompt was
assembled, and the context file's Changed Files section was corrected to match.
No reviewer saw the empty diff.

## Consolidated Findings

### Majority Consensus (>50%)

- [3/4] 🟡 `read_index` uses an exists-then-read TOCTOU sequence instead of one read with `FileNotFoundError` handling | skills/distil-memory/scripts/dedup.py:41 | Found by: Alice, Bob, Carl

### Minority (<=50%)

- [2/4] 🟠 The yield report's "How to proceed" sentence names `dev/local/audit-results/proposals/` (funnel.py:254), but `main()` publishes to `dev/local/audit-results/distil-memory-<timestamp>-proposals/` (funnel.py:522). Confirmed on the real task-11 run; `SKILL.md` documents the correct path, so the code contradicts its own docs | skills/distil-memory/scripts/funnel.py | Found by: Alice, Bob
- [2/4] 🟠 A model-emitted `name` that reduces to nothing after sanitisation raises `ProposalError` (a `ValueError`), which `_distil_and_publish` does not catch (`OSError` only), so it escapes `main()` before the yield report prints | skills/distil-memory/scripts/funnel.py, skills/distil-memory/scripts/proposal.py | Found by: Alice, Bob
- [1/4] 🟠 Judge calls persist hundreds of transcripts into the corpus future runs scan, causing self-ingestion and runaway growth | skills/distil-memory/scripts/funnel.py:178 | Found by: Bob
- [1/4] 🟡 A bare `DISCARD:` response persists an empty reason, violating the reasoned-discard contract | skills/distil-memory/scripts/distil.py:109 | Found by: Bob
- [1/4] 🟡 `--distil` publishes an empty proposals directory with zero counts after triage fails, although no valid survivor set exists | skills/distil-memory/scripts/funnel.py:520 | Found by: Bob
- [1/4] 🟡 `FakeSessionData`, `make_transcript_parser_module` and `write_transcript` are duplicated across three new test modules; extract one shared test helper | N/A | Found by: Bob
- [1/4] 🟡 Tests that only assert a type-alias identity or redundant constant relationship verify implementation structure rather than behavior and can be removed | N/A | Found by: Bob
- [1/4] 🟡 `write_proposals` duck-types discards, forcing `funnel.py` to build `_PublishedDiscard` to satisfy attributes; the `list["Discard"]` annotation names a shape it does not accept | skills/distil-memory/scripts/proposal.py | Found by: Carl
- [1/4] ⚪ `dedup.read_index` and `dedup.shortlist` docstrings dropped the rationale the design doc calls load-bearing (the raising contract; the Jaccard formula and why it beats the alternatives) | skills/distil-memory/scripts/dedup.py | Found by: Alice
- [1/4] ⚪ `dedup.read_candidates` does no validation of its own on the `names` it is handed; safe today only because its sole caller path constrains names via `_ENTRY`'s `[\w.-]+` regex | skills/distil-memory/scripts/dedup.py | Found by: Alice

### Discarded and deferred this cycle

Recorded with reasons in `dev/local/reviews/00008-distil-memory-proposals-v1-ledger.json`
(7 entries: 2 settled deferrals, 5 discards). Summary:

| Disposition | Sev | Finding | Reason |
|---|---|---|---|
| settled-deferral | 🟠 | Self-ingestion: judge calls write transcripts into the scanned corpus | The fix belongs to `funnel.judge`, **verified absent from this diff** and shipped by slice 1 (PRD 00007), shared with triage. Out of PRD 00008's scope; needs its own PRD. |
| settled-deferral | ⚪ | Calibration contract skips when the memory plane is absent, so CI never exercises it | Decided at the design gate: a hermetic fixture was proposed and deliberately not built in this slice. Bob filed it under KNOWN himself. |
| discarded | 🟡 | `parse_index` loop → dict comprehension with a walrus | Behaviour-preserving style churn that trades clarity for brevity, which the review checklist's own Balance rule forbids. |
| discarded | ⚪ | `distil()` / `classify()` signatures add parameters beyond the PRD's literal exports | The design doc specifies these exact signatures verbatim, and it is the implementation authority. Blake judged it non-blocking himself. |
| discarded | ⚪ | `load_examples` restricts anchors to `project`-type memories | The design contract for `load_examples` specifies exactly this; the task's own test list pins it. |
| discarded | ⚪ | purge-devlocal date edit unrelated to this PRD | The requested remedy is already satisfied: isolated in its own commit `0d80bb0` (1 file, 1 line, `docs()` type). The corrected date is factually right. |
| discarded | ⚪ | "Cannot statically verify: pytest, skill validation and braid checks pass" | Bob's sandbox marker, not a defect. The gates were run this cycle (suite green, validator OK). |

## Alice

Ran the suite (412 passed in the skill's own scripts dir) and the create-skill
validator (OK), cross-checked the mechanical-facts block for every countable
claim, and read the real task-11 run artifact to confirm one finding against
live output. Judged the implementation strong overall — the cue-restatement
rule, the atomic-publish sequence, the no-full-read pin and the dedup-failure
handling all match the design doc exactly, and the tests are unusually well
bound to intent. Raised the two HIGHs that drive this cycle's rework, plus the
TOCTOU Medium and three Lows.

R1: pass
R2: pass
R3: pass
R4: pass
R6: pass
R7: fail
R8: pass
R9: fail
R10: fail
R11: pass
R12: pass
R13: pass

## Blake

Located the code from the spec alone, read all four modules and all 15 test
files (6,482 lines, 412 tests), and verified by execution rather than reading:
the suite passed, the calibration test actually ran against the live corpus
(71 files) rather than skipping, the validator reported OK, and the recorded
single-project run exists on disk with its proposals directory. Confirmed the
two-step dedup is provably enforced, publication is atomic, and both
out-of-scope items (corrections, cross-project routing) are verifiably absent.
Raised two Lows, both judged non-blocking by Blake himself; both were discarded
against the design doc.

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

## Bob

Static-only sandbox review carrying the doubt and de-slop lenses. Raised the
most findings of any lens (11), including both HIGHs Alice independently found
and the self-ingestion HIGH nobody else raised. His three doubt buckets were
complete and his `VERIFY` item (run the runtime gates) was executed by the gate:
suite green, validator OK.

FIX:
- Judge-generated sessions pollute future input — skills/distil-memory/scripts/funnel.py:178 — invoke Claude print mode without session persistence and add a regression assertion for that flag
- All-unsafe proposal names crash publication — skills/distil-memory/scripts/funnel.py:422 — validate sanitise_name during distil validation so invalid model output becomes a discard, or explicitly catch ProposalError
- Report names a nonexistent proposals path — skills/distil-memory/scripts/funnel.py:254 — render the actual timestamped directory or a matching distil-memory-*-proposals path
- Empty discard reasons reach disk — skills/distil-memory/scripts/distil.py:109 — reject an empty suffix with an explicit fallback reason and test it
- Distillation runs after triage failure — skills/distil-memory/scripts/funnel.py:520 — require triage_error is None before publishing; leave distil counts n/a and add the combined failure test
- Index read is TOCTOU-prone — skills/distil-memory/scripts/dedup.py:41 — call read_text once and return empty only from FileNotFoundError
- Three test modules duplicate the same fixtures — skills/distil-memory/scripts/test_funnel_main.py:18 — extract FakeSessionData and the parser/transcript builders into one shared test helper
- Framework-verification tests add no behavioral coverage — skills/distil-memory/scripts/test_dedup.py:143 — remove the Candidate alias equality test and the redundant DISTIL_TYPE-membership test
- Unrelated purge-devlocal comment entered the PRD diff — skills/purge-devlocal/scripts/purge_devlocal.py:87 — revert it or move it to separate work
VERIFY:
- Runtime gates were not executable here — run `uv run pytest`, `uv run python3 skills/create-skill/scripts/validate_skill.py skills/distil-memory`, and `braid --check`
KNOWN:
- CI lacks the host-specific calibration memory plane — the PRD explicitly defines a live, derived host corpus; an anonymized hermetic corpus is a separate fixture-scope decision

R1: fail
R2: fail
R3: fail
R4: fail
R6: pass
R7: fail
R8: pass
R9: fail
R10: fail
R11: pass
R12: pass
R13: pass
D1: pass
D2: pass
D3: pass
D4: pass
D5: pass

## Carl

No frontend surface in this change, so reviewed as a generalist against the
shared checklist, as his persona directs. Ran the suite and computed his own
per-file and per-function line counts from the diff. Raised three
simplification Mediums; one (the TOCTOU) corroborated Alice and Bob and became
the cycle's only majority finding, one (the `write_proposals` discard
duck-typing) is real and routed to rework, and one (the `parse_index` rewrite)
was discarded as style churn.

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

## Follow-up Tasks Created

1. `[C1]` Fix the two HIGH defects on the funnel publish path — report path, uncaught ProposalError (M) — 🟠 2/4 consensus — task 12
2. `[C1]` Close the dedup.py findings: TOCTOU, dropped contract rationale, unvalidated candidate names (M) — 🟡 3/4 consensus — task 13
3. `[C1]` Fix two distil-stage correctness gaps: empty discard reason, publishing after a triage failure (M) — 🟡 1/4 consensus — task 14
4. `[C1]` De-slop the new test modules: shared fixtures and structural assertions (S) — 🟡 1/4 consensus — task 15

Each task carries its source findings verbatim in a `### Findings (verbatim)`
block, and each acceptance criterion is "every quoted finding no longer
reproduces".

Verdict: 16 findings
Tests: 853 passed, 0 failed, 5 skipped
