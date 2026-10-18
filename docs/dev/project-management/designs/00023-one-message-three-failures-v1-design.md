# Design: One fatal message for three different causes

## Architecture fit

The debrief-meeting app is a single-file SPA built by `build.py` from a Svelte
template. The payload lives in one `<script id="meeting-payload"
type="application/json">` DOM node; `derive.js` is the pure-derivation layer
(`App.svelte` imports from it, no other module reads the DOM node). This PRD
stays entirely inside that existing layering: `loadPayload()` (data layer)
gains a richer return shape, `App.svelte` (shell layer) renders one more
branch of the existing fallback, and `template.html` is a build artifact that
just picks up the rebuilt bundle. No new layer or module boundary is needed.

## Module placement

- Edit `skills/debrief-meeting/app/src/lib/derive.js` — `loadPayload()` body only.
- Edit `skills/debrief-meeting/app/src/App.svelte` — the `{#if !payload}` block only.
- Rebuild (not hand-edit) `skills/debrief-meeting/assets/template.html` via
  `npm --prefix skills/debrief-meeting/app run build`.
- Edit `skills/debrief-meeting/app/smoke.test.js` — add `renderRaw` helper and
  three tests, no changes to the existing `render()` helper or `PAYLOAD` fixture.

## Interfaces & contracts

```js
// derive.js
/**
 * @returns {{ payload: object|null, error: null | { kind: 'not-built' } | { kind: 'unreadable', reason: string } }}
 */
export function loadPayload() {
  const node = document.getElementById('meeting-payload')
  const text = node.textContent.trim()
  if (/^__[A-Z]+_PAYLOAD__$/.test(text)) {
    return { payload: null, error: { kind: 'not-built' } }
  }
  try {
    const parsed = JSON.parse(text)
    if (!parsed.transcript?.turns) throw new Error('missing transcript.turns')
    return { payload: parsed, error: null }
  } catch (e) {
    return { payload: null, error: { kind: 'unreadable', reason: e.message } }
  }
}
```

`App.svelte` call site:

```js
const { payload, error } = loadPayload()
```

`App.svelte` fallback block (replaces the current single `<p class="empty">` line):

```svelte
{#if !payload}
  <div class="wrap">
    <h1>Meeting Debrief</h1>
    {#if error?.kind === 'unreadable'}
      <p class="empty">The injected payload is present but unreadable: {error.reason}</p>
    {:else}
      <p class="empty">No payload was injected into this file. Re-run scripts/build.py.</p>
    {/if}
  </div>
{:else}
```

The `{:else}` branch (success path) is unchanged; only the `payload`
destructure changes at the top of the fallback's data source.

`smoke.test.js` additions:

```js
function renderRaw(rawText, opts) {
  // same jsdom-mount machinery as render(), but substitutes the marker with
  // rawText verbatim instead of JSON.stringify(payload) — lets a test mount
  // the template with the marker untouched, or with malformed/truncated JSON.
}
```

`renderRaw` shares `render()`'s DOM-mount body (script extraction, jsdom
construction, error capture, `flush`/`openTab` helpers) but takes the
replacement text as a raw string instead of serializing a payload object.
Implementation: factor `render()`'s mount body into a private
`mount(pageHtml)` the two exported functions both call, `render()` builds
`pageHtml` via `JSON.stringify`, `renderRaw()` passes `rawText` through
unescaped except for the existing `<\/` guard.

## Data flow

1. `build.py` writes either the literal placeholder (untouched template, the
   not-built case) or a JSON payload (possibly truncated by a killed build,
   or — not reproducible by `build.py` itself today, but defended anyway —
   structurally wrong) into the `meeting-payload` script node.
2. `loadPayload()` reads `node.textContent`, classifies it in one pass (marker
   regex → JSON.parse → shape check), and returns `{ payload, error }`.
3. `App.svelte` destructures the result once at mount time and renders exactly
   one of three branches: not-built sentence, unreadable sentence with the
   bound reason, or the real app.
4. No other component reads `error`; `payload` flows into `transcript`/`extract`
   exactly as before.

## Reuse inventory

- `loadPayload()` itself (`skills/debrief-meeting/app/src/lib/derive.js:8-17`)
  is the one and only payload reader — extended in place, no second reader
  created.
- `App.svelte`'s existing `{#if !payload}` block (`:61-65`) is the one and
  only fallback-render site — extended in place, no new component.
- `smoke.test.js`'s `render()` helper (`:58-91`) already contains the full
  jsdom-mount machinery (script extraction, virtual console, error capture);
  `renderRaw()` reuses it via a shared `mount()` instead of duplicating it.
- Searched for an existing "classify failure"/"diagnose error" helper
  elsewhere in the skill (`rg -n "kind.*unreadable|not-built|classify|diagnose" skills/debrief-meeting`)
  and across other skills with injected-payload apps
  (`rg -rn "getElementById\('.*-payload'\)" skills/*/app/src 2>/dev/null`): nothing
  found — this pattern (DOM-node JSON payload + one build-time marker) is
  local to debrief-meeting; no shared utility to reuse or extract to.

## Alternatives considered

