---
design: skip
default_model: sonnet
model_tier_rationale: bounded People-tab conditional copy with built-template smoke coverage
---

# Single-speaker meetings receive misleading airtime text

Source: agoge report `dev/local/audit-results/agoge-2026-10-25.md`, finding 20,
accepted option A on 2026-10-29. Reports are local audit artifacts and are not
shipped in the public repository. Evidence came from jsdom, not a real browser.

## Problem

The People tab describes two loudest voices even when the transcript identifies
one speaker. It also shows spread score 0 beside a legend describing 1 as one
person. Readers receive contradictory text for a valid single-speaker transcript.

## Solution

Special-case the single-speaker display: describe one identified speaker using
the actual recorded word share, and show spread as not applicable for one speaker.
Keep the airtime table and multi-speaker behavior. Rebuild the single-file template
and verify the rendered result through the existing smoke harness.

## Requirements

### Must have

- A single-speaker People tab does not refer to two loudest voices.
- Show the actual word share rather than inventing a percentage for incomplete data.
- Present spread as not applicable for one speaker instead of a contradictory
  numeric score/legend. Preserve the underlying multi-speaker metric calculation.
- Retain the single speaker's airtime table and other useful details.
- Preserve multi-speaker summary and score behavior.
- Rebuild the bundled template from source rather than hand-editing generated HTML.
- Add a smoke check of the built artifact with a valid single-speaker payload.

### Nice to have

- None.

## Implementation

```text
skills/debrief-meeting/
├── app/src/components/People.svelte  # conditional single-speaker summary
├── app/smoke.test.js                 # render the built People tab for one/two speakers
└── assets/template.html              # rebuilt single-file app artifact
```

### Module: People tab

- **Location**: `skills/debrief-meeting/app/src/components/People.svelte`
- **Maps-to-capability**: describe single-speaker airtime without false comparison.
- **Responsibility**: select accurate summary and spread presentation for one speaker.
- **Exports**: existing People component.

#### Feature: explain one identified speaker

- **Inputs**: transcript speaker roster and recorded word shares.
- **Outputs**: accurate single-speaker wording and a not-applicable spread label.
- **Behavior**: condition only the summary presentation; retain the table and
  multi-speaker calculation/output.

### Module: built-page smoke check

- **Location**: `skills/debrief-meeting/app/smoke.test.js`
- **Maps-to-capability**: prove the distributed page displays the corrected summary.
- **Responsibility**: exercise a consistent single-speaker payload and multi-speaker control.
- **Exports**: none.

### Module: distributed template

- **Location**: `skills/debrief-meeting/assets/template.html`
- **Maps-to-capability**: ship the corrected component in generated debriefs.
- **Responsibility**: contain the rebuilt app using the existing build pipeline.
- **Exports**: existing single-file template payload interface.

### Dependencies

- People tab: existing speaker data and metric helpers (foundation).
- Template: depends on the source component and current pinned build toolchain.
- Smoke check: exercises the rebuilt template, not source-string assertions.

## Tasks

### Phase 0: Foundation

- [ ] Add the single-speaker display branch and a built-page smoke case with
  consistent roster, turns, and related payload data. Assert one-speaker wording,
  the actual share, a not-applicable spread presentation, and retained table data.
  Retain the two-speaker summary/score control. Rebuild through the existing app
  command and verify the generated template rather than editing it manually.
  Acceptance: `npm --prefix skills/debrief-meeting/app run build` and
  `npm --prefix skills/debrief-meeting/app test` pass; the single-speaker smoke
  assertion fails against the prior built template. No dependency update is needed.

Exit criteria: `uv run pytest`,
`uv run python3 skills/create-skill/scripts/validate_skill.py skills/debrief-meeting`,
and `braid --check` pass, alongside the build/smoke acceptance above.

## Success Criteria

- Single-speaker summaries make no two-person claim or contradictory spread claim.
- Multi-speaker summaries and single-speaker details remain available.
- The source and distributed template agree.

### Test Strategy

Carry the observed evidence verbatim from the accepted packet:

```text
Rendered text: `Airtime The two loudest voices took 100% of the words. Spread score 0 (0 = even, 1 = one person).`
```

The smoke harness is jsdom. Report that validation boundary accurately rather
than calling it a real-browser measurement.

### Risks

The generated template produces bundle diff noise for a small cosmetic change.
Keep the change to presentation and preserve metric math and existing data behavior.
