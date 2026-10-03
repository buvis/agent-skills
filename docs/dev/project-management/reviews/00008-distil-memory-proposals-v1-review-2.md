---
prd: dev/local/prds/wip/00008-distil-memory-proposals-v1.md
review: 2
date: 2026-08-30
head_sha: d6249b7cfde191b5a969087920fe8e773672023b
codex_thread_id: 01a053a2-b231-7c21-a576-51e01c0fba06
reviewers: alice,blake,bob,carl
agents:
  alice: available
  blake: available
  bob: available
  carl: available
---

# Review: 00008-distil-memory-proposals-v1

Diff range: `b4011f0..d6249b7` (10 commits, 18 files, 1449 insertions / 570 deletions)

codex_rung_guard: not fired

pack: failed (engram: "not inside a registered repo; register it in the gita
repos.csv" — this repo is absent from that registry). `{PACK_FILE}` and
`{PACK_FINDINGS}` were substituted with `(no pack available this cycle)` in
every prompt that takes them. Not retried: the failure is the same deterministic
config condition cycle 1 recorded, not a transient one.

## Review Summary

Reviewed: 15 completed tasks (11 original plan, 4 `[D1]` rework tasks)
PRDs checked: 00008-distil-memory-proposals-v1.md

### Agent Status

- Alice (consensus, Claude): ✅ Available — 0 findings, 12 R verdicts (all pass)
- Blake (blind, PRD-only): ✅ Available — 0 severity findings, 19 B verdicts (all pass)
- Bob (doubt + de-slop, codex, resumed thread): ✅ Available — 3 findings, 12 R verdicts, 5 D verdicts
- Carl (UI/generalist, gemini via copilot): ✅ Available — 0 findings, 12 R verdicts (all pass)

Consensus engine: `legacy` (single Alice subagent). Consolidation ran via
`consolidate_findings.py` (script, not model-side), with
`--ledger 00008-distil-memory-proposals-v1-ledger.json --ledger-dismiss BLAKE`.
No Blake finding matched a ledger entry mechanically, because Blake emitted no
line in the severity-emoji finding format this cycle (see his section below), so
the script produced no `Auto-dismissed (ledger)` section.

### Incremental-review scope

This was an incremental review. `gather-context.sh --since b4011f0…` produced a
**non-empty** diff (2454 lines, 18 files) — the empty-diff trap from cycle 1 did
not recur, and the diff was checked before any prompt was assembled. Bob was
resumed on his cycle-1 codex thread (`--resume-thread
01a053a2-b231-7c21-a576-51e01c0fba06`), so he verified the fixes against his own
prior critique rather than re-reviewing from zero. Alice, Bob and Carl received
cycle 1's consolidated findings and the settled-decisions ledger; Blake received
neither, staying blind by design.

## Prior-cycle findings: all 10 verified resolved

Every cycle-1 finding routed to rework was confirmed closed against the source,
not against the reviewers' word:

| Cycle-1 finding | Sev | Where it landed |
|---|---|---|
| Report names a proposals path `main()` never creates | 🟠 | `render_yield` takes `proposals_dir: Path | None` threaded from `main()` via `_report_outcome`; one value, no second literal. funnel.py:221-262, 453-484, 512-558 |
| Unsanitisable name escapes `main()` as an uncaught `ProposalError` | 🟠 | `validate_distil_output` calls `sanitise_name` itself (proposal.py:144-165), so `distil()`'s existing `except ProposalError` turns it into an ordinary reasoned discard before publication |
| `read_index` exists-then-read TOCTOU | 🟡 | One `read_text()` under `try`; `FileNotFoundError` → `""`, every other `OSError` propagates. dedup.py:42-54 |
| Bare `DISCARD:` persists an empty reason | 🟡 | Fallback reason naming the missing-reason case, carrying no slice text. distil.py:109-114 |
| `--distil` publishes after a failed triage | 🟡 | `_distil_if_enabled` gates on `triage_error is None`; the five counts stay absent so the report renders `n/a`, not `0`. funnel.py:487-509 |
| Fixtures duplicated across three test modules | 🟡 | `funnel_test_helpers.py` and `distil_test_helpers.py` are the sole homes; zero test-module-to-test-module imports remain |
| Structural-only tests (type-alias identity, constant membership) | 🟡 | Three removed: `test_shortlist_limit_constant_is_five`, `test_candidate_is_a_memory_name_and_file_text_pair`, `test_distil_type_is_one_of_the_required_types` |
| `write_proposals` duck-types discards | 🟡 | `PublishedDiscard` Protocol (proposal.py:223-233) names the three-field shape; `discards.json` unchanged |
| `read_index` / `shortlist` docstrings dropped load-bearing rationale | ⚪ | Raising contract and the Jaccard formula restored. dedup.py:42-50, 68-77 |
| `read_candidates` does not validate the names it is handed | ⚪ | `_MEMORY_NAME` stem guard; a bad name is skipped like a missing file, so it cannot manufacture a `dedup_error`. dedup.py:91-113 |

No regression was found in the rework range. `d6249b7`'s size refactor
(`_distil_if_enabled` extraction, the `test_distil.py` → `test_distil_discard.py`
split, `_record_reads` extraction) is behaviour-preserving on inspection and by
the passing suite.

## Consolidated Findings

### Full Consensus (4/4)

_(none)_

### Majority Consensus (>50%)

_(none)_

### Minority (<=50%)

- [1/4] 🟡 The invalid-name test allows exit 0 without requiring the documented reasoned discard, so an unreasoned drop accompanied only by diagnostic text would pass | skills/distil-memory/scripts/test_funnel_distil_publication.py:372 | Found by: Bob
- [1/4] 🟡 Candidate-path validation is only lexical; a valid stem backed by a symlink can still make `read_candidates` read outside the memory directory | skills/distil-memory/scripts/dedup.py:104 | Found by: Bob
- [1/4] 🟡 The discard test's shingle-scanning loop is redundant because equality with the bare-discard result already proves later lines cannot affect the reason | skills/distil-memory/scripts/test_distil_discard.py:158 | Found by: Bob

### Gate verification of all three

Each was read from source before classification rather than taken on the
reviewer's word:

1. `test_main_reports_and_returns_when_a_proposal_name_leaves_no_safe_filename`
   (test_funnel_distil_publication.py:372-421) asserts the exit code is an int,
   that the unusable name appears somewhere in what the run said, and that it is
   absent from `proposals.json`. It never requires a `discards.json` record with
   a reason. **Confirmed: the gap is real.**
2. `_MEMORY_NAME` (dedup.py:27) is `(?!\.+\Z)[\w.-]+`, matched with `fullmatch`
   at dedup.py:104 — purely lexical. `rg -n symlink` over `test_dedup_classify.py`
   returns nothing, so Blake's claim that symlink escapes were already covered is
   **wrong**, and Bob's finding stands. It remains defense-in-depth on the user's
   own directory, not a live exploit — the same framing cycle 1 set.
3. test_distil_discard.py:188 asserts `result.reason == bare.reason`; lines
   189-194 then scan every later line for substrings and 12-character shingles.
   Given the equality, no later-line content can reach the reason. **Confirmed
   redundant** — the test's own docstring says the loop "says twice" what is
   already proven.

### Discarded and deferred this cycle

None. All three findings are actionable Mediums and were routed to the tail
sweep. The ledger
(`dev/local/reviews/00008-distil-memory-proposals-v1-ledger.json`, 7 entries from
cycle 1) is unchanged this cycle.

## Alice

Ran the skill suite (445 passed), the whole-repo suite (886 passed, 5 skipped)
and the create-skill validator (OK), cross-checked the mechanical-facts block for
every countable claim, and traced each cycle-1 fix to its shipped source lines
rather than to the diff alone. Found every prior finding resolved and no
regression, and raised nothing new. Her one caveat, recorded rather than filed:
an ad-hoc `ruff check --select F401,F841` produced 4 hits, all false positives on
pytest fixtures used only as parameter names; `skills/` is excluded in the
project's own `pyproject.toml`, so none of it reaches CI.

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

## Blake

Located the code from the spec alone, read the four modules and 19 test files
(272 test functions), and verified by execution: both PRD exit-criteria commands
run literally, the skill suite green at 445, the calibration test actually
running against the live 71-file corpus rather than skipping, the validator OK,
and the Phase 2 run artifact present on disk with its proposals directory. He
emitted no finding in the severity-emoji format — his lines are ✅ confirmations
plus two ⚠️ items he classified himself as non-failures, so consolidation
correctly counted zero findings from him. Both ⚠️ items are recorded here rather
than dropped:

- The **archived** Phase-2 run report
  (`dev/local/audit-results/distil-memory-20260830T162841Z.md`) still carries the
  old "proposals are under dev/local/audit-results/proposals/" sentence. That is
  a frozen artifact written before the cycle-1 fix, not shipped code; the current
  `render_yield` emits the real directory, which Blake confirmed by calling it
  directly. Nothing to fix in the codebase.
- `distil()`'s signature inserts `index_has_names` ahead of `judge` versus the
  PRD's sketch. This is the same claim cycle 1 discarded against the design doc,
  which specifies the signature verbatim and is the implementation authority.
  Blake never receives the ledger, so re-raising it is expected; it stays
  discarded. He judged it a non-failure himself.

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

Static-only sandbox review carrying the doubt and de-slop lenses, resumed on his
cycle-1 codex thread. The only lens to raise anything, and all three findings
survived gate verification. His `R1`/`R2`/`R7` fails are his own three findings
restated as rubric verdicts: two test-strength items under R1/R2 and the
lexical-only path validation under R7. His FIX bucket is complete, VERIFY and
KNOWN are both empty, and all five doubt-rubric rules pass.

FIX:
- Invalid-name test permits a successful unreasoned drop — skills/distil-memory/scripts/test_funnel_distil_publication.py:372 — require exit 0 to produce a `discards.json` record carrying the unusable-name reason; otherwise require the explicit non-zero publish-error path
- Safe-looking symlinks can escape the memory directory — skills/distil-memory/scripts/dedup.py:104 — reject candidate paths whose resolved target leaves the resolved memory directory and add a symlink-backed test
- Redundant tail-shingle assertions obscure the discard test — skills/distil-memory/scripts/test_distil_discard.py:158 — remove `_SHINGLE_LENGTH` and the nested substring loop while retaining the parameter matrix and equality with the bare-discard reason
VERIFY:
- (none)
KNOWN:
- (none)

R1: fail
R2: fail
R3: pass
R4: pass
R6: pass
R7: fail
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

## Carl

No frontend surface in this change, so reviewed as a generalist against the
shared checklist, as his persona directs. Read the full diff and the full context
file and raised nothing; every rubric rule passed. He did not re-raise the
`parse_index` walrus rewrite the ledger records as discarded, which is the
settled-decisions feed working.

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

## Follow-up Tasks Created

1. `[D2]` Sweep the cycle-2 medium findings: unreasoned-drop test gap, symlink-backed candidate read, redundant shingle loop (M) — 🟡 1/4 consensus — task 16

One tail-sweep task, not another rework round: cycle 2 converged (no unresolved
CRITICAL or HIGH), and Medium/Low findings are swept rather than dropped. The
task carries all three findings verbatim in a `### Findings (verbatim)` block,
plus the gate's own source verification of each, and its acceptance criterion is
"every quoted finding no longer reproduces".

Verdict: 3 findings
Tests: 886 passed, 0 failed, 5 skipped
