---
design: skip
default_model: sonnet
model_tier_rationale: Shared matcher output correction with synthetic-secret regression tests.
---

# Prescreen labels expose a secret character

Source: `dev/local/audit-results/agoge-2026-10-25.md`, finding 45, audit dated 2026-10-25. User accepted option A on 2026-10-29.

## Problem

Glean constructs hard-secret labels from the first four characters of the match. For an sk- credential, the fourth character belongs to the secret. Scan and check-staged therefore include secret-derived content in diagnostic labels. The audit used test data, not a known live credential.

## Solution

Give each hard-secret alternative a named group and fixed category label. Emit only that constant label, never a substring of the matched credential. Keep the HARD: prefix used by safety consumers.

## Requirements

### Must have

- Every hard-secret alternative maps to a fixed descriptive label independent of its matched value.
- Both scan and check-staged use the shared corrected matcher.
- Preserve pattern coverage, case behavior, line numbers, blocking decisions, and the HARD: marker contract.
- Do not emit matched values or secret characters in labels, stdout, stderr, or serialized diagnostic fields.
- Test every current hard-secret alternative with synthetic data, including different sk- suffixes that must yield the same constant label.
- Record that changed labels may cause existing ledger entries to resurface once; do not add automatic ledger migration or weaken hard-secret blocking.

### Nice to have

None.

## Implementation

```text
skills/glean/scripts/glean.py
skills/glean/scripts/test_glean.py
```

### Module: Secret prescreen

- **Location**: `skills/glean/scripts/glean.py`
- **Maps-to-capability**: Secret-independent diagnostic labels.
- **Responsibility**: Use named hard-pattern alternatives and constant labels in the shared scanner.
- **Exports**: `scan_lines` and existing scan/check-staged CLI behavior.

#### Feature: Fixed hard-secret categories

- **Inputs**: Text that may match an existing hard-secret pattern.
- **Outputs**: Existing hit structures containing line numbers and constant HARD: labels.
- **Behavior**: Select the label from the matched pattern category without taking any part of the matched text. Preserve refusal behavior for both commands.

### Module: Prescreen regressions

- **Location**: `skills/glean/scripts/test_glean.py`
- **Maps-to-capability**: No secret-derived diagnostic content.
- **Responsibility**: Cover each hard pattern and both command output paths using dummy values.
- **Exports**: Existing pytest tests.

### Dependencies

- Existing regex matcher, isolated home/repository fixtures, and JSON CLI output. No new dependency.

## Tasks

### Phase 0: Constant labels

- [ ] Assign named categories and fixed labels to every current hard-secret alternative, retaining detection semantics and the HARD: prefix.
- [ ] Test category labels directly and capture scan/check-staged stdout and stderr. Vary synthetic secret suffixes and assert constant labels, absent dummy secret contents, correct locations, and unchanged gate decisions.
- [ ] Run `uv run pytest skills/glean/scripts/test_glean.py` and repository-required checks before committing.

Exit criteria: Both commands identify hard-secret categories without deriving diagnostic labels from matched values.

## Success Criteria

- Changing a dummy secret value never changes its category label.
- Hard-secret matches remain blocked and existing scanner coverage passes.

### Test Strategy

Original confirmed evidence, preserved verbatim:

```text
`scan` and `check-staged` both printed `"keyword": "HARD:sk-<first char>"`. The ghp_, PEM and api_key values did not leak.
```

Use only synthetic credentials. Cover all current alternatives to avoid replacing the sk- leak with a similar issue in another pattern. Assert entire category labels independently rather than only checking the HARD: prefix. Capture both output streams and serialized diagnostic fields.

### Risks

Ledger keywords change, so old entries can resurface once. Named-group changes must preserve regex flags and matching behavior. This task does not establish exposure of any real credential.
