# Decision Audit Log: 00017-malformed-memory-half-written-v1

PRD: `00017-malformed-memory-half-written-v1.md`
Started: 2026-09-06T09:15:27Z
Completed: 2026-09-06T09:15:27Z
Autonomous: 9  |  Deferred: 0  |  Doubts: 0

### [autonomous] 2026-09-06T09:15:27Z

**Decision**: PRD cites docket.py read sites at lines 177/185/211, but PRD 00016 moved them to 203/211/238. Which is the contract?

**Choice**: The code SITES are the contract, not the line numbers; tasks 3 and 4 name the current lines and flag the PRD numbers as stale.

### [autonomous] 2026-09-06T09:15:27Z

**Decision**: PRD pins `except (OSError, json.JSONDecodeError)` for the two docket.py read sites, which misses UnicodeDecodeError on a non-utf8 file; docket.load() catches all three. Widen or follow verbatim?

**Choice**: Follow the PRD verbatim. No acceptance criterion covers non-utf8 at these sites, and widening beyond the stated contract is scope creep.

### [autonomous] 2026-09-06T09:15:27Z

**Decision**: Task 3 acceptance names test_docket.py verbatim, but the docket tests were split and test_docket_exit_codes.py is the topical home for main() exit-code guards. Which module gets the new tests?

**Choice**: Append to test_docket.py - the module the PRD acceptance command literally names and exercises. 441 lines, well under the 800-line style limit, so no split is forced. test_docket_exit_codes.py is the more cohesive home; flagged for review.

### [autonomous] 2026-09-06T09:15:27Z

**Decision**: Bob (doubt lens) claims write.py main() is missing a required index snapshot before mutation.

**Choice**: Discarded as refuted by the code, not researched. _atomic_write (write.py:31-38) writes a temp file and replaces it, unlinking the temp on OSError, so a failed index write leaves MEMORY.md at its previous bytes or its original absence. The only index writes are append_pointer:99 and :103 and nothing can fail after them, so the PRD requirement to preserve the index bytes or absence already holds without an explicit snapshot. Alice traced the same control flow and agreed.

### [autonomous] 2026-09-06T09:15:27Z

**Decision**: Bob asks to delete assert exit_code != 2 at test_docket_exit_codes.py:240 as redundant with assert exit_code == 1, and raises two Cannot-statically-verify VERIFY items.

**Choice**: All three discarded. The != 2 assertion is the rule the test is named for (PRD 00015 exit-2 boundary) and rules/testing.md requires tests to bind to the rule they enforce, so deleting it trades intent-binding for one line. The two VERIFY items are codex sandbox artifacts already answered by evidence in hand: last-verification.json records all three project checks exiting 0 at the reviewed HEAD be34106, and the computed fail-first replay block already reports 12 of 16 touched tests failing against base with 3 new files uncollectable there by construction.

### [autonomous] 2026-09-06T09:15:27Z

**Decision**: Bob raised two HIGH findings at 1/4 consensus from a static-only sandbox: read_text() breaks byte-exact rollback restoration, and an undecodable MEMORY.md escapes append_pointers handler.

**Choice**: Both CONFIRMED by reading write.py rather than taken on trust. (1) previous = target.read_text() at write.py:147 applies universal-newline translation, so a CRLF memory file is restored as LF and the PRD Must-have restore the original target bytes is violated; the codes own comment at write.py:145-146 says only the bytes on disk are what a rollback owes back, so the code contradicts its own contract. (2) append_pointer reads MEMORY.md at write.py:93 and main catches (OSError, ProposalError, KeyError) at write.py:154; UnicodeDecodeError subclasses ValueError, not OSError, so a non-UTF-8 index escapes as a traceback with the memory file already written at write.py:148 and no rollback, which is exactly the PRD Success Criterion about the re-run recovery hitting already exists. Both routed to rework as task D1-a rather than deferred.

### [autonomous] 2026-09-06T09:15:27Z

**Decision**: What model tier should the two [D1] decision-gate follow-up tasks run at?

**Choice**: opus. These are brand-new first-pass tasks, not review-flagged retries, so no escalation ladder applies; the plan-tasks classifier would put them at sonnet, and the PRD frontmatter default_model: opus is the floor, so final_tier = max(sonnet, opus) = opus. The frontmatter rationale (failure rollback must preserve existing persisted memories and their index) is exactly what D1-a touches.

### [autonomous] 2026-09-06T09:15:27Z

### [autonomous] 2026-09-06T09:15:27Z
