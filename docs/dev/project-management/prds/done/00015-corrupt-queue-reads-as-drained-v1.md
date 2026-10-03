---
default_model: sonnet
rework_cap: 5
design: skip
---

# A corrupt review queue reads as a drained one

## Problem

`load()` in `skills/distil-memory/scripts/docket.py:42-47` calls `json.loads(p.read_text())` with no schema
check and no error handling, so a corrupt queue raises a bare `JSONDecodeError` or `KeyError` out of
`next_undecided()`. The step-2 command redirects stdout only (`SKILL.md:160`), so the driver sees empty stdout
and a non-zero exit: exactly what `SKILL.md:163-165` defines as drained or capped, "Stop and report". Five
corruption classes look the same there, and the step-7 cross-check (`SKILL.md:246-257`) agrees, because
`cursor` exits 0 printing `0`, so the sitting reports every proposal reviewed when none were readable. Source:
agoge run `dev/local/audit-results/agoge-2026-08-31.md`, finding 5 (HIGH, integration lane); decision
2026-09-02: validate in `load()` and separate the exit codes.

```
Five corruption classes, all identical from the driver's point of view —
next  exit=1  stdout=''  for truncated JSON, a missing entries key, non-dict
entries, a top-level list, and an empty file. The cross-check SKILL.md step 7
prescribes lies too: cursor  exit=0  stdout='0' over broken state.
```

## Solution

Validate inside `load()` and raise `QueueError` (`docket.py:14`) naming the corruption class, copying braid's
`_load_state` (`src/agent_skills_braid/cli.py:219-241`) without sharing code between the skills. Split the exit
codes in `main()`: `next` keeps exit 1 with empty stdout for "nothing left" and returns 2 with the reason on
stderr for "queue unreadable". Document both exits in `SKILL.md` steps 2 and 7, and drop the xfail marker.

## Requirements

### Must have

- `load()` raises `QueueError` for each class agoge exercised: unparseable text, an empty file, a non-dict top
  level, a missing or non-list `entries`, and a non-dict entry.
- Messages mirror braid: `cannot read the review queue <path>: <error>` and `invalid review queue schema in
  <path>: <what>`.
- `next` returns 2 with the message on stderr when the queue is unreadable, and keeps exit 1 with empty stdout
  when nothing is left. `cursor`, `start` and `save` return 2 too, while `decide` keeps exit 1 for a refused decision, as `CHANGELOG.md:27-29` ships.
- `SKILL.md` steps 2 and 7 name both exits.

### Nice to have

- none

## Implementation

### Module: docket
- **Location**: `skills/distil-memory/scripts/`
- **Responsibility**: queue persistence and the CLI the walkthrough drives
- **Exports**: `QueueError`, `load()`, `cursor()`, `main()`

### Module: test_docket
- **Location**: `skills/distil-memory/scripts/`
- **Responsibility**: the queue's regression suite
- **Exports**: `test_a_corrupt_queue_is_named_as_corrupt_rather_than_read_as_drained`

### Module: SKILL
- **Location**: `skills/distil-memory/`
- **Responsibility**: the approval walkthrough the driver follows
- **Exports**: step 2 (`next`), step 7 (sitting report)

### Dependencies
- docket: No dependencies (foundation)
- test_docket: Depends on [docket]
- SKILL: Depends on [docket]

## Tasks

### Phase 0: Foundation

- [ ] Validate the loaded queue and raise `QueueError` per class - Acceptance: `uv run pytest
  skills/distil-memory/scripts/test_docket.py -q` passes with the `@pytest.mark.xfail(...)` block at
  `test_docket.py:730-734` deleted and `rg -n "xfail" skills/distil-memory/scripts/test_docket.py` printing
  nothing, plus one new test per remaining class (empty file, top-level list, no `entries`, non-dict entry)
  asserting `pytest.raises(docket.QueueError)` from `docket.next_undecided(path=queue_path)` with a different
  `str(exc)` each.
- [ ] Split the CLI exit codes - Acceptance: `uv run pytest skills/distil-memory/scripts/test_docket.py -q`
  passes with new tests that chdir into `tmp_path` (the pattern at `test_docket.py:402-411`), write `{"cursor":
  0, "entries": [` into `dev/local/audit-results/distil-memory-queue.json` under it, and assert
  `docket.main(["next"]) == 2`, `docket.main(["cursor"]) == 2` and non-empty `capsys` stderr for both, while an
  all-decided queue still gives `docket.main(["next"]) == 1` with empty stdout.
- [ ] State the split in `SKILL.md` - Acceptance: `rg -n "exit 2" skills/distil-memory/SKILL.md` matches in step
  2 (near line 163) and step 7 (near line 246), naming exit 1 for drained-or-capped and exit 2 for unreadable.

## Success Criteria

- Each corruption class exits 2 from `docket.py next`, naming itself on stderr; drained or capped still exits 1
  with empty stdout.
- `uv run pytest skills/distil-memory/scripts -q` reports no failures and no xfailed tests.
- `rg -n --files-with-matches "docket" skills src tests` lists only `skills/distil-memory/SKILL.md` and three
  test files, so `SKILL.md` is the whole caller sweep for the new exit code.

## Post-completion notes (2026-09-06)

Deferred by batch 202609050909 (cycles 1 and 2), decided 2026-09-06 in the
config-audit closure check (`~/.claude/dev/local/audit-results/2026-09-05.md`).

- The Phase 0 acceptance names `test_docket.py` and the caller sweep above
  expects three test files; the exit-code tests landed in
  `test_docket_exit_codes.py` (224 lines) because merging them into the
  780-line `test_docket.py` would breach the 800-line file limit, so the sweep
  returns four files. The criterion's intent holds; the literal text is stale
  and stays as written. Reviewers agreed 3 of 3.
- "no xfailed tests" across `skills/distil-memory/scripts` is not met by one
  pre-existing xfail in `test_write.py` (`append_pointer` outside the main
  `WriteError` guard), which predates this PRD and belongs to backlog PRD
  00017. This PRD's own xfail block in `test_docket.py` was deleted as required.
- `braid --check` never ran in this PRD's sessions because warden blocked
  braid; buvis commit 1f71e28e (2026-09-05) allows it. Not a gate for this diff.
