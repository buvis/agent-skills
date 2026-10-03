---
default_model: sonnet
rework_cap: 5
catchup: skip
design: skip
---

# A debrief built without extraction reports "0 live risks" beside tiles that say "unknown"

## Problem

When `extract.json` has not been produced, the debrief marks decisions, actions
and open questions as `—` but still prints a hard `0` for live risks. In
`skills/debrief-meeting/app/src/components/Brief.svelte` the tile array runs
lines 13-20, and line 19 (`[unresolvedRisks.length, 'live risks']`) is the only
one of the four extraction-derived tiles missing the `extractRan` guard its
neighbours on lines 16-18 carry. The explanatory note on line 30 lists only the
other three. A reader is told there are zero live risks in a meeting whose risks
were never extracted, and the false number is the most confident-looking one on
the row. It hits every debrief built by the `parse.py` then `build.py` path
without the model extraction step. Source: agoge run
dev/local/audit-results/agoge-2026-08-31.md, finding 11 (MEDIUM, journey lane);
decision 2026-09-02: accepted, add the missing guard and name risks in the note.

```
Real pipeline (parse.py -> build.py with no extract), driven in jsdom,
reproduced twice on two builds: TILE — | decisions, TILE — | actions,
TILE — | open questions, TILE 0 | live risks, and the note reads "The
extraction step hasn't run — decisions, actions, and open questions above
are not counted." Control with an extract renders TILE 1 | live risks.
```

## Solution

Make the fourth tile read like its three neighbours:
`[extractRan ? unresolvedRisks.length : na, 'live risks']`, and add live risks
to the not-run note on line 30. Rebuild `assets/template.html` from `app/`,
because the jsdom suite and the shipped artifact both read the built template,
not the sources. Extend the existing not-run smoke test to assert the fourth
tile and the new note text, and add a test pinning the with-extract count so
the guard cannot be "fixed" by hard-coding the placeholder.

## Requirements

### Must have
- Without an extract, the live-risks tile renders `—`, the same placeholder the
  other three uncounted tiles use.
- With an extract, the tile still renders the unresolved-risk count
  (`extract.risks` entries where `addressed` is falsy).
- The not-run note names live risks. Exact text:
  `The extraction step hasn't run — decisions, actions, open questions, and live risks above are not counted.`
- `skills/debrief-meeting/assets/template.html` is rebuilt from `app/` so the
  shipped artifact carries the fix, and still holds exactly one
  `__MEETING_PAYLOAD__` marker.
- The smoke suite asserts all four extraction-derived tiles, not three.

### Nice to have
- none

## Implementation

### Module: debrief Brief tab
- **Location**: `skills/debrief-meeting/app/src/components/`
- **Responsibility**: the "At a glance" tile row and its not-run note
- **Exports**: `Brief.svelte`

### Module: debrief built template
- **Location**: `skills/debrief-meeting/assets/`
- **Responsibility**: the pre-built single-file app `build.py` injects into
- **Exports**: `template.html`, a build artifact with no exports of its own

### Module: debrief smoke suite
- **Location**: `skills/debrief-meeting/app/`
- **Responsibility**: mount the built template in jsdom and assert what a reader sees
- **Exports**: `brief tiles show em dashes and a not-run note when extraction did not run` (extended), `brief live-risks tile shows the unresolved count when extraction ran` (new)

### Dependencies
- debrief Brief tab: No dependencies (foundation)
- debrief built template: Depends on [debrief Brief tab]
- debrief smoke suite: Depends on [debrief built template]

## Tasks

### Phase 0: Foundation

- [ ] In `skills/debrief-meeting/app/src/components/Brief.svelte`, change line 19 to `[extractRan ? unresolvedRisks.length : na, 'live risks'],` and change the note on line 30 to read `The extraction step hasn't run — decisions, actions, open questions, and live risks above are not counted.` - Acceptance: `rg -n "extractRan \? unresolvedRisks" skills/debrief-meeting/app/src/components/Brief.svelte` prints exactly one line, and `rg -n "open questions, and live risks above are not counted" skills/debrief-meeting/app/src/components/Brief.svelte` prints exactly one line.
- [ ] Rebuild the shipped template: `npm --prefix skills/debrief-meeting/app run build`, then copy `skills/debrief-meeting/app/dist/index.html` over `skills/debrief-meeting/assets/template.html` - Acceptance: `rg --count-matches "open questions, and live risks above are not counted" skills/debrief-meeting/assets/template.html` prints `1`, and `rg --count-matches "__MEETING_PAYLOAD__" skills/debrief-meeting/assets/template.html` prints `1`.
- [ ] In `skills/debrief-meeting/app/smoke.test.js`, extend the test `brief tiles show em dashes and a not-run note when extraction did not run` (lines 205-218) with `assert.ok(tiles.includes('—liverisks'), ...)` and update its exact-note assertion to the new sentence - Acceptance: `rg -n "—liverisks" skills/debrief-meeting/app/smoke.test.js` prints exactly one line, `rg -n "decisions, and open questions above are not counted" skills/debrief-meeting/app/smoke.test.js` prints no match, and `npm --prefix skills/debrief-meeting/app test` exits 0 with zero failures.
- [ ] In the same file add `brief live-risks tile shows the unresolved count when extraction ran`: render the default `PAYLOAD` (its `extract.risks` holds one entry with `addressed: false`) and assert the tile row contains `1liverisks` - Acceptance: `npm --prefix skills/debrief-meeting/app test` exits 0 with zero failures, names `brief live-risks tile shows the unresolved count when extraction ran` as passing, and the new named regression is collected alongside every pre-existing test (47 was the review snapshot, not a fixed total).

### Phase 1: Core

No additional work; the Phase 0 tasks deliver this capability and its regression coverage.

## Success Criteria

- A payload with `extract_ran: false` and `extract: {}` renders four tiles
  reading `—decisions`, `—actions`, `—openquestions`, `—liverisks` once
  whitespace is stripped.
- The same payload renders exactly one `main .muted` paragraph whose text is
  `The extraction step hasn't run — decisions, actions, open questions, and live risks above are not counted.`
- A payload with `extract_ran: true` and one unaddressed risk still renders
  `1liverisks`.
- `npm --prefix skills/debrief-meeting/app test` exits 0 with zero failures and the new named regression passing.
