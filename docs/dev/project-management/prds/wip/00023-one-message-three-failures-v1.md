---
default_model: opus
rework_cap: 5
---

# One fatal message for three different causes, and it names the cause that is usually wrong

## Problem

Three distinct failures - the placeholder was never substituted, the payload
parses but is structurally wrong, the payload was truncated mid-write - all
render one fixed message with an empty console. `loadPayload()` in
`skills/debrief-meeting/app/src/lib/derive.js:8-17` throws its own diagnosis
away: it runs `if (!parsed.transcript?.turns) throw new Error('missing
transcript.turns')` inside `try { … } catch { return null }`, an unbound catch
that never logs. The single `null` then reaches the inline `{#if !payload}`
block in `skills/debrief-meeting/app/src/App.svelte:61-65` (there is no
separate fallback component), which tells the reader to run the build step.
That instruction is wrong in the two cases where the build already ran and
would reproduce the same file, at the exact moment something has already gone
wrong. Source: agoge run
`docs/dev/project-management/audit-results/agoge-2026-08-31.md`, finding 14
(MEDIUM, ux lane); decision 2026-09-02: accepted, bind the error and render it
under the fallback. The finding's brief-portfolio half is moot: commit af1b704
deleted that skill (rescoped 2026-10-17).

```
Three mounts, byte-identical page text and "logs": [] each time. The
distinguishing information exists and is thrown away:
if (!parsed.transcript?.turns) throw new Error('missing transcript.turns')
sits inside try { … } catch { return null }. The app tells the user to
"Re-run scripts/build.py", a step that already ran and will reproduce the
identical file.
```

## Solution

Give `loadPayload()` a result shape instead of a bare `null`: `{ payload, error }`
where `error` is `null`, `{ kind: 'not-built' }`, or `{ kind: 'unreadable',
reason }` carrying the bound `catch (e)` message. The not-built case is the
`meeting-payload` node still holding the build marker, detected by pattern
(`/^__[A-Z]+_PAYLOAD__$/` against the trimmed text) and never by the literal
marker string, because `build.py` substitutes every occurrence of that marker
in the template (`skills/debrief-meeting/scripts/build.py:19` names it,
`:144` is a plain `str.replace`) and a second copy inside the bundle would be
overwritten with the whole payload. `App.svelte` keeps its current wording for
the not-built case and renders the unreadable case with the bound reason. The
template gets rebuilt, and the jsdom suite gains one test per cause.

## Requirements

### Must have
- Not-built case, exact text unchanged:
  `No payload was injected into this file. Re-run scripts/build.py.`
- Structurally-wrong and truncated cases render
  `The injected payload is present but unreadable: <reason>`, with `reason` being
  `missing transcript.turns` for the structural case and the JSON parser's own
  message (for example `Unexpected end of JSON input`) for the truncated case.
- Neither unreadable message advises running or re-running the build step.
- The literal marker text `__MEETING_PAYLOAD__` does not appear in any
  `app/src/` file (today it lives only in `skills/debrief-meeting/app/index.html:9`), and the rebuilt
  template still holds exactly one occurrence of it.
- The suite covers all three causes and asserts the three texts differ.

### Nice to have
- none

## Implementation

### Module: payload loader
- **Location**: `skills/debrief-meeting/app/src/lib/`
- **Responsibility**: read the injected JSON node and classify why it is unusable
- **Exports**: `loadPayload()` in `derive.js`, new return shape `{ payload, error }`

### Module: app shell
- **Location**: `skills/debrief-meeting/app/src/`
- **Responsibility**: the inline `{#if !payload}` fallback the app renders when nothing mounts
- **Exports**: `App.svelte`

### Module: built template
- **Location**: `skills/debrief-meeting/assets/`
- **Responsibility**: the pre-built single-file app `build.py` injects into
- **Exports**: `template.html`, a build artifact with no exports

### Module: jsdom smoke suite
- **Location**: `skills/debrief-meeting/app/`
- **Responsibility**: mount the built template and assert what a failed mount tells the reader
- **Exports**: three new tests in `smoke.test.js`, one per cause, and a raw-text render helper
- New symbols: `renderRaw`, `renders the not-built sentence when the marker was never substituted`, `renders the bound reason for a structurally wrong payload`, `renders the parser message for a truncated payload`

### Dependencies
- payload loader: No dependencies (foundation)
- app shell: Depends on [payload loader]
- built template: Depends on [payload loader, app shell]
- jsdom smoke suite: Depends on [built template]

## Tasks

### Phase 0: Foundation

- [ ] Change `loadPayload()` in `skills/debrief-meeting/app/src/lib/derive.js` to return `{ payload, error }`: `{ payload: null, error: { kind: 'not-built' } }` when the node text matches `/^__[A-Z]+_PAYLOAD__$/` after trimming, `{ payload: null, error: { kind: 'unreadable', reason: e.message } }` from a bound `catch (e)`, and `{ payload: parsed, error: null }` otherwise - Acceptance: `rg -n "catch \(e\)" skills/debrief-meeting/app/src/lib/derive.js` prints one line, `rg -n "catch \{" skills/debrief-meeting/app/src/lib/derive.js` prints no match, and `rg -n "__MEETING_PAYLOAD__" skills/debrief-meeting/app/src` prints no match.
- [ ] Update the `App.svelte` fallback block to read the new result: keep the existing not-built sentence verbatim, and render `The injected payload is present but unreadable: {error.reason}` for `kind: 'unreadable'` - Acceptance: `rg -n "present but unreadable" skills/debrief-meeting/app/src/App.svelte` prints one line, and `rg -n "No payload was injected into this file" skills/debrief-meeting/app/src/App.svelte` still prints its line.
- [ ] Rebuild the template: `npm --prefix skills/debrief-meeting/app run build` then copy `app/dist/index.html` over `skills/debrief-meeting/assets/template.html` - Acceptance: `rg --count-matches "present but unreadable" skills/debrief-meeting/assets/template.html` prints `1`, and `rg --count-matches "__MEETING_PAYLOAD__" skills/debrief-meeting/assets/template.html` prints `1`.
- [ ] Add three tests to `skills/debrief-meeting/app/smoke.test.js`, named `renders the not-built sentence when the marker was never substituted` (the template rendered with its marker left in place), `renders the bound reason for a structurally wrong payload` (a payload of `{"transcript":{}}` shows `unreadable: missing transcript.turns`) and `renders the parser message for a truncated payload` (a body such as `{"transcript":{"turns":[` shows `unreadable:` followed by the parser message), driven through a `renderRaw(text)` helper that substitutes the marker with raw text, beside the existing `render(payload = PAYLOAD, { storage } = {})` at `skills/debrief-meeting/app/smoke.test.js:58` - Acceptance: `npm --prefix skills/debrief-meeting/app test` reports `# fail 0` and lists each of the three names as passing (never a `# pass` total: other PRDs add tests to this suite).

## Success Criteria

- The three causes render three different sentences, and no two of the three
  new assertions expect the same text.
- The unreadable sentences carry the bound reason: `missing transcript.turns`,
  or the parser's own message for truncated input.
- Only the not-built sentence mentions the build step: the rendered unreadable
  message contains neither `build.py` nor `Re-run`, asserted in the suite.
- `npm --prefix skills/debrief-meeting/app test` reports `# fail 0` with the
  three new tests listed as passing.
