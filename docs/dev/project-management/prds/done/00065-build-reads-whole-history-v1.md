---
default_model: sonnet
model_tier_rationale: one expression given, one additive test
design: skip
---

# Every build reads the whole history.jsonl, which grows forever

## Problem

`skills/brief-portfolio/scripts/build.py` reads the entire `history.jsonl` and
then keeps the last 60 lines, while `collect.py` appends one line per run and
never prunes. No budget is stated, so this is an observation: at today's cadence
(4 lines, 11.8 KB; about 1 MB per year of daily runs) nothing is user-visible
for years, but memory grows linearly with the file. Source: agoge run
`dev/local/audit-results/agoge-2026-09-05.md`, finding 15 (LOW, performance
lane, verified, no budget); decision 2026-09-05: read the tail only. History
rotation in `collect.py` was declined because it drops old history.

```
Wrapped Path.read_text: 1 000 lines read 2 922 890 bytes, 10 000 lines read
29 238 890 bytes, page keeps exactly 60 both times; peak RSS 36 MB vs 119 MB.
```

## Solution

Replace the read-everything-then-slice with
`collections.deque(((n, line) for n, line in enumerate(handle, 1) if line.strip()), maxlen=60)` over the open file, so memory is bounded
by 60 retained nonblank raw lines (plus the current iterator line), whatever the file size; the file is still scanned once. Compose
with PRD 00059's per-line decode loop: the deque holds physical line-number/raw-line pairs; the loop decodes
and skips invalid retained lines, with no backfill from older rows. Only
retained malformed lines warn, using their original physical line numbers. Land after 00059.

## Requirements

### Must have

- `build.py` retains at most 60 nonblank raw history lines in its tail buffer.
- The trend series is identical to today's for any file of 60 lines or fewer,
  and equals the last-60-nonblank selection for longer files, using 00059's
  tolerant decoding. Blank rows do not consume the window.

### Nice to have

- none

## Implementation

### Module: build.py

- **Location**: `skills/brief-portfolio/scripts/`
- **Responsibility**: Read the history tail in constant memory.
- **Exports**: `main()`, unchanged CLI

### Module: test_build_page.py

- **Location**: `skills/brief-portfolio/scripts/`
- **Responsibility**: Pin the bound.
- **Exports**: pytest cases

### Dependencies

- build.py: Depends on [PRD 00059's decode loop]
- test_build_page.py: Depends on [build.py]

## Tasks

### Phase 0: Foundation

- [ ] Read `history.jsonl` through the pinned nonblank, line-numbered deque over an open handle (depends on: PRD 00059) - Acceptance: a new test `test_the_build_keeps_the_last_sixty_history_rows_without_reading_the_whole_file` writes 1 000 rows, patches the whole-file read (`Path.read_text` or whatever `build.py` used before this task) to raise when called for `history.jsonl`, runs the build, and asserts the injected history series has 60 points whose last `at` equals the file's last row; trailing/interspersed blanks preserve the 60-row window, and malformed selected rows warn with physical line numbers without backfilling older rows; `uv run pytest skills/brief-portfolio/scripts -q` reports 0 failing.

### Phase 1: Core

- none

## Success Criteria

- The new test passes, and every existing `test_build_page.py` test passes
  unchanged.
- Re-running the report's measurement confirms the bounded retention algorithm; record comparative RSS as
  observational evidence, not an exact allocator-dependent equality.
