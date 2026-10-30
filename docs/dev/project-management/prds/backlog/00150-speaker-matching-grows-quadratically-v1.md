---
design: run
default_model: sonnet
model_tier_rationale: Candidate indexing must preserve conservative speaker identity and deterministic merge behavior.
---

# Speaker matching grows quadratically

Source: `dev/local/audit-results/agoge-2026-10-25.md`, finding 44, audit dated 2026-10-25. User accepted option A on 2026-10-29.

## Problem

The audit measured quadratic fuzzy comparisons across distinct speaker labels, reaching 16.9 seconds for 2,000 labels. This affects unusual transcripts with many distinct labels. Since that audit, PRD 00095 removed fuzzy matching for correctness; the current parser still scans existing groups for initial/prefix compatibility. The historical timings do not measure this revised implementation.

## Solution

Keep exact-key lookup first and index candidates for the remaining permitted initial/prefix identity rule. Preserve the completed speaker-identity fixes. The accepted approximate 200-group cutoff applies only to any residual fuzzy fallback, which must remain absent under PRD 00095. Do not introduce fuzzy matching merely to cap it.

## Requirements

### Must have

- Avoid comparing every distinct full speaker label against every existing group when there are no plausible abbreviation candidates.
- Preserve exact normalized identity, case/punctuation/name-order equivalence, role normalization, and pinned initial/full-name compatibility.
- Preserve distinct full names, numbered speakers, deterministic group selection, merge records, and attribution fixed by PRDs 00094 and 00095.
- Use an exact-key and prefix/initial candidate index before compatibility comparisons.
- Keep fuzzy spelling matching disabled. If reconciling an older implementation containing such a fallback, remove it under PRD 00095 rather than restoring it below a cutoff.
- Test comparison-count bounds with thousands of distinct labels and legitimate abbreviation controls. Do not rely on fragile wall-clock thresholds.

### Nice to have

None.

## Implementation

```text
skills/debrief-meeting/scripts/parse.py
skills/debrief-meeting/scripts/test_parse.py
```

### Module: Speaker canonicalization

- **Location**: `skills/debrief-meeting/scripts/parse.py`
- **Maps-to-capability**: Bounded candidate matching without false speaker merges.
- **Responsibility**: Index candidates for existing conservative identity rules and preserve deterministic mappings.
- **Exports**: `canonicalize`, `name_key`, `_prefix_match`.

#### Feature: Indexed speaker candidates

- **Inputs**: Speaker labels and occurrence counts.
- **Outputs**: Existing canonical-name mapping and merge records.
- **Behavior**: Use exact identity first, then only plausible initial/prefix candidates. Preserve legitimate abbreviations and stable selection when several candidates are compatible. Document bounds and any unavoidable ambiguous-candidate behavior during design.

### Module: Matching regressions

- **Location**: `skills/debrief-meeting/scripts/test_parse.py`
- **Maps-to-capability**: Comparison bounds and retained attribution.
- **Responsibility**: Count compatibility checks on large deterministic inputs and retain existing correctness controls.
- **Exports**: Existing pytest tests.

### Dependencies

- PRDs 00094 and 00095 provide completed speaker-label and identity behavior. Retain their tests and semantics; this PRD addresses the separate performance decision.

## Tasks

### Phase 0: Candidate indexing

- [ ] Design candidate keys from the current allowed identity rule and specify deterministic candidate ordering. Preserve abbreviation behavior without a generic fuzzy fallback.
- [ ] Replace the remaining full-group candidate scan with indexed selection.
- [ ] Add comparison-count regressions for 100, 1,000, and 2,000 distinct full labels; specify a defensible bounded count in the design. Include repeated cues, exact aliases, initial/full-name variants, and ambiguous candidates. Preserve current distinct-name regressions.
- [ ] Run `uv run pytest skills/debrief-meeting/scripts` and repository-required checks before committing.

Exit criteria: Large distinct-label inputs avoid all-pairs candidate comparisons and existing identity/attribution controls pass.

## Success Criteria

- Distinct full-label inputs no longer trigger quadratic compatibility comparisons.
- Legitimate aliases merge and distinct speakers remain separate.

### Test Strategy

Original confirmed evidence, preserved verbatim:

```text
100 labels -> 4,950 calls, 0.064 s; 1,000 -> 499,500 calls, 4.1 s; 2,000 -> 1,999,000 calls, 16.9 s (each timed twice). With 4 speakers, 10k cues give 6 calls.
```

These are historical fuzzy-matcher measurements, not current benchmark claims. Test current compatibility-call counts using deterministic fixtures and preserve the completed similar-name and numbered-label controls. A test that only asserts zero SequenceMatcher calls would miss the remaining prefix scan.

### Risks

Indexing can change which compatible group wins or miss legitimate initials. Preserve current deterministic ordering and test ambiguous forms. The proposed historical cutoff was an estimate; do not let it weaken the already accepted no-fuzzy identity contract.
