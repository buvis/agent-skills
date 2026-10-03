---
prd: dev/local/prds/wip/00009-walk-memory-proposal-queue-v1.md
review: 1
date: 2026-08-31
head_sha: 9a44a4e7d392962d2480ee039292a8f346d35501
codex_thread_id: 01a05512-de48-7331-b4fe-6607a61312d2
reviewers: alice,blake,bob,carl,eve
agents:
  alice: available
  blake: available
  bob: available
  carl: available
  eve: available
---

# Review: 00009-walk-memory-proposal-queue-v1

Diff range: `24afb75409954d5057508e81925883e1e367d072..9a44a4e7d392962d2480ee039292a8f346d35501`

codex_rung_guard: fired (2 codex-implemented task(s))

## Scope note (read before the findings)

This is a **full** review of the PRD's whole work range, not an incremental one.
`gather-context.sh` labels the diff header "incremental review (changes since
24afb75…)" because it was invoked with `--since`; that flag was needed because
autopilot commits directly onto `master` in this repo, so the script's default
`vs master` range resolved to an **empty diff**. The `--since` value is
`state.work_start_sha`, which is exactly the full-review range the skill
prescribes. No prior review file exists for this PRD; this is cycle 1.

**Context pack: unavailable this cycle.** `engram pack` failed twice with
`not inside a registered repo; register it in /Users/bob/.config/gita/repos.csv`.
Per the skill this is non-fatal: `(no pack available this cycle)` was substituted
for `{PACK_FILE}` and `{PACK_FINDINGS}` in every prompt that takes them. The
review is degraded by the missing retrieval context, not invalid.

**Severity mapping for Eve, disclosed.** Eve's doubt format (FIX / VERIFY /
KNOWN) carries no severities, and `consolidate_findings.py` parses only
`[AGENT] emoji … | File: … | Task: …` lines. Her seven FIX items were therefore
transcribed into that line format by the orchestrator, **with severities the
orchestrator assigned** — they are not Eve's own words on severity. Her verbatim
FIX/VERIFY/KNOWN text is reproduced unchanged in her section below.

## Review Summary

Reviewed: 4 completed tasks
PRDs checked: 00009-walk-memory-proposal-queue-v1

### Agent Status

- Alice (consensus, Claude): ✅ Available
- Blake (blind, PRD-only): ✅ Available
- Bob (doubt + de-slop, codex): ✅ Available
- Carl (UI/generalist, gemini via copilot): ✅ Available
- Eve (doubt, Fable 5): ✅ Available — activated by the codex doubt-roster guard

All five lenses ran. Consensus engine: `legacy` (single Task subagent).
Consolidation ran through `consolidate_findings.py` (not model-side).

## Consolidated Findings

19 findings, all scored `[1/5]` by the consolidator. Two pairs are genuine
duplicates the paraphrase matcher did not merge, so the printed consensus
understates them — noted inline below.