- **Smallest-diff version**: keep `loadPayload()` returning bare `null`/`payload`
  and add a *second* function, e.g. `classifyPayloadError()`, called
  separately by `App.svelte` only when `payload` is falsy, re-reading the DOM
  node a second time. Rejected: reads the DOM node twice and reintroduces the
  exact bug this PRD fixes — a second, independent `try/catch` that can again
  diverge from the first. The PRD's Must-haves name `loadPayload()`'s return
  shape directly, so this alternative does not fit the Requirements anyway.
- **Chosen**: `loadPayload()` returns `{ payload, error }` in one pass, single
  source of truth, single call site. Slightly larger diff than the smallest
  version (touches the call site's destructuring) but eliminates the
  double-read risk and matches the PRD's named Acceptance commands exactly.
- **Exception-based**: have `loadPayload()` throw three distinct typed errors
  and let `App.svelte` catch-and-branch. Rejected: Svelte 5 top-level
  `<script>` code runs at module-eval time; an uncaught throw there aborts
  the whole component mount rather than rendering a fallback, so the shell
  would need its own wrapping `try/catch` anyway — strictly more code than
  the return-shape version for the same behavior.

## Risks & edge cases

- **Edge case already covered by the Must-haves**: a payload that parses as
  JSON but lacks `transcript.turns` (structurally wrong) and a payload that
  fails `JSON.parse` outright (truncated) both land in `kind: 'unreadable'`
  with `reason` taken from whichever exception fired — no special-casing
  needed between them, `e.message` already differs (`"missing
  transcript.turns"` vs. the parser's own message).
  - **Why this reads as a single-pass classification, not a parse-then-validate
    sequence that risks a third case**: `JSON.parse` throws on truncated input
    before the shape check runs, so the `catch (e)` block's `e.message` is
    whichever of the two failures actually happened. This is intentional, not
    an omission — the PRD's two unreadable sub-cases are fully disjoint
    (parse failure vs. parse success + shape failure) and the one `catch`
    already distinguishes them via `e.message`.
- **Likely next change 1**: a fourth cause (e.g. payload present but
  `extract` missing while `transcript` is fine) would want its own `kind`.
  The `{ kind, reason? }` shape already generalizes to that without touching
  `App.svelte`'s branch structure beyond adding an `{:else if}`.
- **Likely next change 2**: another skill in this repo adopting the same
  injected-payload-SPA pattern (the reuse sweep found none today) would want
  this exact `{ payload, error }` contract extracted to a shared helper. Not
  worth doing now for a single consumer — flagged here so it doesn't get
  missed.
- **Boxed-in by this design**: none — the return shape is additive and the
  regex-based not-built detection is independent of payload content, so later
  payload-shape changes don't touch the not-built path.

## Test strategy outline

- Three new `smoke.test.js` tests, one per cause, each via `renderRaw`:
  1. template rendered with the marker left in place (regex match) → asserts
     the not-built sentence.
  2. `renderRaw(JSON.stringify({transcript: {}}))` → structurally wrong →
     asserts `unreadable: missing transcript.turns`.
  3. `renderRaw('{"transcript":{"turns":[')` → truncated → asserts
     `unreadable:` followed by whatever `JSON.parse` throws on that string
     (verify the literal message in a scratch Node REPL run during
     implementation rather than hardcoding a guess — V8's wording is stable
     across Node versions but the exact phrase must be copied, not assumed).
- Existing `render()`-based tests are unaffected (success path unchanged).
- `npm --prefix skills/debrief-meeting/app test` is the one gate; no Python
  test changes (this PRD touches no `.py` file).

## Review log

- non-blocker: `renderRaw(rawText, opts)` carries an unused `opts` param copied from `render()`'s signature — none of the three new tests need it; trim to `renderRaw(rawText)` unless a planned test needs options.
- non-blocker: `node.textContent.trim()` in the new `loadPayload()` has no observed motivating case (the measured template has no surrounding whitespace around the marker) — precautionary, not wrong.
- question: empty `textContent` falls into `kind: 'unreadable'` (JSON.parse('') throws) rather than `kind: 'not-built'` — not reachable via `build.py` today, confirmed out of scope rather than overlooked.
dispatch 1 (claude): cardinal-sin 0, blocker 0, non-blocker 2, question 1
- non-blocker: structural validation stays narrow (`!parsed.transcript?.turns` accepts truthy-but-invalid shapes like `turns: "bad"`); the "structurally wrong" diagnosis covers only missing `turns`, not general corruption — preserves an existing limitation.
- non-blocker: the test strategy's literal-parser-message assertion risks runtime dependence across JS engine versions — assert the `unreadable:` prefix plus a nonempty reason, or derive the expected message at test runtime rather than hardcoding it.
- non-blocker: the exception-based alternative's rationale is imprecise (Svelte top-level `<script>` runs at component-init time, not strictly "module evaluation") — the conclusion (reject exceptions, prefer the result-shape) still holds.
- question: Module placement says "no changes to the existing `render()` helper" while Interfaces & contracts has `render()` delegate to a new `mount()` — clarified: `render()`'s signature and external behavior are unchanged, only its implementation delegates internally.
dispatch 2 (codex): cardinal-sin 0, blocker 0, non-blocker 3, question 1
