---
default_model: sonnet
model_tier_rationale: two lines with an exact condition, one additive test
design: skip
---

# After a torn history line, the next collect appends onto it and loses its own row

## Problem

`main()` in `skills/brief-portfolio/scripts/collect.py` (about lines 517-518)
appends to `history.jsonl` with a plain `open(..., "a")` and never checks that
the file ends in a newline, so a torn tail from a killed run swallows the next
run's row into one invalid line. The first run after the tear loses its history
point, and the fused line keeps tripping `build.py` until someone hand-edits
the file (PRD 00059 makes the build step over it). Source: agoge run
`dev/local/audit-results/agoge-2026-09-05.md`, finding 7 (MEDIUM, integration
lane, status mocked: gh shim, the append itself is real); decision 2026-09-05:
newline guard before the append. Atomic rewrite and rotation were declined.

```
After printf '{"at":' >> history.jsonl, the next run's wc -l is 5 but the last
line reads {"at":{"at": "2026-09-05T04:52:18+00:00", ...}}: two rows fused,
exit 0, no WARN.
```

## Solution

Before appending, if `history.jsonl` exists, is non-empty and its last byte is
not `\n`, write a `\n` first. The torn fragment stays as its own bad line for
`build.py` to skip; that was the option's named drawback.

## Requirements

### Must have

- A run after a torn tail appends its row on a new line: the file gains one
  line that decodes on its own, and the torn fragment is unchanged.
- A healthy file is appended to exactly as today.

### Nice to have

- none

## Implementation

### Module: collect.py

- **Location**: `skills/brief-portfolio/scripts/`
- **Responsibility**: Never fuse two history rows.
- **Exports**: `main()`, unchanged CLI

### Module: test_collect_history.py

- **Location**: `skills/brief-portfolio/scripts/`
- **Responsibility**: Pin the guard.
- **Exports**: pytest cases

### Dependencies

- collect.py: No dependencies (foundation)
- test_collect_history.py: Depends on [collect.py]

## Tasks

### Phase 0: Foundation

- [ ] Add the newline guard before the history append in `main()` - Acceptance: a new test `test_a_torn_history_tail_does_not_swallow_the_next_row` pre-writes `history.jsonl` as `{"at":` with no trailing newline, runs `main()` against a fake registry with `collect.run` stubbed, and asserts the file has exactly 2 lines, the first is `{"at":` and `json.loads` of the second succeeds; `uv run pytest skills/brief-portfolio/scripts -q` reports 0 failing.

### Phase 1: Core

- none

## Success Criteria

- The new test passes; the existing history-row tests pass unchanged.
- The report's reproduction can no longer fuse rows: one new independently decodable record is appended per run. Repairing
  an unterminated tail also adds its missing separator; subsequent appends
  add only the new record's newline. The last record always decodes.