| Consensus | Severity | Issue | File | Task | Found By |
|-----------|----------|-------|------|------|----------|
| [1/5] | 🟠 | `write_memory()` and `append_pointer()` write files with a plain `Path.write_text()` call (open, write, close - not atomic), unlike `docket.py`'s own `_save_queue()` in the same feature, which uses a temp-file-plus-rename pattern. An interruption mid-write to the shared `MEMORY.md` index (described in the PRD as "always-loaded") can truncate the whole file, losing every previously recorded pointer line, not just the one being added or updated. No test exercises a partial-write/crash scenario. | skills/distil-memory/scripts/write.py | Phase 1 | BLAKE |
| [1/5] | 🟠 | Keep/edit becomes terminal before publication; a missing-store or pointer-write failure permanently skips an approved but unwritten entry | skills/distil-memory/SKILL.md:177 | general | BOB |
| [1/5] | 🟠 | Memory-file and `MEMORY.md` symlinks can escape the selected store and overwrite external files | skills/distil-memory/scripts/write.py:39 | 2 | BOB |
| [1/5] | 🟠 | CLI implementations (main functions and argparse logic) are entirely missing test coverage | N/A | general | CARL |
| [1/5] | 🟠 | Both CLI entry points ship with zero automated tests (new behavior; the testing rule requires a regression test) — a manual drive proves they work today, but nothing pins `_save_from_proposals_dir`'s field mapping to the proposals.json shape or `write.py main`'s stdin contract. | skills/distil-memory/scripts/docket.py:156 | general | EVE |
| [1/5] | 🟡 | The PRD's Structural Decomposition and Phase 0 Exit Criteria name the module `queue.py`/`test_queue.py` verbatim; it was renamed to `docket.py`/`test_docket.py` (commit 9a44a4e) to avoid shadowing Python's stdlib `queue` module. Functionally equivalent and fully tested, but running the PRD's own literal exit-criteria command fails: `pytest scripts/test_queue.py` -> "file or directory not found". | skills/distil-memory/scripts/docket.py | Phase 0 | BLAKE |
| [1/5] | 🟡 | The "frontmatter contract" test uses an invalid fixture without `metadata` and only parses two fields, so it cannot enforce the stated contract | skills/distil-memory/scripts/test_write.py:283 | 2 | BOB |
| [1/5] | 🟡 | The integration test never exercises the required invalid-edit path that must leave the proposal undecided and write nothing | skills/distil-memory/scripts/test_walkthrough_integration.py:79 | 4 | BOB |
| [1/5] | 🟡 | Eliminate redundant file write operations by modifying the lines list and performing a single write_text at the end | skills/distil-memory/scripts/write.py | 2 | CARL |
| [1/5] | 🟡 | Use next() generator expression to find the first undecided entry for consistency with decide() | skills/distil-memory/scripts/docket.py | 1 | CARL |
| [1/5] | 🟡 | "Passes the frontmatter contract" test asserts a weaker check than the contract: the fixture emits no `metadata.type`, so the written file actually FAILS `proposal.validate` (REQUIRED_TYPES), and the test only re-parses two keys — it cannot fail when the real contract diverges (PRD success metric: "same frontmatter contract as the existing 70"). Same fixture gap in test_walkthrough_integration.py:16. | skills/distil-memory/scripts/test_write.py:283 | 2 | EVE |
| [1/5] | 🟡 | `dedup_error` is silently dropped at queue ingestion: proposals.json carries it (proposal.py:216) and SKILL.md's yield section says such a proposal's new/update verdict "is not trustworthy", but `_save_from_proposals_dir` omits it, so the walkthrough decider never sees the warning. | skills/distil-memory/scripts/docket.py:178 | 1 | EVE |
| [1/5] | 🟡 | SKILL.md step 6 tells the driver to validate edits with `proposal.validate_distil_output` but never states its required inputs: the function takes `(Proposal, index_has_names)`; a driver guessing `index_has_names=True` against a store with an empty index wrongly rejects a linkless edit, guessing False skips the link rule. | skills/distil-memory/SKILL.md:190 | 3 | EVE |
| [1/5] | 🟡 | Two same-named "new" proposals in one run collide at write time: publish de-collides filenames with `-2` suffixes (proposal.py:202), but `_target_stem` re-derives the stem from `entry["name"]`, so keeping the second raises WriteError "already exists" with no documented recovery. | skills/distil-memory/scripts/write.py:18 | 2 | EVE |
| [1/5] | ⚪ | `RUBRIC_VERSION` is a hand-maintained string constant, coupled to `distil.py`'s `_DISTIL_PROMPT` only by a code comment ("bump by hand when ... changes meaningfully"). There is no automated check tying the two, so a future prompt change could ship without bumping the version, leaving proposals judged under a now-stale rubric silently suppressed forever (the PRD's stated intent is that a rubric bump reopens old drops). | skills/distil-memory/scripts/docket.py | general | BLAKE |
| [1/5] | ⚪ | `decide()` and `write_memory()` raise `QueueError`/`WriteError` that propagate as unhandled Python tracebacks through their respective CLI entry points (`docket.py decide`, `write.py write`) rather than a caught, friendly stderr message, weakening the "stop and report" framing of the missing-store error path in practice (though the assistant driving the walkthrough is expected to read and relay the failure). | skills/distil-memory/scripts/write.py | Phase 1 | BLAKE |
| [1/5] | ⚪ | Cannot statically verify: tests and required validator/braid checks actually pass | N/A | general | BOB |
| [1/5] | ⚪ | `WriteError` docstring overclaims: "Raised when a memory file or its index pointer cannot be written", but `append_pointer` raises raw OSError/ProposalError, never WriteError. | skills/distil-memory/scripts/write.py:14 | 2 | EVE |
| [1/5] | ⚪ | Constant-restating tests fail exactly when the documented maintenance happens (the PRD says tune the cap after the first real run; the RUBRIC_VERSION comment says bump it by hand) and enforce nothing the 25/10 PRD-scenario test does not already pin — delete `test_per_run_cap_constant_is_ten` and `test_rubric_version_constant_is_one`. | skills/distil-memory/scripts/test_docket.py:38 | 1 | EVE |

