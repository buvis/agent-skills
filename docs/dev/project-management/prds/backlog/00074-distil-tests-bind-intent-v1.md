---
default_model: sonnet
model_tier_rationale: each edit names the exact assertion to add or the exact parameter to drop
design: skip
catchup: force
---

# Four distil-memory tests pass without proving what they claim

## Problem

Four leftovers from PRD 00009's review, verified at HEAD on 2026-09-05, in
`skills/distil-memory/scripts/`:

1. `test_walkthrough_integration.py` line 86 validates an edited proposal
   with `proposal.validate(candidate)` while its docstring says it models the
   documented step 6, which mandates
   `proposal.validate_distil_output(proposal, index_has_names)`; an edit
   failing only the distil-specific rules passes the test and is refused by
   the walkthrough (MEDIUM, 3/5).
2. The four crash-safety tests now in `test_write_crash_safety.py` (lines 29,
   54, 79, 104 at HEAD 076b306:
   `test_append_pointer_leaves_memory_md_fully_intact_when_the_move_fails_appending_a_new_line`,
   `..._replacing_a_line_in_place`,
   `test_write_memory_update_leaves_the_existing_file_fully_intact_when_the_move_fails`,
   `test_append_pointer_leaves_no_leftover_tmp_file_when_the_write_step_itself_fails`)
   were written against `pytest.raises(Exception)`; PRD 00017 has since given
   the injected faults exact types and messages, so re-check each at execution
   time and keep the ones that already bind as the baseline (MEDIUM, 2/5).
3. `test_docket_cli.py` line 122 `test_main_start_returns_zero` asserts only the
   exit code and cannot fail if `start` stops calling `advance()` (MEDIUM,
   1/5).
4. `test_docket_cli.py` declares a `capsys` parameter it never reads in three
   tests (lines 251, 277 and 302 at HEAD 076b306) (LOW).

Source: batch 202608290848 deferred items on PRD 00009 (cap-overflow, cycle
2); decided 2026-09-05: one test-only PRD. Land after PRD 00071, which
touches the same files.

## Solution

Bind each test to its intent: derive `index_has_names` from the temporary
store and call `validate_distil_output`; narrow the four `raises` to the
exact exception the patched move produces (`OSError` from the patched
`Path.replace`, or `WriteError` where `write_memory` wraps it) and assert on
its message; make the `start` test assert the effect `advance()` leaves
(start with a capped queue and a remaining undecided entry, assert start
reopens that entry while leaving the lifetime cursor unchanged); drop the three unused parameters. Re-ground by test name after 00017/00071,
preserving their rollback/recovery tests. Add a general-valid but distil-invalid
edited proposal (no wiki link with a nonempty index) and assert no decision
or write occurs, so the validator distinction is actually observed.

## Requirements

### Must have

- A targeted mutation of each behavioral contract makes its named test fail;
  record that red run. Unused-fixture cleanup is checked statically and has
  no production behavior to revert.
- No test is renamed or deleted.

### Nice to have

- none

## Implementation

### Module: test_walkthrough_integration.py, test_write_crash_safety.py, test_docket_cli.py

- **Location**: `skills/distil-memory/scripts/`
- **Responsibility**: Tests that fail when the behaviour they name changes.
- **Exports**: pytest cases

### Dependencies

- tests: Depends on [PRD 00071's write.py and docket.py changes]

## Tasks

### Phase 0: Foundation

- [ ] Bind the four tests (depends on: PRD 00071) - Acceptance: the four named crash-safety cases in `test_write_crash_safety.py` assert the injected exception and its message (cases that already do so count as the baseline and are left as they are), with no global ban on unrelated assertions; `rg -n "validate_distil_output" skills/distil-memory/scripts/test_walkthrough_integration.py` matches; `test_main_start_returns_zero` proves the capped queue is rearmed with lifetime cursor unchanged; the general-valid/distil-invalid edit cannot be decided or written; the three identified unused capsys parameters are absent, while fixtures actually used elsewhere remain; `uv run pytest skills/distil-memory/scripts -q` reports 0 failing.

### Phase 1: Core

- none

## Success Criteria

- The four checks above hold and the suite is green.
- Recorded mutations turn the behavioral regression tests red; a static
  signature check verifies the unused-fixture cleanup.
