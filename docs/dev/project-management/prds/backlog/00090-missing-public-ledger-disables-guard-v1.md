---
design: skip
default_model: sonnet
model_tier_rationale: bounded ledger-loading fix with regression tests for both commands
---

# A missing public ledger disables glean's safety gate

Source: agoge report `dev/local/audit-results/agoge-2026-10-26.md`, finding 1,
accepted option A on 2026-10-26. Also covers finding 13 of the 2026-10-25 report.
The reports are local audit artifacts and are not shipped in the public repository.

## Problem

Glean treats a missing configured public ledger as empty. A typo or deleted file
therefore removes public never verdicts and lets check-staged report success for
a forbidden staged file. Target users are operators checking dotfiles before
committing to a public repository. A configuration error can expose private files.

## Solution

Require a public ledger to exist whenever the local configuration names one.
Both scan and check-staged must stop with a non-zero exit and a clear diagnostic
naming the missing path. Keep the existing first-run diagnostic for a missing
local ledger, and preserve configurations that omit an optional public ledger.

## Requirements

### Must have

- A configured public-ledger path that does not exist stops both commands.
- The diagnostic identifies the missing public ledger without a Python traceback.
- A valid public ledger continues to enforce its never verdicts.
- An omitted public-ledger setting retains its current behavior.
- A missing local ledger retains the existing no-config first-run guidance.
- Add regression coverage for scan and check-staged using isolated temporary homes.

### Nice to have

- None.

## Implementation

```text
skills/glean/scripts/
├── glean.py       # require an explicitly configured public ledger
└── test_glean.py  # regression and compatibility coverage
```

### Module: ledger loading

- **Location**: `skills/glean/scripts/glean.py`
- **Maps-to-capability**: enforce the configured public ledger before either command.
- **Responsibility**: distinguish an absent optional setting from a configured missing file.
- **Exports**: `load_json`, `load_ledgers`.

#### Feature: require a configured public ledger

- **Inputs**: the local ledger and its public-ledger configuration.
- **Outputs**: loaded entries or a non-zero exit naming the missing path.
- **Behavior**: fail before reporting scan results or a successful staged check
  when the configured public ledger is missing. Do not create a replacement ledger.

### Module: ledger regression tests

- **Location**: `skills/glean/scripts/test_glean.py`
- **Maps-to-capability**: regression coverage for the missing-ledger safety gate.
- **Responsibility**: exercise missing, present, and omitted public ledgers in isolation.
- **Exports**: none.

### Dependencies

- Ledger loading: no dependencies (foundation).
- Ledger regression tests: depend on ledger loading and existing temporary-home fixtures.
- Both command entry points use the shared ledger loader (integration).

## Tasks

### Phase 0: Foundation

- [ ] Add failing regression tests for both commands, then require configured
  public ledgers to exist. Cover a staged harmless file with a public never
  verdict, a valid ledger, a missing ledger, an omitted setting, and a missing
  local ledger. Assert a non-zero exit, a path-specific diagnostic without a
  traceback, and no successful staged-check result for the missing public ledger.
  Acceptance: `uv run pytest skills/glean/scripts/test_glean.py` passes after
  the change; the missing-public-ledger cases fail against the prior code.
  The strict-xfail test for this finding exists only on the unmerged branch
  `agoge/authored-tests-2026-10-26`; implement independently if absent. If present,
  convert that test to a normal regression when the fix lands, without merging
  unrelated branch changes.

Exit criteria: `uv run pytest`,
`uv run python3 skills/create-skill/scripts/validate_skill.py skills/glean`,
and `braid --check` pass.

## Success Criteria

- Scan and check-staged both refuse a missing configured public ledger.
- A present public ledger still blocks a staged file with a never verdict.
- Optional-ledger and first-run controls retain their previous behavior.

### Test Strategy

Carry the observed evidence verbatim from the accepted packet:

```text
Public ledger `{".foorc": never}`, `.foorc` staged. Correct path: `check-staged` -> `"ok": false, "hard":[{"path":".foorc","why":"ledger verdict never"}]`, exit 1. Path `pub.jsno` (missing): `{"ok": true, "hard": [], "soft": [], "staged": 1}`, exit 0. The local ledger gets a "no config" exit for the same fault.
```

The report uses shorthand above; construct a valid ledger with the existing
test helpers. Add equivalent missing-ledger coverage for scan. Run against a
temporary bare repository, never the operator's dotfiles repository.

### Risks

Fresh setups that configure the public-ledger path before creating the file now
stop. Broadly changing load_json could also alter local-ledger first-run behavior;
keep the stricter requirement specific to the configured public ledger.
