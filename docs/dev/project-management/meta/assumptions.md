# Assumptions ledger — PRD 00023

## 1: Change loadPayload() to classify the three fallback causes

- Used the `loadPayload()` body word for word from the design's "Interfaces & contracts" section, including `.trim()` and the marker regex.
- `document.getElementById('meeting-payload')` now sits outside the try. If the node is missing, it throws instead of returning a value. No test covers that case, and the design places it outside the try.
- (Tess, strengthen pass) Did not add a test for the missing `#meeting-payload` DOM node case; marked in-contract per the brief since the design doc treats it as out of scope (not reachable via the real template).
- (Tess, strengthen pass) Reused the substring-marker test as the "second distinct success input" Devon's weak point 1 asked for, rather than adding a separate ninth case, since it already satisfies both requirements without duplication.

## 2: Update App.svelte fallback to render the bound reason

- Assumed `derive.js`'s `loadPayload()` already implements the `{ payload, error }` return shape described in the dispatch's Interfaces & contracts (it was not in Ivan's allowlist to read/verify directly; git log shows the prior task landed it).

## 3: Rebuild template.html from the updated bundle

- ASSUMPTIONS: none (pure build + copy, no judgment calls).

## 4: Add three smoke tests covering the three fallback causes

- Drove `renderRaw` with the literal marker string read out of the template (`readFileSync(TEMPLATE).match(/__[A-Z]+_PAYLOAD__/)[0]`) rather than a hardcoded `'__MEETING_PAYLOAD__'` literal, so the test does not encode the marker name as a second source of truth.
- Computed the truncated-payload test's expected parser message by running `JSON.parse` on the same string inside the test and catching the thrown message, instead of a hardcoded string literal, since V8's wording can vary by environment.
- Used `doc.querySelector('.empty')` (not `main .empty`) for the three new tests, since the fallback markup has no `<main>` element in the error-fallback state.
