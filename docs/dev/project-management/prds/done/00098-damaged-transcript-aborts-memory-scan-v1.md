---
design: skip
default_model: sonnet
model_tier_rationale: bounded transcript input resilience with mixed-corpus CLI regression tests
---

# One damaged transcript aborts the entire memory scan

Source: agoge report `dev/local/audit-results/agoge-2026-10-26.md`, finding 9,
accepted option A on 2026-10-27. The report is a local audit artifact and is not
shipped in the public repository.

## Problem

The memory-extraction funnel skips invalid JSON syntax but assumes every parsed
value is an object and every transcript is UTF-8. A scalar, list, or decoding
failure raises an exception and prevents the whole collection from producing
a report. Operators cannot extract useful memory from otherwise valid transcripts
until the damaged input is found and removed.

## Solution

Skip non-object transcript entries and isolate decoding failures to the affected
file. Warn on stderr when either condition is encountered, identifying the file
and the line when available. Continue processing valid entries and other files
so the normal yield report remains available.

## Requirements

### Must have

- JSON scalar, list, and null entries do not reach object-only entry processing.
- A file with invalid UTF-8 does not abort scanning other transcripts.
- Newly skipped non-object entries and decoding failures produce visible stderr
  warnings, without printing transcript contents.
- Valid entries in the mixed corpus still contribute their normal slices and counts.
- Dry-run completes with a report despite the reported malformed inputs.
- Preserve assistant-only filtering, marker matching, and existing model-failure behavior.

### Nice to have

- None.

## Implementation

```text
skills/distil-memory/scripts/
├── funnel.py             # guard entry shape and isolate per-file decoding failures
└── test_funnel_main.py  # mixed-corpus CLI regressions and valid-input controls
```

### Module: transcript scan

- **Location**: `skills/distil-memory/scripts/funnel.py`
- **Maps-to-capability**: continue useful extraction when individual inputs are damaged.
- **Responsibility**: validate parsed entry shape and warn on isolated input failures.
- **Exports**: `_iter_entries`, `scan`, `main`.

#### Feature: isolate malformed transcript inputs

- **Inputs**: transcript paths containing valid objects and malformed entries or encoding.
- **Outputs**: existing slice and count results, plus stderr warnings for skipped input.
- **Behavior**: skip non-object entries and catch decoding failure per file rather
  than allowing it to terminate the collection scan. Continue with other files.

### Module: mixed-corpus regression tests

- **Location**: `skills/distil-memory/scripts/test_funnel_main.py`
- **Maps-to-capability**: prove one damaged input cannot prevent a useful report.
- **Responsibility**: exercise valid and damaged temporary transcripts through dry-run.
- **Exports**: none.

### Dependencies

- Transcript scan: existing entry iteration and filtering (foundation).
- Mixed-corpus tests: depend on the scan and existing CLI test fixtures.
- Report generation consumes the existing scan output contract (integration).

## Tasks

### Phase 0: Foundation

- [ ] Add failing dry-run regressions with a valid transcript, non-object JSON
  lines, and a non-UTF-8 transcript in one collection. Guard entry shape and
  isolate decoding errors per file, with stderr warnings. Assert the valid
  transcript contributes expected slices and counts, a report is written,
  no traceback occurs, and warnings identify affected paths without leaking
  transcript text. Put valid files before and after the damaged file to verify
  processing continues. Keep existing model and report-write failure tests valid.
  Acceptance: `uv run pytest skills/distil-memory/scripts/test_funnel_main.py`
  passes; non-object and invalid-encoding regressions fail against the prior code.
  The unmerged branch `agoge/authored-tests-2026-10-26` holds strict-xfail
  regressions for this finding. Implement independently if absent; if present,
  convert them to normal tests without merging unrelated branch changes.

Exit criteria: `uv run pytest`,
`uv run python3 skills/create-skill/scripts/validate_skill.py skills/distil-memory`,
and `braid --check` pass.

## Success Criteria

- A mixed valid/damaged corpus completes dry-run and writes its yield report.
- Valid transcripts remain available for extraction despite a damaged neighbor.
- Warnings expose skipped malformed input without exposing transcript contents.

### Test Strategy

Carry the observed evidence verbatim from the accepted packet:

```text
`funnel.py --days 3650 --dry-run` over a transcript with lines `123` and `[1,2]` -> `AttributeError: 'int' object has no attribute 'get'`. A transcript beginning with bytes 0xFF 0xFE -> `UnicodeDecodeError: 'utf-8' codec can't decode byte 0xff in position 0`. Both: traceback, no report. Seams that held: `claude` exit 1 -> exit 1 with stderr; the tier reaches the request (`--model haiku`).
```

Use isolated temporary transcripts and existing dry-run fixtures; do not scan the
operator's real corpus or invoke a live model for regression verification.

### Risks

Skipping input can hide a changed transcript format unless warnings remain
visible. Catch only the intended input failures; unrelated programming, model,
and report-write errors must not become silent successes.