**Unmerged duplicates.** Bob and Eve raised the frontmatter-contract fixture
defect at the same file and line (`test_write.py:283`) — real consensus 2/5, not
1/5. Carl and Eve raised the untested CLI entry points — real consensus 2/5, and
Alice failed `R1` on the same gap without emitting an issue line for it, so three
of five reviewers converged on it.

## Orchestrator verification of contested findings

Three findings were checked against the code directly before classification, because
a wrong call on any of them would have sent rework in the wrong direction.

- **Blake's atomicity HIGH — CONFIRMED.** `write.py:85` and `write.py:89` each call
  `index_path.write_text("\n".join(lines) + "\n")`, rewriting the whole index.
  `docket.py:30-34` (`_save_queue`) in the same PRD does use tmp-plus-`Path.replace`.
  The inconsistency and the truncation window are both real.
- **Carl's "redundant file write operations" — REFUTED, discarded.** The two
  `write_text` call sites at `write.py:85` and `write.py:89` are mutually exclusive
  branches: line 85 sits inside the update-in-place loop and returns immediately.
  Exactly one write executes per invocation. There is no redundant runtime write.
- **Blake's traceback finding — CONFIRMED.** Neither `docket.main` (`docket.py:195-215`)
  nor `write.main` (`write.py:103-112`) catches anything, so `QueueError` and
  `WriteError` do reach the terminal as tracebacks. Eve's separate observation that
  the missing-store case "exits 1 and creates nothing" is also true and not in
  conflict — an uncaught exception exits 1.

Also confirmed by reading: Eve's `dedup_error` drop (`docket.py:178-189` omits the
field), and that `next_undecided`'s `PER_RUN_CAP` gate (`docket.py:102-103`) sits
before the loop, so Carl's `next()` suggestion is genuinely behavior-preserving.

## Alice (consensus)

Verification she performed: full suite (941 passed, 5 skipped); the create-skill
validator (`[OK] Skill is valid!`); a manual end-to-end drive of the whole
documented CLI sequence (`docket.py save` → `start` → `next` → `decide` →
`write.py write` → `docket.py cursor`) against a temp store, reporting that every
command's output matched `SKILL.md`'s prose character for character, including the
literal `MEMORY.md: unchanged` string. **This directly retires the cycle's named
top suspect: no prose/CLI drift exists.** She also confirmed no stale
`queue.py`/`test_queue.py` references remain in tracked files, and checked function
and file sizes against the mechanical-facts block.

```
[ALICE] ✅ No issues found
```

She raised no issue line but failed `R1` deliberately, reporting the untested CLI
layer honestly in the verdict rather than passing it silently.

```
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
```

## Blake (blind, PRD-only)

Located the code unaided and verified the module contracts, the per-sitting cap,
the rejection record, the update-vs-new write semantics and the walkthrough prose
against the spec alone.

