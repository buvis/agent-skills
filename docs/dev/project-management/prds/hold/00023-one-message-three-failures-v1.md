---
default_model: opus
rework_cap: 5
---

# One fatal message for three different causes, and it names the cause that is usually wrong

## Problem

Three distinct failures - the placeholder was never substituted, the payload
parses but is structurally wrong, the payload was truncated mid-write - all
render one fixed message with an empty console, in both apps. `loadPayload()`
throws its own diagnosis away: `skills/brief-portfolio/app/src/lib/derive.js:3-11`
runs `if (!p.data?.repos) throw new Error('missing data.repos')` inside
`try { … } catch { return null }`, an unbound catch that never logs, and
`skills/debrief-meeting/app/src/lib/derive.js:8-17` has the same shape with
`missing transcript.turns`. The single `null` then reaches the inline
`{#if !payload}` block in each app (`brief-portfolio/app/src/App.svelte:70-74`,
`debrief-meeting/app/src/App.svelte:61-65`; there is no separate fallback
component), which tells the reader to run the build step. That instruction is
wrong in the two cases where the build already ran and would reproduce the same
file, at the exact moment something has already gone wrong. Source: agoge run
dev/local/audit-results/agoge-2026-08-31.md, finding 14 (MEDIUM, ux lane);
decision 2026-09-02: accepted, bind the error and render it under the fallback.

```
Three mounts, byte-identical page text and "logs": [] each time. The
distinguishing information exists and is thrown away:
if (!p.data?.repos) throw new Error('missing data.repos') sits inside
try { … } catch { return null }. The debrief app tells the user to "Re-run
scripts/build.py", a step that already ran and will reproduce the identical
file.
```

## Solution

Give `loadPayload()` a result shape instead of a bare `null`, in both apps:
`{ payload, error }` where `error` is `null`, `{ kind: 'not-built' }`, or
`{ kind: 'unreadable', reason }` carrying the bound `catch (e)` message. The not-built case is the
payload node still holding the build marker, detected by pattern
(`/^__[A-Z]+_PAYLOAD__$/` against the trimmed text) and never by the literal
marker string, because `build.py` substitutes every occurrence of that marker in
the template and a second copy inside the bundle would be overwritten with the
whole payload. Each `App.svelte` keeps its current wording for the not-built
case and renders the unreadable case with the bound reason. Both templates get
rebuilt, and each app's jsdom suite gains one test per cause.

## Requirements

### Must have
- Not-built case, exact text unchanged. brief-portfolio:
  `No data injected. Run build.py to produce this file from data.json.`
  debrief-meeting: `No payload was injected into this file. Re-run scripts/build.py.`
- Structurally-wrong and truncated cases render
  `The injected payload is present but unreadable: <reason>`, with `reason` being `missing data.repos` /
  `missing transcript.turns` for the structural case and the JSON parser's own
  message (for example `Unexpected end of JSON input`) for the truncated case.
- Neither unreadable message advises running or re-running the build step.
- The literal marker text `__PORTFOLIO_PAYLOAD__` / `__MEETING_PAYLOAD__` does
  not appear in any `app/src/` file, and each rebuilt template still holds
  exactly one occurrence of its marker.
- Each app's suite covers all three causes and asserts the three texts differ.

### Nice to have
- none

## Implementation

### Module: payload loaders
- **Location**: `skills/brief-portfolio/app/src/lib/`, `skills/debrief-meeting/app/src/lib/`
- **Responsibility**: read the injected JSON node and classify why it is unusable
- **Exports**: `loadPayload()` in each `derive.js`, new return shape `{ payload, error }`

### Module: app shells
- **Location**: `skills/brief-portfolio/app/src/`, `skills/debrief-meeting/app/src/`
- **Responsibility**: the inline `{#if !payload}` fallback each app renders when nothing mounts
- **Exports**: `App.svelte` in each app

### Module: built templates
- **Location**: `skills/brief-portfolio/assets/`, `skills/debrief-meeting/assets/`
- **Responsibility**: the pre-built single-file apps the builders inject into
- **Exports**: `template.html` in each skill, build artifacts with no exports

