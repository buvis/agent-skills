---
default_model: sonnet
model_tier_rationale: one-line guard with an exact message, the authored xfail flips green
design: skip
---

# A missing gita registry gives a traceback, not the exit message SKILL.md promises

## Problem

SKILL.md says that without `~/.config/gita/repos.csv` the collector "exits with
'no repos found in gita registry'", but `main()` in
`skills/brief-portfolio/scripts/collect.py` (about line 494) opens the file
unguarded, so the documented case is a `FileNotFoundError` traceback. A
first-time user on a new machine sees a traceback where the doc promised a
sentence. Source: agoge run `dev/local/audit-results/agoge-2026-09-05.md`,
finding 11 (MEDIUM, release lane, verified); decision 2026-09-05: one-line
guard. Strict xfail landed on master in a550262.

```
HOME pointed at an empty scratch dir: exit 1 with FileNotFoundError: [Errno 2]
No such file or directory: '<S>/home/.config/gita/repos.csv' at line 494.
Control, a registry naming no git repo: exit 1 with exactly
no repos found in gita registry.
```

## Solution

Before opening the registry in `main()`:
`if not GITA_CSV.is_file(): sys.exit(f"no repos found in gita registry: {GITA_CSV} is missing")`.

## Requirements

### Must have

- A missing registry exits 1 with the one-line message above and no traceback.
- The existing empty-registry exit is unchanged.
- The xfail marker on
  `test_missing_registry_file_exits_with_the_documented_message` is deleted.

### Nice to have

- none

## Implementation

### Module: collect.py

- **Location**: `skills/brief-portfolio/scripts/`
- **Responsibility**: Say what is missing instead of tracing.
- **Exports**: `main()`, unchanged CLI

### Module: test_collect_pipeline.py

- **Location**: `skills/brief-portfolio/scripts/`
- **Responsibility**: Pin the message.
- **Exports**: pytest cases

### Dependencies

- collect.py: No dependencies (foundation)
- test_collect_pipeline.py: Depends on [collect.py]

## Tasks

### Phase 0: Foundation

- [ ] Add the `is_file()` guard in `main()` - Acceptance: delete the `xfail` marker on `test_missing_registry_file_exits_with_the_documented_message`; `uv run pytest skills/brief-portfolio/scripts -q` reports that test passing and 0 failing.

### Phase 1: Core

- none

## Success Criteria

- The authored test passes without its marker; the empty-registry test passes
  unchanged.
- The report's reproduction prints the documented sentence and no `Traceback`.
