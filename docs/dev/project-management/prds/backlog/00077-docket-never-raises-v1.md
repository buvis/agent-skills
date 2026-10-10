---
default_model: sonnet
model_tier_rationale: two exception tuples widened at named lines, one write guard, and tests specified per case
rework_cap: 3
catchup: force
design: skip
---

# The docket CLI still raises a traceback on undecodable input and failed writes

## Problem

PRD 00017 pinned `except (OSError, json.JSONDecodeError)` for the two `docket.py` read sites and the build
followed it verbatim, so four routes still print a traceback where `SKILL.md:203-207` promises an exit code
and a stderr reason. A traceback with empty stdout reads to the walkthrough driver as "drained or capped", the
misread PRD 00015 closed for corrupt queues. Source: batch 202609050909 deferred ledger, PRD 00017 rows
(`out-of-contract` x2, `out-of-scope`, `settled-deferral`, `known-gap` tasks 3 and 4, `assumed-ambiguity`);
decided 2026-09-06 in the config-audit closure walkthrough (`~/.claude/docs/dev/project-management/audit-results/2026-09-05.md`).

1. `_save_from_proposals_dir` (reads at `docket.py:207` and `:218`, `except` at `:223`) and the `decide --file` read (`docket.py:250`)
   catch `(OSError, json.JSONDecodeError)`; a non-UTF-8 file raises `UnicodeDecodeError`, a `ValueError`,
   which escapes `main`. `docket.load()` (`docket.py:50`) already guards its own read with
   `(OSError, UnicodeDecodeError, json.JSONDecodeError)`, so the module's own idiom is wider than the PRD tuple.
2. A `proposals.json` holding an object instead of a list, or a record missing a required key, raises
   `TypeError` or `KeyError` from `_save_from_proposals_dir`.
3. The `json.JSONDecodeError` arm on the plain-text `--file` read (`docket.py:251`) is dead: a text read never
   raises it.
4. `_save_queue` (`docket.py:30`) is unguarded, so an `OSError` during `save`, `decide` or `advance` (disk full,
   permission denied, unwritable parent) propagates as a raw traceback. Blake reproduced it live in review
   cycle 2 by monkeypatching `Path.write_text`. The PRD warned against widening the guard over the `save()` call
   because `save()` raises `QueueError` for a corrupt queue, which must keep exiting 2.

## Solution

Widen both read guards to `(OSError, ValueError)`: `ValueError` covers `UnicodeDecodeError` and
`json.JSONDecodeError`, so the dead arm disappears with the gap. Validate the loaded batch shape in
`_save_from_proposals_dir` before any sibling read or queue write: a non-list top level, a non-object record,
or a record missing any of the six keys the reader indexes (`name`, `file`, `kind`, `transcript`, `line_no`,
`evidence_text`, `docket.py:210-217`) exits 1 naming the fault and the record's position; the whole batch is
refused and nothing is saved. Guard the queue write where it is called, in the `save`, `decide` and `start`
verbs (`start` calls `advance()` internally), mapping `OSError` to exit 1 with
`cannot write the review queue <path>: <error>` on stderr, while `QueueError` keeps exit 2. `decide` keeps
its single queue read (`test_main_decide_reads_the_queue_once_so_no_later_read_can_be_taken_for_a_refusal`), and PRD 00071's `unpublished` exit
distinction (queue unreadable 2, store/index failure 1) is preserved when 00071 has landed. Messages
mirror the existing `cannot read the review queue` and `invalid review queue schema` wording.

## Requirements

### Must have

- A latin-1 `proposals.json`, a latin-1 sibling memory file and a latin-1 `decide --file` each exit 1 with the
  reason on stderr; no traceback.
- A `proposals.json` whose top level is an object, a record that is not an object, and a record missing any
  of `name`, `file`, `kind`, `transcript`, `line_no` or `evidence_text`, each exit 1 naming the fault;
  nothing is saved, even when readable records precede the bad one.