### Module: jsdom smoke suites
- **Location**: `skills/brief-portfolio/app/`, `skills/debrief-meeting/app/`
- **Responsibility**: mount the built template and assert what a failed mount tells the reader
- **Exports**: three new tests per `smoke.test.js`, one per cause

### Dependencies
- payload loaders: No dependencies (foundation)
- app shells: Depends on [payload loaders]
- built templates: Depends on [payload loaders, app shells]
- jsdom smoke suites: Depends on [built templates]

## Tasks

### Phase 0: Foundation

- [ ] Change `loadPayload()` in both `derive.js` files to return `{ payload, error }`: `{ payload: null, error: { kind: 'not-built' } }` when the node text matches `/^__[A-Z]+_PAYLOAD__$/` after trimming, `{ payload: null, error: { kind: 'unreadable', reason: e.message } }` from a bound `catch (e)`, and `{ payload: p, error: null }` otherwise - Acceptance: `rg -n "catch \(e\)" skills/brief-portfolio/app/src/lib/derive.js skills/debrief-meeting/app/src/lib/derive.js` prints one line per file, `rg -n "catch \{" skills/brief-portfolio/app/src/lib/derive.js skills/debrief-meeting/app/src/lib/derive.js` prints no match, and `rg -n "__PORTFOLIO_PAYLOAD__|__MEETING_PAYLOAD__" skills/brief-portfolio/app/src skills/debrief-meeting/app/src` prints no match.
- [ ] Update both `App.svelte` fallback blocks to read the new result: keep the existing not-built sentence verbatim, and render `The injected payload is present but unreadable: {error.reason}` for `kind: 'unreadable'` - Acceptance: `rg -n "present but unreadable" skills/brief-portfolio/app/src/App.svelte skills/debrief-meeting/app/src/App.svelte` prints one line per file, and `rg -n "No data injected. Run" skills/brief-portfolio/app/src/App.svelte` plus `rg -n "No payload was injected into this file" skills/debrief-meeting/app/src/App.svelte` each still print their line.
- [ ] Rebuild both templates: `npm --prefix skills/brief-portfolio/app run build` then copy `app/dist/index.html` over `skills/brief-portfolio/assets/template.html`, and the same for `skills/debrief-meeting` - Acceptance: `rg --count-matches "present but unreadable" skills/brief-portfolio/assets/template.html skills/debrief-meeting/assets/template.html` prints `1` per file, and `rg --count-matches "__PORTFOLIO_PAYLOAD__" skills/brief-portfolio/assets/template.html` and `rg --count-matches "__MEETING_PAYLOAD__" skills/debrief-meeting/assets/template.html` each print `1`.
- [ ] Add three tests to `skills/brief-portfolio/app/smoke.test.js` - the template rendered with its marker left in place shows the not-built sentence; a payload of `{"data":{}}` shows `unreadable: missing data.repos`; a truncated body such as `{"data":{"repos":[` shows `unreadable:` followed by the parser message - taking a raw-text render helper alongside the existing `render(payload)` - Acceptance: `npm --prefix skills/brief-portfolio/app test` reports `# fail 0`, names the three new tests as passing, and its `# pass` total is 19 (16 today plus these three).
- [ ] Add the mirror three tests to `skills/debrief-meeting/app/smoke.test.js`, with `{"transcript":{}}` for the structural case and `missing transcript.turns` as the expected reason - Acceptance: `npm --prefix skills/debrief-meeting/app test` reports `# fail 0`, names the three new tests as passing, and its `# pass` total is 50 (47 today plus these three).

## Success Criteria

- The three causes render three different sentences in each app, and no two of
  the six assertions in the suites expect the same text.
- The unreadable sentences carry the bound reason: `missing data.repos`,
  `missing transcript.turns`, or the parser's own message for truncated input.
- Only the not-built sentence mentions the build step: the rendered unreadable
  message contains neither `build.py` nor `Re-run`, asserted in both suites.
- `npm --prefix skills/brief-portfolio/app test` reports `# pass 19` and
  `npm --prefix skills/debrief-meeting/app test` reports `# pass 50`, both with
  `# fail 0`.
