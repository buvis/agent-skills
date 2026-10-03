---
default_model: opus
rework_cap: 5
---

# The CI shell-suite entry miscounts the skills that ship one

Source: agoge run `dev/local/audit-results/agoge-2026-08-31.md`, finding 38
(LOW, release lane, verified). Decision 2026-09-02: accepted — fix the count
and delete the unverified test-total figure.

## Overview

### Problem Statement

`CHANGELOG.md:264-267` and `.github/workflows/ci.yml:34` both say "five
skills ship a bash suite". Four do; they ship five files (`use-qwen` carries
two). The companion "172 tests between them" figure is untested — warden
refuses the suites locally, so they execute only in CI, and static counts
neither confirm nor refute it. Harmless in itself; it matters as a signal the
numbers were never checked.

### Target Users

Anyone reading the changelog or workflow to understand test coverage.

### Success Metrics

- Both places read "four skills ship five suites" (or equivalent wording).
- The "172 tests" figure is gone from both.

## Functional Decomposition

Two text edits: the count corrected, the unverifiable figure removed.

## Structural Decomposition

- `CHANGELOG.md` (~264-267)
- `.github/workflows/ci.yml` (~34)

## Implementation Phases

### Phase 0: The edits

Two files. (If PRD 00029's changelog roll-up lands first, apply the fix
inside the `0.1.0` section it moved to.)

## Test Strategy

Evidence from the report, verbatim:

```
ls skills/*/scripts/test_*.sh returns five files across four skills —
use-qwen ships two (test_eval_automation.sh and test_qwen_run.sh).
rg --files -g '*test*.sh' over the whole repo returns the same five. The
"172 tests between them" figure is untested: warden refuses the suites on
this host, and static PASS/FAIL call-site counts (301 sites) neither confirm
nor refute it.
```

## Risks

The figure is probably right, and deleting information because nobody checked
it is blunt — accepted; the pinned-total CI option was declined for its
maintenance friction.
