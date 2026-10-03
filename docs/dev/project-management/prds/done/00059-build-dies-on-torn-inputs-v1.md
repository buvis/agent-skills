---
default_model: sonnet
model_tier_rationale: exact behaviours and messages given, two authored xfails flip green
design: skip
---

# build.py dies with a traceback on a torn history line, a truncated data.json or an invalid epics.json

## Problem

`skills/brief-portfolio/scripts/build.py` calls `json.loads` unguarded on
`data.json` (about line 28), `epics.json` (about line 32) and every
`history.jsonl` line (about line 43), so a partial write from a killed collect
run (Ctrl-C, full disk, sleep) makes every later build exit with a Python
traceback and no page. SKILL.md tells the user never to delete `history.jsonl`,
so there is no sanctioned recovery. A missing `data.json` already exits cleanly
with "run collect.py first". Source: agoge run
`dev/local/audit-results/agoge-2026-09-05.md`, finding 6 (MEDIUM, journey +
integration lanes, verified); decision 2026-09-05: tolerate in build.py. Two
strict xfails landed on master in a550262.

```
python3 build.py --dir <S>/out3 with history.jsonl ending in {"at": ->
Traceback ... build.py line 43 ... json.decoder.JSONDecodeError: Unterminated
string, exit 1, no page written. Same shape at line 28 for a data.json cut to
105 531 of 211 063 bytes, and at line 32 for epics.json = {"summary": "x",
"repos": {. Missing data.json: the clean "missing ... run collect.py first".
```

## Solution

Select the last 60 nonblank raw history lines, preserving their original
1-based physical line numbers, then decode them. Skip a selected line that
json.loads rejects with
`WARN: history.jsonl line N skipped: <reason>` on stderr and keeping the rest,
so a torn line costs one history point, not the page. Do not backfill from
older lines; malformed rows outside the selected tail are not decoded or warned.
This is the shared retention rule later PRD 00065 must preserve. Wrap the `data.json` and
`epics.json` loads so a decode error exits with `sys.exit(f"{path}: {exc}")`,
naming the file, no traceback. PRD 00060 stops a tear from fusing the next row;
this PRD makes the build survive one that already exists.

## Requirements

### Must have

- A `history.jsonl` with one undecodable line builds the page, prints one WARN
  naming the line number, and the trend series has one point fewer.
- A truncated `data.json` exits non-zero with a one-line message naming the
  file and the decode error, and no traceback.
- An invalid `epics.json` exits the same way.
- The xfail markers on `test_a_torn_history_line_does_not_abort_the_build` and
  `test_a_truncated_data_json_exits_with_a_message_naming_the_file` in
  `skills/brief-portfolio/scripts/test_build_page.py` are deleted.

### Nice to have

- none

## Implementation

### Module: build.py

- **Location**: `skills/brief-portfolio/scripts/`
- **Responsibility**: Read its three inputs defensively and say what it skipped.
- **Exports**: `main()`, unchanged CLI

### Module: test_build_page.py

- **Location**: `skills/brief-portfolio/scripts/`
- **Responsibility**: Pin the three input failures.
- **Exports**: pytest cases

### Dependencies

- build.py: No dependencies (foundation)
- test_build_page.py: Depends on [build.py]

## Tasks

### Phase 0: Foundation

- [ ] Read `history.jsonl` in a loop that skips undecodable lines with a stderr WARN - Acceptance: delete the `xfail` marker on `test_a_torn_history_line_does_not_abort_the_build`; `uv run pytest skills/brief-portfolio/scripts/test_build_page.py -q` reports that test passing and 0 failing; the WARN text matches `history.jsonl line <N> skipped`.
- [ ] Wrap the `data.json` and `epics.json` loads in a `try` that exits with `f"{path}: {exc}"` - Acceptance: delete the `xfail` marker on `test_a_truncated_data_json_exits_with_a_message_naming_the_file`; add `test_an_invalid_epics_json_exits_with_a_message_naming_the_file` using `epics.json` = `{"summary": "x", "repos": {`; both pass, the exit code is non-zero, stderr contains the file name and no `Traceback`; `uv run pytest skills/brief-portfolio/scripts -q` reports 0 failing.

### Phase 1: Core

- none

## Success Criteria

- The two authored tests pass without an xfail marker and the new epics.json
  test passes.
- `rg -n "xfail" skills/brief-portfolio/scripts/test_build_page.py` no longer
  matches either name above.
- The report's three reproductions give a page (history) or a one-line named
  exit (data.json, epics.json).
