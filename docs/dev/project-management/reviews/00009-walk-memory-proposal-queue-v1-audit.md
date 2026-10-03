# Decision Audit Log: 00009-walk-memory-proposal-queue-v1

PRD: `00009-walk-memory-proposal-queue-v1.md`
Started: 2026-08-31T01:33:17Z
Completed: 2026-08-31T01:33:17Z
Autonomous: 10  |  Deferred: 16  |  Doubts: 0

### [autonomous] 2026-08-31T01:33:17Z

**Decision**: queue.save()'s skip rule said skip on (a) slice_key already queued in ANY decision state OR (b) rejected() true - but (a) alone (any decision state) would block a dropped entrys slice_key forever regardless of rubric version, contradicting the acceptance criterion that a rubric bump re-opens drops.

**Choice**: Scoped condition (a) to undecided/kept decisions only; a dropped entrys re-eligibility is governed solely by rejected() (which already checks rubric version). Updated task 1s persisted Contract to this corrected wording. Consistent with the design docs own Likely next changes note that a rubric bump re-opens ALL drops.

### [autonomous] 2026-08-31T01:33:17Z

**Decision**: Tess's per-run-cap test decided all 15 remaining proposals in a single second sitting after one advance() call, which only holds if the cap permanently lifts after the first advance(). The design's own advance() contract says each advance() unlocks only the NEXT PER_RUN_CAP (10) calls, repeatable - a queue of 25 needs three capped sittings (10+10+5), not two.

**Choice**: Fixed the test to assert the correct repeatable per-sitting cap: second sitting drains exactly 10 more (cursor 20, 5 remain), a second advance() drains the final 5 (cursor 25). Verified red against Ivan's existing implementation (which used a permanent cap_lifted model matching the old buggy test) - confirms a real implementation fix is needed, not just a test tweak.

### [autonomous] 2026-08-31T01:33:17Z

**Decision**: queue.py's Contract (design doc + task 1) names a thin argparse CLI (save/start/next/decide/cursor) as part of the module, explicitly described as untested-beyond-smoke - Tess correctly wrote no CLI tests since the design doc says the CLI is not the tested contract. But nothing then forced Ivan (tests-are-the-spec, no acceptance criteria) to build it, and task 3 (SKILL.md walkthrough) needs this CLI to exist for its prose to be accurate.

**Choice**: Implemented the CLI directly via Edit (not another Ivan dispatch) since it is a thin, low-ambiguity wrapper over already-implemented and already-tested pure functions, then independently smoke-tested every subcommand (save/start/next/decide/cursor) by hand in a scratch /tmp directory - matching the design doc's own untested-beyond-smoke standard for this surface.

### [autonomous] 2026-08-31T01:33:17Z

**Decision**: Pat's 3rd review cycle (the cap) surfaced one new MEDIUM: test_queue.py's _proposal() fixture hardcodes the literal string "new" instead of importing proposal.NEW, so it could silently drift from proposal.py's canonical constant.

**Choice**: Per the per-task-review 3-cycle cap, proceeding with warning rather than dispatching a 4th Ivan/Pat cycle: this is a test-fixture maintainability nitpick (both sides currently hold the identical string "new", so there is no functional bug), not a correctness defect, and it is left for the PRD-level review lenses (Alice/Blake/Eve, which independently review the whole diff) to flag again if warranted.

### [autonomous] 2026-08-31T01:33:17Z

### [autonomous] 2026-08-31T01:33:17Z

### [autonomous] 2026-08-31T01:33:17Z

### [autonomous] 2026-08-31T01:33:17Z

### [autonomous] 2026-08-31T01:33:17Z

### [autonomous] 2026-08-31T01:33:17Z

### [deferred] 2026-08-31T01:33:17Z

**Decision**: Memory-file and MEMORY.md symlinks can escape the selected store and overwrite external files (skills/distil-memory/scripts/write.py:39)

**Rationale**: Review cycle 1 settled deferral. The memory store is the operators own directory reached from the source transcripts location; not a trust boundary, no untrusted input. Containment checks would be defensive validation for a state that cannot occur (rules/coding-style.md).

### [deferred] 2026-08-31T01:33:17Z

**Decision**: RUBRIC_VERSION is hand-maintained and coupled to distil.py _DISTIL_PROMPT only by a code comment (skills/distil-memory/scripts/docket.py)

**Rationale**: Review cycle 1 settled deferral. Hand-maintenance is the specified design; the task contract says bump by hand. Automating the coupling would re-open every drop on any incidental prompt edit.

### [deferred] 2026-08-31T01:33:17Z

**Decision**: SKILL.md already-exists recovery is non-functional: for a new kind entry, write.py _target_stem() derives the target stem from entry["name"] and never reads the re-emitted frontmatter name, while the documented edit-path rename replaces only file_text, so the collision reproduces (skills/distil-memory/SKILL.md, ALICE, verified empirically)

