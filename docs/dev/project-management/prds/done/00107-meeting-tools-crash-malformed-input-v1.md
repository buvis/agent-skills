---
design: skip
default_model: sonnet
model_tier_rationale: bounded format-error handling and consumed-field validation with malformed-input CLI regressions
---

# Meeting tools crash on corrupt or incorrectly structured input

Source: agoge report `dev/local/audit-results/agoge-2026-10-26.md`, finding 18,
accepted option A on 2026-10-27. Also covers findings 12 and 19 of the 2026-10-25
report. The reports are local audit artifacts and are not shipped in the public
repository.

## Problem

The meeting parser and HTML builder handle some input errors cleanly, but corrupt
Word archives and valid JSON with invalid structure raise Python tracebacks.
Operators processing transcripts or model-generated extraction data receive
confusing crashes instead of a clear explanation of which input needs correction.

## Solution

Handle specific Word archive errors at the source-reading boundary and validate
JSON structure after decoding, before fields are consumed. Exit non-zero with a
clear one-line diagnostic naming the offending input. Use the existing skill
schema and actual consumer fields as the validation contract, retaining valid
transcript-only and extraction-assisted builds.

## Requirements

### Must have

- A corrupt DOCX archive or missing word/document.xml yields a controlled input
  error rather than BadZipFile or KeyError escaping to the CLI.
- Invalid transcript JSON syntax and non-object or missing-required-field
  transcript structures are rejected before building.
- Invalid extraction roots and wrong-type corrections are rejected before use;
  validate correction entries and other fields consumed directly by the builder.
- Report a one-line diagnostic naming the file and input problem, with exit 1
  and no traceback for the reported malformed cases.
- Do not write output artifacts after rejecting input.
- Preserve optional missing extraction, unknown-key warnings, valid corrections,
  and valid text/VTT/SRT/Word parsing.
- Avoid catch-all exception handling that masks unrelated programming errors.

### Nice to have

- None.

## Implementation

```text
skills/debrief-meeting/scripts/
├── parse.py                # specific DOCX input error handling
├── build.py                # decoded transcript and extraction shape checks
├── test_parse.py           # corrupt and incomplete DOCX regressions
└── test_debrief_build.py   # malformed JSON structure and clean-build controls
```

### Module: transcript source reader

- **Location**: `skills/debrief-meeting/scripts/parse.py`
- **Maps-to-capability**: explain corrupt or incomplete Word input cleanly.
- **Responsibility**: handle archive-format and required-member errors locally.
- **Exports**: `read_source`, `main`.

#### Feature: refuse invalid Word archives

- **Inputs**: a DOCX path and its required document member.
- **Outputs**: decoded source or a controlled CLI diagnostic.
- **Behavior**: catch the specific archive errors at their read boundary, preserving
  other parser behavior.

### Module: build input validation

- **Location**: `skills/debrief-meeting/scripts/build.py`
- **Maps-to-capability**: reject invalid transcript/extraction structures before use.
- **Responsibility**: validate required consumed fields against the documented schema.
- **Exports**: `load_extract`, `apply_corrections`, `main`.

#### Feature: validate decoded build input

- **Inputs**: decoded transcript and optional extraction JSON.
- **Outputs**: valid payloads or a clear file-specific refusal.
- **Behavior**: check object/container and consumed-field types before corrections
  or rendering; preserve optional-field defaults and unknown-key warnings.

### Module: malformed-input regressions

- **Locations**: `skills/debrief-meeting/scripts/test_parse.py`,
  `skills/debrief-meeting/scripts/test_debrief_build.py`.
- **Maps-to-capability**: keep expected input failures out of Python tracebacks.
- **Responsibility**: exercise CLI refusals and valid-input controls in temporary directories.
- **Exports**: none.

### Dependencies

- Source reader and build validation: existing format readers and documented schemas (foundation).
- Malformed-input regressions: depend on both input boundaries.
- Corrections and HTML rendering consume validated payloads (integration).

## Tasks

### Phase 0: Foundation

- [ ] Add failing cases for a text file named DOCX, a ZIP missing document.xml,
  truncated transcript JSON, an empty transcript object, list/null extraction
  roots, and a string corrections value. Add the specific archive error handling
  and decoded-data shape checks. Test valid correction entries alongside malformed
  entries, and retain successful transcript-only, extraction, and Word controls.
  Assert exit 1, a one-line file-specific diagnostic, no traceback, and no output
  creation for each malformed input. Validate against the schema in the skill
  instructions rather than inventing additional mandatory extraction fields.
  Acceptance: `uv run pytest skills/debrief-meeting/scripts/test_parse.py skills/debrief-meeting/scripts/test_debrief_build.py`
  passes; the reported malformed-input CLI cases fail against the prior code.

Exit criteria: `uv run pytest`,
`uv run python3 skills/create-skill/scripts/validate_skill.py skills/debrief-meeting`,
and `braid --check` pass.

## Success Criteria

- The reported corrupt DOCX and malformed JSON cases produce clear refusals.
- No rejected input produces output artifacts or an uncaught traceback.
- Existing valid transcript and extraction workflows continue working.

### Test Strategy

Carry the observed evidence verbatim from the accepted packet:

```text
`parse.py <S>/bad.docx` (text named .docx) -> `zipfile.BadZipFile: File is not a zip file`, exit 1; a zip without `word/document.xml` -> `KeyError: "There is no item named 'word/document.xml' in the archive"`. `build.py <dir>`: truncated `transcript.json` -> `JSONDecodeError`; `{}` -> KeyError 'turns'; `extract.json` `[1,2]` -> AttributeError; `null` -> TypeError; `{"corrections":"oops"}` -> AttributeError. A truncated `extract.json` is handled ("is not valid JSON", exit 1). Nothing is written on failure.
```

### Risks

Hand-written validation can drift from the schema or over-reject valid optional
data. Keep checks tied to documented and consumed fields. PRDs 00094 and 00095
also change parse.py and its tests; retain their speaker recognition and identity
behavior while adding these independent input checks.
