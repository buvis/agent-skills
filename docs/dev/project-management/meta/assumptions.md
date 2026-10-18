# Assumptions ledger — PRD 00023

## 1: Change loadPayload() to classify the three fallback causes

- Used the `loadPayload()` body word for word from the design's "Interfaces & contracts" section, including `.trim()` and the marker regex.
- `document.getElementById('meeting-payload')` now sits outside the try. If the node is missing, it throws instead of returning a value. No test covers that case, and the design places it outside the try.
- (Tess, strengthen pass) Did not add a test for the missing `#meeting-payload` DOM node case; marked in-contract per the brief since the design doc treats it as out of scope (not reachable via the real template).
- (Tess, strengthen pass) Reused the substring-marker test as the "second distinct success input" Devon's weak point 1 asked for, rather than adding a separate ninth case, since it already satisfies both requirements without duplication.
