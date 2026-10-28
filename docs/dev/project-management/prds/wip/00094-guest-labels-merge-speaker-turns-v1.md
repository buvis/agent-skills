---
design: skip
default_model: sonnet
model_tier_rationale: bounded speaker-header normalization with text and DOCX regression coverage
---

# Guest speaker labels merge into another person's turn

Source: agoge report `dev/local/audit-results/agoge-2026-10-26.md`, finding 5,
accepted option A on 2026-10-26. The report is a local audit artifact and is not
shipped in the public repository.

## Problem

The debrief parser rejects speaker labels ending in parenthetical role text,
such as Sam Okafor (Guest), before canonicalization can remove that suffix.
In text and Word transcripts the rejected header and its speech join the previous
speaker's turn. Meeting participants receive incorrect speech and action-item
attribution, sometimes with only a generic single-speaker warning.

## Solution

Strip trailing parenthetical text before speaker-name plausibility checks.
Preserve the existing canonicalization of role suffixes and the distinction
between speaker headers and ordinary speech. Cover the Teams and bracketed
timestamp layouts through the parsing path, rather than testing canonicalization alone.

## Requirements

### Must have

- Recognize trailing parenthetical speaker labels in Teams-style text headers.
- Recognize the same labels in bracketed timestamp headers and Word text input.
- Attribute each header's following speech to the corresponding normalized name.
- Handle arbitrary trailing role text rather than only an explicit Guest suffix.
- Preserve ordinary speech containing parentheses or colons as speech.
- Keep existing VTT voice-tag behavior and role-suffix canonicalization working.

### Nice to have

- None.

## Implementation

```text
skills/debrief-meeting/scripts/
├── parse.py       # normalize role suffixes before speaker-name plausibility checks
└── test_parse.py  # Teams, bracketed timestamp, and Word-path regression coverage
```

### Module: speaker header recognition

- **Location**: `skills/debrief-meeting/scripts/parse.py`
- **Maps-to-capability**: recognize role-suffixed speaker headers before assigning turns.
- **Responsibility**: remove trailing parenthetical text for plausibility validation.
- **Exports**: `_plausible_name`, `parse_cues`, `canonicalize`.

#### Feature: accept role-suffixed speaker headers

- **Inputs**: a candidate speaker name with optional trailing parenthetical text.
- **Outputs**: a valid speaker header when its remaining name passes existing checks.
- **Behavior**: strip the trailing suffix before plausibility validation, then use
  the existing name normalization when attributing the speaker's speech.

### Module: header regression tests

- **Location**: `skills/debrief-meeting/scripts/test_parse.py`
- **Maps-to-capability**: prevent guest speech from joining the prior speaker's turn.
- **Responsibility**: test parsing and attribution across affected layouts.
- **Exports**: none.

### Dependencies

- Speaker header recognition: existing parsing and role canonicalization (foundation).
- Header regression tests: depend on speaker header recognition.
- Text and Word inputs share the plain-text parsing path (integration).

## Tasks

### Phase 0: Foundation

- [ ] Add failing regression coverage for a Teams header containing Sam Okafor
  (Guest), then strip trailing parenthetical text before plausibility checks.
  Cover bracketed timestamps, the Word text-input path, another role suffix,
  and ordinary parenthetical speech. Assert distinct speakers, correct turn text,
  no swallowed speaker header, and no false single-speaker warning for the sample.
  Acceptance: `uv run pytest skills/debrief-meeting/scripts/test_parse.py` passes;
  the role-suffixed header regression fails against the prior code.
  The unmerged branch `agoge/authored-tests-2026-10-26` holds a strict-xfail
  regression for this finding. Implement independently if absent; if present,
  convert it to a normal regression without merging unrelated branch changes.

Exit criteria: `uv run pytest`,
`uv run python3 skills/create-skill/scripts/validate_skill.py skills/debrief-meeting`,
and `braid --check` pass.

## Success Criteria

- Role-suffixed headers produce their own speaker turns in affected input layouts.
- Speech and speaker labels stay correctly attributed in the Teams reproduction.
- Existing voice-tag, plain-header, and ordinary-speech parsing remain correct.

### Test Strategy

Carry the observed evidence verbatim from the accepted packet:

```text
Teams-layout text with `Sam Okafor (Guest)   1:05` -> "2 speakers, 2 turns, 20 words"; Alex's turn text was `Works for me, I have a hard stop. Sam Okafor (Guest)   1:05 Then Postgres.` A `[00:00:12] Sam Okafor (Guest): Then Postgres.` file gave "WARN: only one speaker detected". Cause: `_plausible_name` needs every token to start uppercase; `(Guest)` starts with `(`. The VTT `<v ...>` path skips the check.
```

### Risks

Stripping trailing parenthetical text can remove a legitimate part of a person's
name. Keep stripping confined to candidate speaker labels; do not change transcript
speech. Finding 6 separately concerns false merges between similar names and is
outside this PRD unless the user accepts that finding independently.