**Rationale**: rework cap reached with this finding unresolved

### [deferred] 2026-08-31T01:33:17Z

**Decision**: SKILL.md already-exists recovery is additionally unexecutable: the step-6 edit path it routes through ends in decide <id> kept --file, which raises no-undecided-entry for an already-kept entry (skills/distil-memory/SKILL.md:204, EVE). Independently fatal from the _target_stem defect; fixing one leaves the other

**Rationale**: rework cap reached with this finding unresolved

### [deferred] 2026-08-31T01:33:17Z

**Decision**: Failed-publication retry is blocked after an index-write failure: the memory file is already on disk, so re-running write.py write stops at already-exists inside write_memory and never reaches append_pointer (skills/distil-memory/SKILL.md:191, BOB)

**Rationale**: rework cap reached with this finding unresolved

### [deferred] 2026-08-31T01:33:17Z

**Decision**: write.py main leaves the append_pointer call unguarded, so a MEMORY.md write failure escapes as a raw OSError or ProposalError traceback, contradicting the new SKILL.md:193 claim that write exits 1 and prints the reason to stderr instead of raising (skills/distil-memory/scripts/write.py:125, EVE)

**Rationale**: rework cap reached with this finding unresolved

### [deferred] 2026-08-31T01:33:17Z

**Decision**: Kept-before-published recovery is sitting-scoped only: a session dying between decide kept and a successful write strands the entry permanently, since next_undecided skips decided entries and save refuses to re-queue the slice_key, and the step-7 report can only name failures its own sitting witnessed (skills/distil-memory/SKILL.md:191, EVE)

**Rationale**: rework cap reached with this finding unresolved

### [deferred] 2026-08-31T01:33:17Z

**Decision**: test_walkthrough_integration _attempt_edit_then_publish validates with proposal.validate, not the proposal.validate_distil_output(proposal, index_has_names) that SKILL.md step 6 mandates, while its docstring claims to model the documented step-6 ordering; an edit failing only the distil-specific rules passes the test but is refused by the walkthrough (skills/distil-memory/scripts/test_walkthrough_integration.py:86)

**Rationale**: rework cap reached with this finding unresolved

### [deferred] 2026-08-31T01:33:17Z

**Decision**: SKILL.md:223 index_has_names snippet passes a plain string to dedup.read_index, which does memory_dir / MEMORY.md and requires a Path, so the documented validation raises TypeError

**Rationale**: rework cap reached with this finding unresolved

### [deferred] 2026-08-31T01:33:17Z

**Decision**: The four crash-safety tests assert pytest.raises(Exception), so a failure before the atomic move is reached also satisfies them, hollowing out the intact-after-the-move-fails proof (skills/distil-memory/scripts/test_write.py:483,508,533,557)

**Rationale**: rework cap reached with this finding unresolved. Consolidator printed BOB and EVE as two 1/5 rows because they anchored different lines; real consensus is 2/5

### [deferred] 2026-08-31T01:33:17Z

**Decision**: test_main_start_returns_zero asserts only the exit code and cannot fail if start stops calling advance() (skills/distil-memory/scripts/test_docket.py:509, EVE)

**Rationale**: rework cap reached with this finding unresolved

### [deferred] 2026-08-31T01:33:17Z

**Decision**: PRD Phase 2 acceptance text names a temporary store under dev/local/tmp/, but test_walkthrough_integration.py uses pytest tmp_path (system TMPDIR); functionally equivalent, literal deviation (BLAKE)

**Rationale**: rework cap reached with this finding unresolved

### [deferred] 2026-08-31T01:33:17Z

**Decision**: docket.py decide and advance carry keyword parameters (file_text, path, new_cursor) beyond the PRD Structural Decomposition Exports signatures; functionally required by the specs own re-emit-on-edit feature and temp-store testing, recorded as a literal deviation (BLAKE)

**Rationale**: rework cap reached with this finding unresolved

### [deferred] 2026-08-31T01:33:17Z

**Decision**: docket.py load/save/decide perform a non-atomic read-modify-write across separate CLI invocations with no file lock, so concurrent use could lose an update (BLAKE). The design doc Risks section already scopes concurrency out for this solo-maintainer tool

**Rationale**: rework cap reached with this finding unresolved

### [deferred] 2026-08-31T01:33:17Z

**Decision**: docket.load calls json.loads with no try/except, so a corrupted or hand-edited queue.json raises JSONDecodeError as a traceback rather than the clean stderr message QueueError and WriteError now get (skills/distil-memory/scripts/docket.py, BLAKE)

**Rationale**: rework cap reached with this finding unresolved

### [deferred] 2026-08-31T01:33:17Z

**Decision**: Unused capsys fixture parameters on the three new dedup_error CLI tests (skills/distil-memory/scripts/test_docket.py:638,663,688, EVE)

**Rationale**: rework cap reached with this finding unresolved