- An `OSError` from `_save_queue` during the `save`, `decide` and `start` verbs exits 1 with
  `cannot write the review queue <path>: <error>` on stderr, and the queue bytes on disk are unchanged.
- A corrupt queue still exits 2 from every verb (PRD 00015 unchanged); `decide` keeps exit 1 for a refused
  decision and reads the queue exactly once.
- `SKILL.md`'s exit-code lines (near 203-207) name the failed-write case; `CHANGELOG.md` gains a
  `**distil-memory**` entry under Fixed.

### Nice to have

- none

## Implementation

### Module: docket
- **Location**: `skills/distil-memory/scripts/`
- **Responsibility**: queue persistence and the CLI the walkthrough drives
- **Exports**: `_save_from_proposals_dir()`, `_save_queue()`, `main()`

### Module: test_docket_refusals
- **Location**: `skills/distil-memory/scripts/`
- **Responsibility**: the refusal and exit-code regressions; split if it nears 800 lines
- **Exports**: the tests named below

### Module: SKILL
- **Location**: `skills/distil-memory/`
- **Responsibility**: the exit-code contract the driver follows
- **Exports**: the exit-code lines near 203-207

### Dependencies
- PRDs 00015, 00016, 00017 (done): preserve their exit codes and read sites.
- PRD 00076 (backlog): shares `test_docket_refusals.py`; either order works, rebase the later one.
- docket: No dependencies (foundation)
- test_docket_refusals: Depends on [docket]
- SKILL: Depends on [docket]

## Tasks

### Phase 0: Foundation

- [ ] Widen the two read guards and validate the batch shape - Acceptance: `uv run pytest
  skills/distil-memory/scripts -q` reports 0 failing with new tests `test_save_refuses_a_latin1_proposals_file`,
  `test_save_refuses_a_latin1_sibling`, `test_save_refuses_an_object_top_level`,
  `test_save_refuses_a_non_object_record`, `test_save_refuses_a_record_missing_file`,
  `test_save_refuses_a_record_missing_evidence_text_after_readable_records` and `test_decide_refuses_a_latin1_file`
  asserting `docket.main(["save", "--proposals-dir", d]) == 1`, non-empty stderr naming the fault, and no queue
  file written, for a latin-1 `proposals.json`, a latin-1 sibling, an object top level, a string record, a record
  missing `file`, and a third record missing `evidence_text` behind two valid ones;
  `docket.main(["decide", entry_id, "kept", "--file", p]) == 1` for a latin-1 file with the entry still
  `undecided`; each watched red against the old code first.
- [ ] Guard the queue write in the `save`, `decide` and `start` verbs (depends on: nothing) - Acceptance: 0 failing
  with new tests `test_save_reports_a_failed_queue_write`, `test_decide_reports_a_failed_queue_write` and
  `test_start_reports_a_failed_queue_write` that monkeypatch `Path.write_text` to raise `OSError` and assert exit 1, stderr starting
  `cannot write the review queue`, and queue bytes unchanged, for each of the three CLI verbs (`start` is the
  verb; `advance()` is the function it calls); the existing corrupt-queue tests still assert exit 2 and
  `test_main_decide_reads_the_queue_once_so_no_later_read_can_be_taken_for_a_refusal` still passes.

### Phase 1: Core

- [ ] State the failed-write exit in `SKILL.md` and add the CHANGELOG entry (depends on: Phase 0) -
  Acceptance: `rg -n "cannot write the review queue" skills/distil-memory/SKILL.md` matches near the exit-code
  lines; `rg -n "distil-memory" CHANGELOG.md` matches under `[Unreleased]`; `uv run python3
  skills/create-skill/scripts/validate_skill.py skills/distil-memory/` reports the skill valid.

## Success Criteria

- `uv run pytest skills/distil-memory/scripts -q` reports 0 failing.
- None of the four routes above prints a traceback, including a record missing any of the six indexed keys;
  each exits 1 with its reason on stderr, and a corrupt queue still exits 2.
- `rg -n "json.JSONDecodeError" skills/distil-memory/scripts/docket.py` matches only inside `load()`.
