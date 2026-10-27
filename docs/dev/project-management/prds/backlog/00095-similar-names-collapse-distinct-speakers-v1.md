---
design: skip
default_model: sonnet
model_tier_rationale: speaker identity rule change with similar-name regressions and pinned initial-name compatibility
---

# Similar names collapse distinct meeting speakers

Source: agoge report `dev/local/audit-results/agoge-2026-10-26.md`, finding 6,
accepted option A on 2026-10-26. The report is a local audit artifact and is not
shipped in the public repository. The older report's finding 44 concerns
performance and requires its own decision.

## Problem

The debrief parser combines speaker labels using a fuzzy similarity ratio and
unrestricted token-prefix matches. Different people such as Dana and Dane Whitfield,
or Speaker 1 and Speaker 10, silently become one speaker. Meeting participants
receive incorrect attribution and speaking statistics whenever distinct names
happen to look similar.

## Solution

Merge labels by normalized identity: case, punctuation, and name-order differences.
Remove fuzzy spelling similarity and unrestricted token-prefix merging. Preserve
existing pinned merges, including the tested initial/full-name form, without
allowing that compatibility rule to merge distinct full names or numbered labels.

## Requirements

### Must have

- Keep Speaker 1 and Speaker 10 distinct.
- Keep Dana Whitfield and Dane Whitfield distinct.
- Keep Alexander Smith and Alexandra Smith distinct.
- Continue merging case, punctuation, and comma-swapped variants of the same name.
- Preserve existing role-suffix normalization and pinned abbreviation compatibility,
  including A. Rivera with Alex Rivera.
- Do not repair misspelled full names by fuzzy similarity.
- Keep distinct-speaker turn attribution and derived statistics correct.

### Nice to have

- None.

## Implementation

```text
skills/debrief-meeting/scripts/
├── parse.py       # conservative speaker identity and pinned-merge compatibility
└── test_parse.py  # false-merge regressions and existing identity controls
```

### Module: speaker identity

- **Location**: `skills/debrief-meeting/scripts/parse.py`
- **Maps-to-capability**: distinguish people while joining equivalent speaker labels.
- **Responsibility**: replace fuzzy and unrestricted prefix matches with identity rules.
- **Exports**: `canonicalize`, `name_key`, `display_form`.

#### Feature: merge only equivalent labels and pinned forms

- **Inputs**: observed speaker labels and their occurrence counts.
- **Outputs**: the existing raw-to-display mapping and merge records.
- **Behavior**: normalize case, punctuation, and name order; preserve pinned initial
  forms while leaving distinct full names, typos, and numbered labels separate.

### Module: speaker identity tests

- **Location**: `skills/debrief-meeting/scripts/test_parse.py`
- **Maps-to-capability**: protect attribution against similar-name false merges.
- **Responsibility**: cover the three reported pairs and legitimate existing merges.
- **Exports**: none.

### Dependencies

- Speaker identity: existing display normalization and mapping output (foundation).
- Speaker identity tests: depend on the identity rules.
- Turn merging and speaking statistics consume the preserved mapping (integration).

## Tasks

### Phase 0: Foundation

- [ ] Add failing regressions for the three distinct-name pairs, then replace
  fuzzy similarity and unrestricted prefix matching with conservative identity
  checks. Preserve the existing tested comma-swapped, role-suffixed, and initial
  forms. Check both mapping results and a parsed transcript where different
  speakers must retain separate turns. Update merge-record assertions only where
  the new rule changes how a legitimate merge is recorded.
  Acceptance: `uv run pytest skills/debrief-meeting/scripts/test_parse.py` passes;
  the distinct-name pair regressions fail against the prior code, while the pinned
  initial-name and role-suffix controls continue passing.
  The unmerged branch `agoge/authored-tests-2026-10-26` holds a parametrized
  strict-xfail regression for this finding. Implement independently if absent;
  if present, convert it to a normal regression without unrelated branch changes.

Exit criteria: `uv run pytest`,
`uv run python3 skills/create-skill/scripts/validate_skill.py skills/debrief-meeting`,
and `braid --check` pass.

## Success Criteria

- All three reported distinct-name pairs remain distinct.
- Equivalent spellings and existing pinned initial forms still merge.
- Distinct speakers retain their speech and individual statistics.

### Test Strategy

Carry the observed evidence verbatim from the accepted packet:

```text
`parse.canonicalize(names*3)`: `['Speaker 1','Speaker 10']` -> `['Speaker 1']`; `['Dana Whitfield','Dane Whitfield']` -> `['Dana Whitfield']`; `['Alexander Smith','Alexandra Smith']` -> `['Alexander Smith']`; `['Speaker 1','Speaker 2']` stays separate. A 10,000-cue fixture of `Speaker Number0..5` collapsed to 1 speaker, 1 turn.
```

### Risks

Transcription typos that previously merged remain separate speakers. The existing
abbreviation test uses a prefix-based match today; preserve its intended identity
without preserving generic prefix behavior. PRD 00094 touches the same parser and
tests for guest-header recognition; retain that fix and its coverage.
