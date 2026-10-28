---
design: skip
catchup: skip
default_model: sonnet
model_tier_rationale: single README command correction with literal and rendered-text verification
---

# The README's Windows command contains an extra backslash

Source: agoge report `dev/local/audit-results/agoge-2026-10-26.md`, finding 29,
accepted option A on 2026-10-28. The report is a local audit artifact and is not
shipped in the public repository. Evidence remains unverified on Windows.

## Problem

The README's inline Windows command contains two literal backslashes. A reader
can copy that spelling rather than the intended single-separator path. The audit
identified a documentation ambiguity, without testing execution on Windows.

## Solution

Write the inline command as `py bin\braid.py`, with one literal backslash.
Preserve the surrounding installation and NTFS-junction explanation.

## Requirements

### Must have

- Use the accepted single-backslash command in README inline code.
- Preserve surrounding content and runtime behavior.
- Re-check the current text before editing and skip an already-corrected command.
- Do not claim Windows execution was verified by a documentation-only check.

### Nice to have

- None.

## Implementation

```text
README.md  # single-backslash Windows invocation
```

### Module: installation instructions

- **Location**: `README.md`
- **Maps-to-capability**: give Windows readers the intended command spelling.
- **Responsibility**: correct the inline path separator.
- **Exports**: none.

#### Feature: show the intended Windows command

- **Inputs**: current inline command and accepted single-separator spelling.
- **Outputs**: the corrected README command.
- **Behavior**: change only the surplus backslash, preserving the executable and path.

### Dependencies

- Installation instructions: no implementation changes or new dependencies.

## Tasks

### Phase 0: Foundation

- [ ] Premise: the Windows inline command still contains two literal backslashes.
  Re-check source and inline-code rendering at execution time. Remove the extra
  backslash if present, or skip an already-corrected passage and report why.
  Acceptance: the README source and displayed inline command contain exactly
  one backslash between bin and braid.py; the diff changes only that command.

Exit criteria: `uv run pytest` and `braid --check` pass. No new tests or
Windows-runtime assertion are needed for this documentation spelling correction.

## Success Criteria

- The displayed command is `py bin\braid.py` with one separator.
- The finding's Windows execution status remains unverified.

### Test Strategy

Carry the report's evidence verbatim:

```text
The text quoted above.
```

The packet's quoted source was `py bin\\braid.py`, containing two backslashes.
Inspect literal bytes and inline-code rendering for the correction; that does
not establish execution behavior on Windows.

### Risks

The original command was not run on Windows. Keep the change to the accepted
spelling correction; do not broaden it into platform behavior changes.
