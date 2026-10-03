---
prd: dev/local/prds/wip/00009-walk-memory-proposal-queue-v1.md
review: 2
date: 2026-08-31
head_sha: ab4e946b0f3288655e828fae8f94a048a8fe6055
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

Diff range: `9a44a4e7d392962d2480ee039292a8f346d35501..ab4e946b0f3288655e828fae8f94a048a8fe6055`

codex_rung_guard: fired (2 codex-implemented task(s))

## Scope note (read before the findings)

This is an **incremental** review of cycle 1's rework: 12 commits, 7 files, the six
`[D1]` tasks (ids 5-10) created by cycle 1's decision gate. `gather-context.sh` was
invoked with `--since 9a44a4e…` (the cycle-1 review file's `head_sha`), which is
required in this repo because autopilot commits directly onto `master`, so the
script's default `vs master` range resolves to an **empty diff**. Cycle 1 already
reviewed the PRD's full work range.

Bob's codex session was resumed via `--resume-thread 01a05512-…`, so he verified
closure against his own cycle-1 critique rather than re-reviewing from zero.

**Context pack: unavailable this cycle.** `engram pack` failed with
`not inside a registered repo; register it in /Users/bob/.config/gita/repos.csv` —
the same deterministic error that failed twice in cycle 1, so no retry was burned.
Per the skill this is non-fatal: `(no pack available this cycle)` was substituted for
`{PACK_FILE}` and `{PACK_FINDINGS}` in every prompt that takes them. For Eve, the real
findings precedent (her own seven cycle-1 findings, the six routed from other
reviewers, and the five settled-ledger entries) was passed in the pack's place. The
review is degraded by the missing retrieval context, not invalid.

**Mechanical-facts block.** `compute_mech_facts.py` was run over the five changed
Python files and its output written to `dev/local/tmp/review-mechfacts-2.md`, which
every implementation-aware prompt was pointed at by absolute path. It was NOT appended
into `review-context-2.md` as the skill prescribes: the aegis
`block_devlocal_redirects.py` hook blocks shell redirects into `dev/local/`, and
re-writing the 712-line context file through the Write tool to append 118 lines was
not worth the cost. Effect on reviewers is identical (the block is in front of all
four implementation-aware lenses); the deviation is recorded here rather than hidden.

**Severity mapping for Eve, disclosed.** Eve's doubt format (FIX / VERIFY / KNOWN)
carries no severities, and `consolidate_findings.py` parses only
`[AGENT] emoji … | File: … | Task: …` lines. Her eight FIX items were transcribed into
that line format by the orchestrator, **with severities the orchestrator assigned** —
they are not Eve's own words on severity. Her verbatim FIX/VERIFY/KNOWN text is
reproduced unchanged in her section below.

## Review Summary

Reviewed: 10 completed tasks (4 original-plan, 6 `[D1]` rework)
PRDs checked: 00009-walk-memory-proposal-queue-v1

### Agent Status

- Alice (consensus, Claude): ✅ Available
- Blake (blind, PRD-only): ✅ Available
- Bob (doubt + de-slop, codex, resumed thread): ✅ Available
- Carl (UI/generalist, gemini via copilot): ✅ Available
- Eve (doubt, Fable 5): ✅ Available — activated by the codex doubt-roster guard

All five lenses ran. Consensus engine: `legacy` (single Task subagent).
Consolidation ran through `consolidate_findings.py` (not model-side), with
`--ledger` + `--ledger-dismiss BLAKE` against the 5-entry settled-decisions ledger.
No Blake finding was auto-dismissed this cycle.

## Consolidated Findings

15 findings: 5 🟠 High, 5 🟡 Medium, 5 ⚪ Low. **Zero 🔴 Critical.**

| Consensus | Severity | Issue | File | Task | Found By |
|-----------|----------|-------|------|------|----------|
| [3/5] | 🟡 | test_walkthrough_integration.py's `_attempt_edit_then_publish` (added for the invalid-edit-path test) validates through `proposal.validate()`, not `proposal.validate_distil_output(proposal, index_has_names)` - the exact call SKILL.md step 6 documents as the walkthrough's real validation. The helper's own docstring claims to model "Walkthrough's documented step-6 ordering", so it overclaims: a regression that broke only validate_distil_output's extra rules (exact metadata.type match, non-empty body, the wiki-link-when-index-has-names rule) would pass this test undetected. | skills/distil-memory/scripts/test_walkthrough_integration.py | 7 | ALICE, BOB, EVE |
| [2/5] | 🟡 | The `index_has_names` snippet passes a string to `dedup.read_index`, whose path operation requires a `Path`, so the documented validation raises `TypeError` | skills/distil-memory/SKILL.md:223 | 9 | BOB, EVE |
| [1/5] | 🟠 | SKILL.md's new "already exists" recovery ("resolve it by renaming the proposal through the edit path... which re-emits the file under a distinct name") does not work: for a "new" kind entry, write.py's `_target_stem()` derives the collision-checked filename from `entry["name"]` (verified empirically - changing file_text's frontmatter name to "widget-fact-renamed" while entry["name"] stays "widget-fact" still resolves the target stem to "widget-fact"), and step 6's literal instructions only replace `file_text` in entry.json, never `entry["name"]`. Following the documented recovery verbatim reproduces the identical WriteError. | skills/distil-memory/SKILL.md | 9 | ALICE |
| [1/5] | 🟠 | Failed-publication recovery remains impossible after an index-write failure: the memory file already exists, so retry stops at "already exists," while step 6 cannot re-decide the terminal entry or change its target by editing only `file_text` | skills/distil-memory/SKILL.md:191 | 9 | BOB |
| [1/5] | 🟠 | write.py CLI still tracebacks when append_pointer fails (raw OSError on the MEMORY.md write, ProposalError on a drifted existing_text), directly contradicting the new SKILL.md:193 claim that "write" exits 1 and prints the reason to stderr instead of raising | skills/distil-memory/scripts/write.py:125 | 5 | EVE |
| [1/5] | 🟠 | The new "already exists" collision recovery is unexecutable as written: it routes through step 6's edit path, but that path ends in `decide "<id>" kept --file`, which raises "no undecided entry" for the already-kept entry (step 5 itself says re-deciding is impossible) | skills/distil-memory/SKILL.md:204 | 9 | EVE |
| [1/5] | 🟠 | The kept-before-published recovery is sitting-scoped only: a session dying between `decide kept` and a successful write leaves an entry that `next` skips forever, and the step-7 "list any kept whose write did not succeed" report can only name failures the same sitting witnessed | skills/distil-memory/SKILL.md:191 | 9 | EVE |
| [1/5] | 🟡 | Atomic-write tests catch broad `Exception`, so unrelated failures can satisfy the intended crash path | skills/distil-memory/scripts/test_write.py:501 | 6 | BOB |
| [1/5] | 🟡 | `test_main_start_returns_zero` asserts only the exit code and cannot fail if `start` stops calling advance() | skills/distil-memory/scripts/test_docket.py:509 | 5 | EVE |
| [1/5] | 🟡 | The four crash-safety tests assert `pytest.raises(Exception)`, which also passes when the code fails before reaching the atomic move (e.g. a KeyError during setup), hollowing out the "intact after the move fails" proof | skills/distil-memory/scripts/test_write.py:483 | 6 | EVE |
| [1/5] | ⚪ | Phase 2's acceptance text says "a temporary store under dev/local/tmp/"; test_walkthrough_integration.py uses pytest's tmp_path (system $TMPDIR), not a path under the repo's dev/local/tmp/. Functionally equivalent (both are inside the documented write-fence roots) but a literal deviation from the PRD's stated location. | skills/distil-memory/scripts/test_walkthrough_integration.py | Phase 2 task 2 | BLAKE |
| [1/5] | ⚪ | docket.py's Structural Decomposition lists decide(id, state) and cursor()/advance(cursor); the implementation adds decide(..., file_text=None, path=None) and advance(new_cursor=None, path=None). The additions are functionally required (file_text serves the spec's own "re-emit on edit" feature; path enables the temp-store testing the PRD's acceptance criteria demand) rather than gratuitous scope creep, but they are additions beyond the literal Exports signatures. | skills/distil-memory/scripts/docket.py | Foundation Layer (Phase 0) | BLAKE |
| [1/5] | ⚪ | docket.py's load()/save()/decide() do a non-atomic read-modify-write across separate CLI invocations (no file lock); a second concurrent invocation could lose an update (classic check-then-act). The PRD's Target Users ("the solo maintainer... across more than one sitting") implies sequential, non-concurrent use, so this isn't a spec violation, but it's worth naming for deployment readiness. | skills/distil-memory/scripts/docket.py | general | BLAKE |
| [1/5] | ⚪ | docket.load() calls json.loads() on the queue file with no try/except; a corrupted or hand-edited queue.json would raise an unhandled JSONDecodeError with a traceback surfaced in chat rather than a clean stderr message (unlike QueueError/WriteError elsewhere, which are handled cleanly). Not required by the PRD, and the atomic tmp+replace write pattern should prevent partial-write corruption in the normal path. | skills/distil-memory/scripts/docket.py | general | BLAKE |
| [1/5] | ⚪ | Unused `capsys` fixture parameters on the three new dedup_error CLI tests | skills/distil-memory/scripts/test_docket.py:638 | 8 | EVE |

**Unmerged duplicates — the printed consensus understates three rows.**

- Bob's `test_write.py:501` and Eve's `test_write.py:483` are the **same** defect (the
  four crash-safety tests catching broad `Exception`); different line anchors kept the
  paraphrase matcher from merging them. Real consensus **2/5**.
- Alice's `SKILL.md` "already exists" HIGH and Eve's `SKILL.md:204` HIGH are the same
  broken recovery reached from two different angles — Alice: `_target_stem()` never
  reads the re-emitted frontmatter name for a `"new"` kind, so the stem does not
  change; Eve: the edit path's terminating `decide … kept --file` cannot run on an
  already-`kept` entry. Real consensus **2/5**, and **both defects are independently
  fatal to the documented recovery** — fixing one leaves the other.
- Bob's `SKILL.md:191` HIGH and Eve's `SKILL.md:191` HIGH share a line but are
  genuinely distinct failure modes (Bob: retry blocked *within* a sitting after the
  index write fails; Eve: the entry stranded *across* sittings when a session dies
  between `decide kept` and the write). Left unmerged deliberately.

## Orchestrator verification of contested findings

Every 🟠 High was checked against the code directly before classification, because a
wrong call on any of them would send rework in the wrong direction.

- **Bob's failed-publication HIGH — CONFIRMED.** `write.py main()` (`write.py:116-127`)
  wraps only `write_memory` in `try/except WriteError`; the `append_pointer` call at
  `write.py:125` is unguarded. So an index-write failure leaves the memory file already
  on disk, and re-running `write.py write` — the recovery `SKILL.md:191-199` prescribes —
  hits `WriteError: … already exists` at `write_memory` (`write.py:51-52`) and never
  reaches the pointer step. The documented retry is blocked in exactly the failure mode
  it was written for.
- **Eve's traceback HIGH — CONFIRMED, same root, different symptom.** Because
  `append_pointer` is outside the `try`, its raw `OSError`/`ProposalError` escapes
  `main()` as a traceback. `SKILL.md:193` states "`decide` and `write` both exit 1 and
  print the reason to stderr instead of raising". That claim is false for the pointer
  half. Note this is *new prose added by task 9*, so cycle 1's traceback finding was
  closed for `QueueError`/`WriteError` but the doc now overclaims beyond what task 5
  actually fixed.
- **Alice's "already exists" HIGH — CONFIRMED.** `_target_stem()` (`write.py:18-28`)
  returns `sanitise_name(entry["name"])` for a `"new"` kind and never consults the
  file text's frontmatter. `decide(id, "kept", file_text=…)` (`docket.py:127-129`)
  replaces only `file_text`. So a rename through the edit path cannot change the target
  stem, and the collision reproduces. Alice verified this empirically with a direct
  `_target_stem` call.
- **Eve's unexecutable-recovery HIGH — CONFIRMED.** `decide()` (`docket.py:121-126`)
  selects on `e["decision"] == "undecided"` and raises
  `QueueError("no undecided entry with id …")` otherwise. The step-6 edit path ends in
  `decide … kept --file`, so routing an already-`kept` entry through it raises. `SKILL.md`
  step 5 says so itself ("re-deciding it is not possible"), which makes the step-5
  recovery text self-contradictory.
- **Eve's cross-sitting stranding HIGH — CONFIRMED by reading.** Nothing at sitting
  start reconciles `kept` entries against the store. `next_undecided()` (`docket.py:104-107`)
  filters on `decision == "undecided"`, so a `kept`-but-unwritten entry is invisible
  forever, and `save()` (`docket.py:82-85`) refuses to re-queue its `slice_key`. The
  step-7 report can only name failures its own sitting observed.
- **Bob's `read_index` TypeError MEDIUM — CONFIRMED.** `dedup.read_index(memory_dir: Path)`
  (`dedup.py:42`) does `(memory_dir / "MEMORY.md").read_text()`. `SKILL.md:223`'s snippet
  is `dedup.read_index("<store-path>")` — a quoted string, which raises
  `TypeError: unsupported operand type(s) for /: 'str' and 'str'`.
- **The 3/5 `validate_distil_output` MEDIUM — CONFIRMED.**
  `_attempt_edit_then_publish` (`test_walkthrough_integration.py:81`) calls
  `proposal.validate(candidate)`, and its docstring claims to model "Walkthrough's
  documented step-6 ordering". `SKILL.md` step 6 mandates
  `proposal.validate_distil_output(proposal, index_has_names)`.
- **The crash-test breadth MEDIUM — CONFIRMED.** All four tests at
  `test_write.py:483,508,533,557` use `with pytest.raises(Exception):`.

**Closure verified positively** (no finding raised): tasks 5, 6, 8 and 10 closed
cleanly, and task 7's fixture/contract half closed cleanly. Three reviewers
independently confirmed the same closures. Alice further confirmed the two inert lines
task 10 removed were genuinely inert, so their removal did not change any test's
meaning.

## Alice (consensus)

Verification she ran: `uv run pytest skills/distil-memory/scripts/ -q` (522 passed);
full repo `uv run pytest -q` (963 passed, 5 skipped — the 5 skips are pre-existing
`skills/survey` tests needing an optional `tree_sitter_language_pack`, unrelated to this
diff); the create-skill validator (`[OK] Skill is valid!`); `braid.py --check` (0 drift);
and `wc -l` on every changed file plus the mechfacts block to check the 800-line file cap
and 50-line function cap (largest file `test_docket.py` at 727 lines, largest function 47
lines — both under).

```
[ALICE] 🟠 SKILL.md's new "already exists" recovery ("resolve it by renaming the proposal through the edit path... which re-emits the file under a distinct name") does not work: for a "new" kind entry, write.py's `_target_stem()` derives the collision-checked filename from `entry["name"]` (verified empirically - changing file_text's frontmatter name to "widget-fact-renamed" while entry["name"] stays "widget-fact" still resolves the target stem to "widget-fact"), and step 6's literal instructions only replace `file_text` in entry.json, never `entry["name"]`. Following the documented recovery verbatim reproduces the identical WriteError. | File: skills/distil-memory/SKILL.md | Task: 9
[ALICE] 🟡 test_walkthrough_integration.py's `_attempt_edit_then_publish` (added for the invalid-edit-path test) validates through `proposal.validate()`, not `proposal.validate_distil_output(proposal, index_has_names)` - the exact call SKILL.md step 6 documents as the walkthrough's real validation. The helper's own docstring claims to model "Walkthrough's documented step-6 ordering", so it overclaims: a regression that broke only validate_distil_output's extra rules (exact metadata.type match, non-empty body, the wiki-link-when-index-has-names rule) would pass this test undetected. | File: skills/distil-memory/scripts/test_walkthrough_integration.py | Task: 7
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

Her R1 flipped from `fail` (cycle 1) to `pass`: task 5 closed the untested-CLI gap she
had reported honestly rather than passing silently.

## Blake (blind, PRD-only)

Located the code unaided from the PRD alone and ran the exit-criteria suites himself
(`test_docket.py` 45 passed, `test_write.py` 26 passed, integration 2 passed, full skill
suite 522 passed, validator `[OK]`). All 19 blind rules pass; his four findings are all
⚪ Low.

```
[BLAKE] ⚪ Phase 2's acceptance text says "a temporary store under dev/local/tmp/"; test_walkthrough_integration.py uses pytest's tmp_path (system $TMPDIR), not a path under the repo's dev/local/tmp/. Functionally equivalent (both are inside the documented write-fence roots) but a literal deviation from the PRD's stated location. | File: skills/distil-memory/scripts/test_walkthrough_integration.py | Task: Phase 2 task 2
[BLAKE] ⚪ docket.py's Structural Decomposition lists decide(id, state) and cursor()/advance(cursor); the implementation adds decide(..., file_text=None, path=None) and advance(new_cursor=None, path=None). The additions are functionally required (file_text serves the spec's own "re-emit on edit" feature; path enables the temp-store testing the PRD's acceptance criteria demand) rather than gratuitous scope creep, but they are additions beyond the literal Exports signatures. | File: skills/distil-memory/scripts/docket.py | Task: Foundation Layer (Phase 0)
[BLAKE] ⚪ docket.py's load()/save()/decide() do a non-atomic read-modify-write across separate CLI invocations (no file lock); a second concurrent invocation could lose an update (classic check-then-act). The PRD's Target Users ("the solo maintainer... across more than one sitting") implies sequential, non-concurrent use, so this isn't a spec violation, but it's worth naming for deployment readiness. | File: skills/distil-memory/scripts/docket.py | Task: general
[BLAKE] ⚪ docket.load() calls json.loads() on the queue file with no try/except; a corrupted or hand-edited queue.json would raise an unhandled JSONDecodeError with a traceback surfaced in chat rather than a clean stderr message (unlike QueueError/WriteError elsewhere, which are handled cleanly). Not required by the PRD, and the atomic tmp+replace write pattern should prevent partial-write corruption in the normal path. | File: skills/distil-memory/scripts/docket.py | Task: general
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

## Bob (doubt + de-slop, codex, static-only, resumed thread)

```
[BOB] 🟠 Failed-publication recovery remains impossible after an index-write failure: the memory file already exists, so retry stops at "already exists," while step 6 cannot re-decide the terminal entry or change its target by editing only `file_text` | File: skills/distil-memory/SKILL.md:191 | Task: 9
[BOB] 🟡 The `index_has_names` snippet passes a string to `dedup.read_index`, whose path operation requires a `Path`, so the documented validation raises `TypeError` | File: skills/distil-memory/SKILL.md:223 | Task: 9
[BOB] 🟡 The edit integration helper calls `proposal.validate` instead of documented `validate_distil_output(..., index_has_names)`, allowing empty-body or missing-link edits through the test driver | File: skills/distil-memory/scripts/test_walkthrough_integration.py:86 | Task: 7
[BOB] 🟡 Atomic-write tests catch broad `Exception`, so unrelated failures can satisfy the intended crash path | File: skills/distil-memory/scripts/test_write.py:501 | Task: 6
```

```
R1: fail
R2: fail
R3: pass
R4: fail
R6: pass
R7: pass
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

Bob emitted **no** "cannot statically verify" line this cycle — the prompt carried the
orchestrator's measured runtime results, which retired the sandbox artifact discarded in
cycle 1.

## Carl (UI/generalist, gemini via copilot)

The diff has no frontend surface (Python scripts plus a Markdown skill file), so Carl
reviewed as a generalist per his persona's instruction not to invent frontend findings.
He read `write.py`, `docket.py`, the crash tests, the deleted constant tests, the
`SKILL.md` diff, and the integration test's edit path.

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

## Eve (doubt + de-slop, Fable 5)

Activated by the codex doubt-roster guard. She ran the distil-memory suite (522 passed)
and the create-skill validator (`[OK]`), verified all seven of her own cycle-1 findings
plus the six routed from other reviewers, then hunted the rework for regressions.

Her closure verdict, verbatim:

> Genuinely closed: CLI test coverage with field-by-field save mapping and the stdin
> contract (task 5), atomic writes with crash tests (task 6), the frontmatter-contract
> test now calling `proposal.validate` on a fixture that actually passes it (task 7), the
> invalid-edit path driven end to end (task 7), `dedup_error` carried through ingestion
> with three tests plus the SKILL.md step-3 warning (task 8), validator inputs documented
> (task 9), and all four task-10 items (docstring narrowed, both constant tests deleted,
> `next()` refactor, inert integration-test lines dropped).
>
> Not genuinely closed: the CLI-traceback finding (only `QueueError`/`WriteError` are
> caught; the pointer half of `write.py main` still tracebacks) and the two task-9
> findings about kept-before-published and name collisions (the new recovery prose is
> partly unexecutable and partly sitting-scoped).

Orchestrator transcription of her FIX items into the parseable line format (severities
assigned by the orchestrator, not by Eve):

```
[EVE] 🟠 write.py CLI still tracebacks when append_pointer fails (raw OSError on the MEMORY.md write, ProposalError on a drifted existing_text), directly contradicting the new SKILL.md:193 claim that "write" exits 1 and prints the reason to stderr instead of raising | File: skills/distil-memory/scripts/write.py:125 | Task: 5
[EVE] 🟠 The new "already exists" collision recovery is unexecutable as written: it routes through step 6's edit path, but that path ends in `decide "<id>" kept --file`, which raises "no undecided entry" for the already-kept entry (step 5 itself says re-deciding is impossible) | File: skills/distil-memory/SKILL.md:204 | Task: 9
[EVE] 🟠 The kept-before-published recovery is sitting-scoped only: a session dying between `decide kept` and a successful write leaves an entry that `next` skips forever, and the step-7 "list any kept whose write did not succeed" report can only name failures the same sitting witnessed | File: skills/distil-memory/SKILL.md:191 | Task: 9
[EVE] 🟡 The integration test's edit helper validates with `proposal.validate`, not the `proposal.validate_distil_output(proposal, index_has_names)` that SKILL.md step 6 mandates, so an edit failing only the distil-specific rules (metadata.type != project, empty body, missing wiki link against a populated index) passes the test but is refused by the documented walkthrough; its docstring claims it follows "the documented step-6 ordering" | File: skills/distil-memory/scripts/test_walkthrough_integration.py:86 | Task: 7
[EVE] 🟡 Step 6's snippet `dedup.read_index("<store-path>")` raises TypeError when the driver substitutes a plain string: read_index does `memory_dir / "MEMORY.md"`, which needs a Path | File: skills/distil-memory/SKILL.md:223 | Task: 9
[EVE] 🟡 `test_main_start_returns_zero` asserts only the exit code and cannot fail if `start` stops calling advance() | File: skills/distil-memory/scripts/test_docket.py:509 | Task: 5
[EVE] 🟡 The four crash-safety tests assert `pytest.raises(Exception)`, which also passes when the code fails before reaching the atomic move (e.g. a KeyError during setup), hollowing out the "intact after the move fails" proof | File: skills/distil-memory/scripts/test_write.py:483 | Task: 6
[EVE] ⚪ Unused `capsys` fixture parameters on the three new dedup_error CLI tests | File: skills/distil-memory/scripts/test_docket.py:638 | Task: 8
```

Her verbatim buckets:

```
FIX:
- write.py CLI still tracebacks when append_pointer fails (raw OSError on the MEMORY.md write, ProposalError on a drifted existing_text), directly contradicting the new SKILL.md:193 claim that "write" exits 1 and prints the reason to stderr instead of raising — skills/distil-memory/scripts/write.py:125 — wrap the append_pointer call in try/except (OSError, proposal.ProposalError), print to stderr, return 1
- The new "already exists" collision recovery is unexecutable as written: it routes through step 6's edit path, but that path ends in `decide "<id>" kept --file`, which raises "no undecided entry" for the already-kept entry (step 5 itself says re-deciding is impossible) — skills/distil-memory/SKILL.md:204 — reword: re-emit and validate per step 6, update the driver's entry.json by hand, then re-run only `write.py write`, skipping the decide
- The integration test's edit helper validates with `proposal.validate`, not the `proposal.validate_distil_output(proposal, index_has_names)` that SKILL.md step 6 mandates, so an edit failing only the distil-specific rules (metadata.type != project, empty body, missing wiki link against a populated index) passes the test but is refused by the documented walkthrough; its docstring claims it follows "the documented step-6 ordering" — skills/distil-memory/scripts/test_walkthrough_integration.py:86 — build the Proposal with kind/existing_text/dedup_error carried over and call validate_distil_output with index_has_names derived from store_path (verified: both current fixtures stay green with index_has_names=False)
- Step 6's snippet `dedup.read_index("<store-path>")` raises TypeError when the driver substitutes a plain string: read_index does `memory_dir / "MEMORY.md"`, which needs a Path — skills/distil-memory/SKILL.md:223 — change the snippet to `dedup.read_index(Path("<store-path>"))`
- The kept-before-published recovery is sitting-scoped only: a session dying between `decide kept` and a successful write leaves an entry that `next` skips forever, and the step-7 "list any kept whose write did not succeed" report can only name failures the same sitting witnessed — skills/distil-memory/SKILL.md:191 — add to step 1: at sitting start, re-run `write.py write` for any kept entry whose target file is absent from its store
- `test_main_start_returns_zero` asserts only the exit code and cannot fail if `start` stops calling advance() — skills/distil-memory/scripts/test_docket.py:509 — seed a queue whose session_decided is at PER_RUN_CAP, run main(["start"]), assert `next` yields an entry again
- The four crash-safety tests assert `pytest.raises(Exception)`, which also passes when the code fails before reaching the atomic move (e.g. a KeyError during setup), hollowing out the "intact after the move fails" proof — skills/distil-memory/scripts/test_write.py:483,508,533,557 — tighten to OSError for the append_pointer tests and write.WriteError for the write_memory test
- Unused `capsys` fixture parameters on the three new dedup_error CLI tests — skills/distil-memory/scripts/test_docket.py:638,663,688 — delete the parameter
VERIFY:
- (none)
KNOWN:
- `docket.py`'s `_save_queue` leaves its `.tmp` file behind when the write fails, unlike write.py's new `_atomic_write` — out of scope: pre-existing behavior in a lightly-touched file, the queue is a dev/local artifact, and no cycle-1 finding or rework task covers it
- `docket.py main save` still tracebacks on a missing or malformed proposals.json — out of scope: its input is the distil stage's atomically published directory, so malformation cannot occur through the documented flow, and guarding it would be defensive validation of an impossible state (coding-style rule); cycle-1's traceback finding named only QueueError/WriteError, both now handled
```

```
D1: pass
D2: pass
D3: pass
D4: pass
D5: pass
```

## Decision gate outcome — rework cap reached

`state.cycle` is 2 and `state.rework_cap` is 2, so this cycle is **at cap**. Five 🟠 High
findings remain unresolved and none is a settled deferral, so the review did **not**
converge. There is **no 🔴 Critical finding**, so the loop-mode cap-out branch applies:
every unresolved finding is recorded in `state.deferred_decisions` as a `cap-overflow`
record and the PRD finalizes as **converged-with-deferrals**. No third review cycle runs,
and **no rework was dispatched for any finding in this file**.

Stated plainly, because it is the thing a reader most needs to know: **the fifteen
findings above are deferred to batch end, not fixed.** The five High ones are all real,
all orchestrator-verified, and all concentrated in one place — the `SKILL.md` walkthrough's
publication-failure and name-collision recovery prose added by task 9, plus the
`append_pointer` error path in `write.py main` that the prose describes incorrectly. The
shipped *code* for the queue, the cursor, the rejection record, the atomic writes and the
memory-write contract is clean by all five lenses; what is broken is the documented
recovery for two failure modes, and one unguarded error path behind it.

Verdict: 15 findings
Tests: 963 passed, 0 failed, 5 skipped