```
[BLAKE] 🟡 The PRD's Structural Decomposition and Phase 0 Exit Criteria name the module `queue.py`/`test_queue.py` verbatim; it was renamed to `docket.py`/`test_docket.py` (commit 9a44a4e) to avoid shadowing Python's stdlib `queue` module. Functionally equivalent and fully tested, but running the PRD's own literal exit-criteria command fails: `pytest scripts/test_queue.py` -> "file or directory not found". | File: skills/distil-memory/scripts/docket.py | Task: Phase 0
[BLAKE] 🟠 `write_memory()` and `append_pointer()` write files with a plain `Path.write_text()` call (open, write, close - not atomic), unlike `docket.py`'s own `_save_queue()` in the same feature, which uses a temp-file-plus-rename pattern. An interruption mid-write to the shared `MEMORY.md` index (described in the PRD as "always-loaded") can truncate the whole file, losing every previously recorded pointer line, not just the one being added or updated. No test exercises a partial-write/crash scenario. | File: skills/distil-memory/scripts/write.py | Task: Phase 1
[BLAKE] ⚪ `RUBRIC_VERSION` is a hand-maintained string constant, coupled to `distil.py`'s `_DISTIL_PROMPT` only by a code comment ("bump by hand when ... changes meaningfully"). There is no automated check tying the two, so a future prompt change could ship without bumping the version, leaving proposals judged under a now-stale rubric silently suppressed forever (the PRD's stated intent is that a rubric bump reopens old drops). | File: skills/distil-memory/scripts/docket.py | Task: general
[BLAKE] ⚪ `decide()` and `write_memory()` raise `QueueError`/`WriteError` that propagate as unhandled Python tracebacks through their respective CLI entry points (`docket.py decide`, `write.py write`) rather than a caught, friendly stderr message, weakening the "stop and report" framing of the missing-store error path in practice (though the assistant driving the walkthrough is expected to read and relay the failure). | File: skills/distil-memory/scripts/write.py | Task: Phase 1
```

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

## Bob (doubt + de-slop, codex, static-only)

```
[BOB] 🟠 Keep/edit becomes terminal before publication; a missing-store or pointer-write failure permanently skips an approved but unwritten entry | File: skills/distil-memory/SKILL.md:177 | Task: general
[BOB] 🟠 Memory-file and `MEMORY.md` symlinks can escape the selected store and overwrite external files | File: skills/distil-memory/scripts/write.py:39 | Task: 2
[BOB] 🟡 The "frontmatter contract" test uses an invalid fixture without `metadata` and only parses two fields, so it cannot enforce the stated contract | File: skills/distil-memory/scripts/test_write.py:283 | Task: 2
[BOB] 🟡 The integration test never exercises the required invalid-edit path that must leave the proposal undecided and write nothing | File: skills/distil-memory/scripts/test_walkthrough_integration.py:79 | Task: 4
[BOB] ⚪ Cannot statically verify: tests and required validator/braid checks actually pass | File: N/A | Task: general
```

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
R13: pass
```

```
D1: pass
D2: pass
D3: pass
D4: pass
D5: pass
```

```
FIX:
- Terminal decisions can outlive failed publication — skills/distil-memory/SKILL.md:177 — publish and verify before recording `kept`, or introduce a retryable publication state; test missing-store and pointer-write failures
- Symlink targets can escape the memory store — skills/distil-memory/scripts/write.py:39 — resolve and containment-check both target paths, reject dangling/out-of-store links, and add symlink tests
- The contract test does not validate the real contract — skills/distil-memory/scripts/test_write.py:283 — use a complete project-memory fixture and call the same proposal validator used by production
- Invalid edited output is untested — skills/distil-memory/scripts/test_walkthrough_integration.py:79 — exercise validator rejection and assert the queue entry remains undecided with no files created
VERIFY:
- Runtime verification was prohibited — run `uv run pytest`, `uv run python3 skills/create-skill/scripts/validate_skill.py skills/distil-memory`, and `braid --check`
KNOWN:
- (none)
```

Bob's `VERIFY` item was discharged by the orchestrator: `uv run pytest` →
941 passed, 5 skipped, 0 failed. Alice independently ran the create-skill
validator (exit 0). Bob's several `fail` verdicts (R2, R4, R7, R9, R10) reflect
his static-only sandbox, where a criterion he cannot confirm counts as fail;
Alice, Carl and Blake, all of whom executed code, passed those same rules.

## Carl (UI/generalist, gemini)

No frontend surface in this diff, so Carl reviewed as a generalist, as his
persona directs.

```
[CARL] 🟠 CLI implementations (main functions and argparse logic) are entirely missing test coverage | File: N/A | Task: general
[CARL] 🟡 Eliminate redundant file write operations by modifying the lines list and performing a single write_text at the end | File: skills/distil-memory/scripts/write.py | Task: 2
[CARL] 🟡 Use next() generator expression to find the first undecided entry for consistency with decide() | File: skills/distil-memory/scripts/docket.py | Task: 1
```

```
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
```

## Eve (doubt, Fable 5)

Activated by the codex doubt-roster guard. She drove both untested CLIs end to
end by hand, ran the create-skill validator, scanned all 175 real memory files
against `parse_frontmatter`, and ran both the 500-test distil-memory subset and
the full repo suite. She independently confirms Alice's prose-vs-argparse result:
every documented subcommand and flag matches the parsers, and no stale `queue.py`
references remain.

Her verbatim output:

```
FIX:
- "Passes the frontmatter contract" test asserts a weaker check than the contract: fixture at test_write.py:11 emits no `metadata.type`, so the written file actually FAILS `proposal.validate` (REQUIRED_TYPES), and the test at test_write.py:283 only re-parses two keys - it cannot fail when the real contract diverges (PRD success metric: "same frontmatter contract as the existing 70") — test_write.py:283 (same fixture gap in test_walkthrough_integration.py:16) — add `metadata:\n  type: project` to the fixtures and assert via `proposal.validate(proposal.Proposal(file_text=..., evidence=proposal.Evidence(...)))`.
- `dedup_error` is silently dropped at queue ingestion: proposals.json carries it (proposal.py:216), SKILL.md's yield section says such a proposal's new/update verdict "is not trustworthy," but `_save_from_proposals_dir` omits it so the walkthrough decider never sees the warning — docket.py:178 — copy `"dedup_error": record.get("dedup_error")` into the queue entry and add one line to SKILL.md step 3 to surface it.
- SKILL.md step 6 tells the driver to validate edits with `proposal.validate_distil_output` but never states its required inputs: the function takes `(Proposal, index_has_names)`; a driver guessing `index_has_names=True` against a store with an empty index wrongly rejects a linkless edit, guessing False skips the link rule — SKILL.md:190 — state how to build the `Proposal` (needs an `Evidence`) and that `index_has_names = bool(dedup.parse_index(dedup.read_index(<store-path>)))` for the target store.
- Two same-named "new" proposals in one run collide at write time: publish de-collides filenames with `-2` suffixes (proposal.py:202), but `_target_stem` re-derives the stem from `entry["name"]`, so keeping the second raises WriteError "already exists" with no documented recovery — write.py:18 — add a sentence to SKILL.md step 5: a keep that fails with "already exists" is renamed through the edit path (or carried published stem; the doc line is the bounded fix).
- `WriteError` docstring overclaims: "Raised when a memory file or its index pointer cannot be written," but `append_pointer` raises raw OSError/ProposalError, never WriteError — write.py:14 — narrow the docstring to the memory file, or wrap `append_pointer`'s writes; pick one so the claim is true.
- Both CLI entry points ship with zero automated tests (new behavior; testing rule requires a regression test) - my manual drive proves they work today but nothing pins `_save_from_proposals_dir`'s field mapping to the proposals.json shape or `write.py main`'s stdin contract — docket.py:156-215, write.py:93-112 — add `main()`-level tests: `docket.main(["save", "--proposals-dir", ...])` against a seeded dir, `next`/`decide`/`cursor`, and `write.main(["write", "--store", ...])` with a stdin entry.
- Constant-restating tests fail exactly when the documented maintenance happens (PRD says tune the cap after the first real run; the RUBRIC_VERSION comment says bump it by hand) and enforce nothing the 25/10 PRD-scenario test doesn't already pin — test_docket.py:38-43 — delete `test_per_run_cap_constant_is_ten` and `test_rubric_version_constant_is_one`.
VERIFY:
- (none)
KNOWN:
- The cursor is a lifetime decision counter, not the PRD's "cursor marking how far the corpus has been consumed": `--all` drainability actually comes from save() dedup plus drop records, and every `--all --distil` run re-reads/re-distils the corpus — a true corpus-position cursor lives in slice 2's selection/limit mechanics (funnel.py), outside this diff, and all PRD acceptance tests pass as written.
- `advance(new_cursor=...)` has no production caller (the `start` subcommand never passes it; force-setting would desync step 7's drained-vs-capped comparison) — the PRD's export list names `advance(cursor)` verbatim, so removing the parameter re-litigates the PRD; revisit with the cursor semantics.
- An update whose `existing_text` has unparseable frontmatter crashes `append_pointer` (raw ProposalError) after `write_memory` already replaced the file - 2 of 175 real memory files fail the parse (both in the buvis-clusters store) — verified unreachable today: that store's `./`-prefixed index links never match `dedup._ENTRY`, so classify cannot type an update against them; the data fix belongs to that store, not this diff.
- `_report_dir()` is duplicated verbatim between docket.py:18 and funnel.py:285 — importing funnel from docket would couple the queue module to the whole pipeline for six lines; accepted drift risk, consolidate only if a third copy appears.
- Inert `reversed()` in the by-id kept-entry lookup — test_walkthrough_integration.py:52 — confirmed present; already recorded as a deferred MEDIUM in this cycle's settled context.
- Inert `docket.advance()` call (only 2 of 5 entries decided, cap is 10) — test_walkthrough_integration.py:79 — confirmed present; already recorded as a deferred MEDIUM in this cycle's settled context.
```

```
D1: pass
D2: pass
D3: pass
D4: pass
D5: pass
```

Counts: 13 findings = 7 FIX + 0 VERIFY + 6 KNOWN.

**One KNOWN worth flagging beyond this PRD:** Eve's first KNOWN argues the
delivered `cursor` is a lifetime decision counter rather than the PRD's
"cursor marking how far the corpus has been consumed". She judged all PRD
acceptance criteria satisfied as written and placed the gap in slice 2's
selection mechanics, outside this diff. Recorded here so it is not lost;
it is not actioned in this cycle.

## Decision gate (cycle 1)

Cap: `rework_cap` 2, `cycle` 1 → `1 < 2`, rework allowed.
**Not converged**: unresolved HIGH findings remain. Proceeding to rework.

### Deferred (recorded, not fixed)

- 🟠 Symlink escape in `write.py:39` — the memory store is the operator's own
  directory, reached from the source transcript's own location. It is not a
  trust boundary and takes no untrusted input, so a planted symlink presupposes
  an attacker who already has write access to the same directory being written.
  Containment checks would be defensive validation for a state that cannot occur
  (`rules/coding-style.md`).
- ⚪ `RUBRIC_VERSION` hand-maintenance — that is the specified design, not an
  oversight; the task contract says "bump by hand". Automating it would re-open
  every drop on any incidental prompt edit.

### Discarded (verified reason)

- 🟡 Blake's `queue.py` naming finding — settled, recorded spec divergence
  (stdlib shadowing broke 33 tests; the rename was the root fix). Blake is blind
  by construction, so the re-raise is legitimate, but the decision stands. The
  residue is a stale name in a historical PRD document, not a code defect.
- 🟡 Carl's "redundant file write operations" — refuted against the code; the two
  `write_text` call sites are mutually exclusive branches.
- ⚪ Bob's "cannot statically verify" — sandbox artifact; the suite was run.

All five entries are recorded in
`dev/local/reviews/00009-walk-memory-proposal-queue-v1-ledger.json`.

### Follow-up tasks created

1. [D1] Add main()-level CLI tests for docket.py and write.py, and report their errors instead of tracebacks (M) — 🟠, 3-of-5 agreement counting Alice's R1
2. [D1] Write the memory file and MEMORY.md atomically, matching docket.py's own tmp-plus-replace idiom (S) — 🟠
3. [D1] Make the frontmatter-contract test enforce the real contract, and cover the invalid-edit path (M) — 🟡, 2-of-5
4. [D1] Carry dedup_error through queue ingestion so the walkthrough decider sees the untrustworthy-verdict warning (S) — 🟡
5. [D1] Close three gaps in SKILL.md's walkthrough prose: failed publication, validator inputs, and name collisions (M) — 🟠 + 🟡
6. [D1] De-slop: truthful WriteError docstring, drop constant-restating tests, and the two known inert test lines (S) — ⚪/🟡

Six tasks, under the 10-task scope alarm.

Verdict: 19 findings
Tests: 941 passed, 0 failed, 5 skipped
