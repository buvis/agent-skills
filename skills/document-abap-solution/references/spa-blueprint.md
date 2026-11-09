# Explorer SPA Blueprint

Read this during Phase 5. It defines the data contract, the tech pipeline, the views, the design system, and the pass/fail gates for the interactive explorer.

## Product bar

The explorer's first job is to ORIENT a developer who opened this file knowing nothing about the solution. Job one, most frequent by far: "I have to change this thing tomorrow — where do I start?" Only after that is it a lookup instrument ("I saw ZCL_FOO in a dump, what is it?") and a mental-model builder ("how does a request flow end to end?"). It is dense-but-calm and IDE-adjacent in *aesthetics*, but its opening screen is a curriculum, not a control panel. The audience is expert at SAP and new to THIS code; respect their platform fluency, never assume they know this solution.

Test of the first 10 seconds: a first-time visitor sees what the solution is, how far this explorer covers it, and an explicit ordered "start here" path — not a raw architecture dump. A landing screen whose first content is a layer list or a dependency-edge table has failed this test. After 20 minutes a newcomer can answer: what does this do, which pattern do I copy for my task, how does a request flow, which objects matter, what will bite me. Every view earns its place against one of those; if it does not, cut it.

**This blueprint is a hard contract, not a mood board.** The failure this section fights is real and observed: a generator reads the prose, likes the design tokens, and ships a naive version that dumps data on the landing screen and buries the guided path. The Orientation contract and Interaction contracts below are checkable requirements with pass/fail gates. The no-node "path B" is permission to drop the *build tooling* (Svelte, Shiki, FLIP), never permission to drop an interaction contract or the orientation screen.

## Non-negotiables

- ONE self-contained `explorer/dist/explorer.html`. Opens via `file://` double-click on enterprise Windows (current Chrome/Edge). No server, no CDN, fully offline. Budget <= 1.5 MB.
- Every piece of content renders from the inlined solution data (a `<script type="application/json" id="solution-data">` block inside the HTML). The app is a generic viewer; the data is solution-specific. Never hand-weave solution content into markup. **Never emit a separate `solution.json` file** — the data lives inside the HTML; a file:// page cannot fetch siblings.
- The end user never builds anything. Builds happen on the authoring machine only.

## Pipeline

1. **Build the solution data** from the Phase 3 synthesis artifacts (traces from architecture.md, recipes from cookbook.md, cards and ledger from `research/`). Same stable IDs as the docs — the recipe set in `recipes[]` is the cookbook's recipe set, not a re-derived one. **The data is inlined directly into the HTML** as `<script type="application/json" id="solution-data">{...}</script>` — compact JSON, no external file. There is no separate `solution.json` deliverable. The `file://` protocol blocks fetch/XHR to relative paths in every modern browser; an external JSON file that "works from file://" is a lie that ships broken every time.
2. **Validate it**: write and run a small `explorer/validate.mjs` that checks BOTH:
   - **Contract completeness:** every non-optional top-level section present (`meta, layers, objects, edges, traces, patterns, recipes, wizard, cheatsheet, glossary, gotchas`; optional: `capabilities, onboarding_path, challenges`); `objects[]` length equals the ledger count minus OUT (the Catalog view IS the L4 catalog — a solution.json without `objects[]` has no explorer, just a brochure); every pattern and recipe ID from the docs present; every `recipes[].code` non-empty AND every `recipes[].source_objects[]` non-empty and resolving to `objects[]` (a recipe with no real source object is a fabricated template — fail or force the `placeholder:true` flag that drives the TEMPLATE marking); `onboarding_path` present and non-empty (the Overview curriculum depends on it; its absence is a Phase 3 gap, not an SPA choice); every trace step carries `object_id` and `detail`, and each `object_id` resolves to `objects[]` (a trace step citing an unread/absent object is a fabricated step — the SKILL Phase 3 rule).
   - **Referential integrity:** every `steps[].object_id`, `edges[].from/to`, `wizard` `recipe_id`, `recipes[].related`, `gotchas[].related_objects`, `onboarding_path[].link`, and `challenges[].related_object` resolves; every `objects[].layer` exists in `layers[]`; IDs unique.
   It prints a numbers report (objects, edges, trace steps, recipes with code, wizard nodes, gotchas, glossary terms) that goes verbatim into the phase report. Build only after it passes.
3. **Scaffold**: Svelte 5 + Vite + `vite-plugin-singlefile` (path A, default when node is available). Never SvelteKit.
4. **Implement views** (below) against the data contract.
5. **Highlight code at build time** with Shiki (`lang: 'abap'`, dual themes `github-light`/`github-dark`; prefer `defaultColor: 'light-dark()'`, else the documented dual-theme CSS snippet). Zero runtime highlighting JS.
6. **Build** and check size; open `dist/explorer.html` from `file://`.
7. **Verify** with the checklist at the end (use browser automation tools if the session has them, otherwise walk the user through it).

Path B (no node available): one hand-authored `explorer/dist/explorer.html`. Same design system — paste `assets/explorer.css` verbatim as the first `<style>` block — same data (inlined as `<script type="application/json">`), `<template>` elements plus event delegation, a ~60-line regex ABAP tokenizer emitting the stylesheet's `.tok-*` classes (keywords, comments, strings, numbers) instead of Shiki. Skip FLIP animations. Everything else in this blueprint still applies.

### vite.config.js (path A, exact)

```javascript
import { defineConfig } from 'vite';
import { svelte } from '@sveltejs/vite-plugin-svelte';
import { viteSingleFile } from 'vite-plugin-singlefile';

export default defineConfig({
  plugins: [svelte(), viteSingleFile()],
  build: {
    target: 'es2022',
    assetsInlineLimit: 100000000,
    chunkSizeWarningLimit: 100000000,
    cssCodeSplit: false,
    rollupOptions: { output: { inlineDynamicImports: true } }
  }
});
```

Pitfalls: no external CSS `@import`; no webfont files; no dynamic imports; import `solution.json` statically.

## solution.json contract

```jsonc
{
  "meta": { "title", "summary", "system", "root_package", "generated_at", "coverage_pct", "object_count" },
  "layers": [ { "id", "name", "order", "summary" } ],
  "objects": [ { "id", "name", "type", "package", "layer", "role", "pattern_ids": [], "summary", "tags": [], "links": [] } ],
  "edges": [ { "from", "to", "kind", "label" } ],          // kind: inherits|implements|calls|reads|writes|registered_in|triggers
  "traces": [ { "id", "title", "paradigm",
    "steps": [ { "seq", "object_id", "layer_id", "action", "detail", "direction", "is_async", "code" } ] } ],
  "patterns": [ { "id", "name", "summary", "count" } ],
  "recipes": [ { "id", "title", "use_when", "difficulty", "prerequisites": [], "source_objects": [],
    "code": [ { "lang", "src", "annotations": [] } ], "register", "verify", "differs_from", "related": [] } ],
  "capabilities": [ { "area", "feature", "status", "hint", "example_object" } ],   // status: used|partial|unused
  "wizard": { "start_node", "nodes": [ { "id", "text", "options": [ { "label", "next_node", "recipe_id" } ] } ] },
  "cheatsheet": { "sections": [ { "title", "rows": [ [ "..." ] ] } ] },
  "glossary": [ { "term", "definition" } ],
  "gotchas": [ { "id", "severity", "description", "related_objects": [] } ],
  "onboarding_path": [ { "seq", "label", "link", "detail" } ],
  "challenges": [ { "id", "title", "code", "question", "answer", "related_object" } ]   // optional; only from real bugs
}
```

`direction` on trace steps: `in|out|internal|db` (renders as a badge like `RFC IN`, `DB UPDATE`). Code on steps and recipes is pre-highlighted HTML after the Shiki pass (path A) or raw source for the runtime tokenizer (path B).

## Views (5): names, verbs, routes

Name views for the developer's intent, not the data model. "Router" reads as a network device, "Registry" as regedit, "Map" as abstract — all make an expert hesitate. Use the verb names:

| View | Verb | Answers | Route |
|---|---|---|---|
| **Overview** | Orient | "What is this and where do I start?" | `#/overview` |
| **Lifecycle** | Follow | "How does a request flow end to end?" | `#/lifecycle/<trace>/<step>` |
| **Cookbook** | Build/Fix | "How do I add or change one?" | `#/cookbook/<recipe>` |
| **Catalog** | Look up | "I saw ZCL_FOO in a dump — what is it?" | `#/catalog/<object>` |
| **Reference** | Verify | "What are the rules, names, gotchas?" | `#/reference` |

Left nav rail (or top bar), keyboard-reachable, `aria-current` on the active view. Default route is `#/overview`, never a data view. On load parse the hash; on change sync it.

**Nav tab styling rules (mandatory):**
- The `.ax-app` grid MUST account for all direct children: header, banner, nav, main, footer → `grid-template-rows: auto auto auto 1fr auto`. The original 4-row grid (`auto auto 1fr auto`) assigned `1fr` to the nav, stretching it to fill viewport height. The nav is ALWAYS the 3rd child (after header and banner) and must be `auto`, with `1fr` on `<main>`.
- Active tab uses `aria-current="page"` (not just attribute presence — inactive tabs get `aria-current="false"` which still matches `[aria-current]`). CSS must target `[aria-current="page"]`.
- Active tab gets accent-tinted background (`background: var(--ax-accent-weak)`) plus the bottom border indicator — the bottom border alone is too subtle and visually indistinguishable from the nav container's border.
- Nav buttons get `outline: none` unconditionally. The global `:focus-visible` outline expands the nav bar height because `outline` is drawn OUTSIDE the element box. Instead, keyboard focus uses `outline: none; box-shadow: inset 0 0 0 2px var(--ax-accent)` — this stays INSIDE the button and cannot change its dimensions. The `outline: none` must be repeated in the `:focus-visible` rule to override the global `:focus-visible { outline: 2px solid }`.
- These rules are in `assets/explorer.css` — embed it verbatim and do not improvise alternatives.

Global chrome on every view:
- **Command palette:** Ctrl+K AND `/` (when no input is focused) open a `<dialog>` searching objects, recipes, glossary terms, and gotchas in one grouped list, keyboard-first; Enter deep-links. Both keys are required — `/` is the reflex an SAP developer already has. Fastest answer to "what is ZCL_FOO?".
- **First-run tour:** on first open, a 5-step dismissible popover names the five views, one sentence each. Esc dismisses forever (`abapx:<solution-id>:toured`); never blocks interaction.
- **`?`** opens a shortcuts popover listing every key.
- **Coverage banner (when `meta.coverage_pct < 100`):** a thin persistent strip — "Partial map: N of M objects explored (P%). Unread: <domains>." Framing is deliberate curation, not breakage. It is the honest face of an INCOMPLETE run (see SKILL Phase 6); a partial explorer that hides its partiality is the failure.

### 1. Overview (Orient) — the orientation contract

This is the landing screen and the most important view. Its content order is fixed:

1. **Hero (first 10 seconds).** One calm block: `meta.title`, one-sentence `meta.summary` in plain words, and the coverage line ("Maps N of M objects — P% — enough to <the reader's job>"). No layer list, no table here.
2. **Day-one path (the curriculum).** Render `onboarding_path[]` as an ordered checklist at the TOP of the view, directly under the hero — each step a one-line label + deep link, checkbox state persisted in `localStorage`. Step 1 is always "watch the primary lifecycle trace" so day one starts from a concrete run. This array is the whole point of the view; if the data has it and the view buries or omits it, the view is wrong. (Observed failure: `onboarding_path` present in the data, rendered nowhere.)
3. **The shape (below the fold).** Layer bands as nested semantic HTML, objects listed within; hovering/focusing a layer highlights its objects. Clicking an object opens `#/catalog/<id>`.

**Do NOT put a raw dependency-edge table on this view.** A flat FROM|type|TO list is unreadable out of context and reads as noise to a newcomer. Edges belong on a Catalog object's page, in the context of one object. (Observed failure: a raw edge table dumped as landing content.)

### 2. Lifecycle (Follow) — the centerpiece; interaction contract below.

### 3. Catalog (Look up)
A dense filterable grid of all objects, `<search>` wrapping the filter input. Instant filtering: zero debounce, matched substrings in `<mark>`, `scrollbar-gutter: stable`, `content-visibility: auto` on rows for large solutions. Row click opens an object `<dialog>`: role, package, patterns, edges in/out, gotchas touching it, visited checkmark, a 1-hop neighborhood mini-graph (hand-rolled SVG from `edges[]`). Second tab: capability matrix. **Dialogs open with `showModal()` — never `show()` — so they center in the viewport over a dimmed `::backdrop`; the canonical stylesheet keeps `dialog { margin: auto }` because a global margin reset silently pins native dialogs to the top-left corner.** (Observed failure: inspector dialog floating in the upper-left instead of centered.)

**Unmapped-reference rule (hard):** an edge or link whose target is not in `objects[]` (standard SAP, or an object beyond this run's coverage) renders as muted text with a dashed underline and a `title` ("standard SAP / not yet explored"), NEVER as a live link. A link to a blank page destroys trust instantly and is the fastest way an explorer feels broken. Every render loop that emits a link checks `objById[target]` first.

### 4. Cookbook (Build/Fix)
Top: the decision wizard as breadcrumb chips; answering narrows to a recipe. Below: all recipes as `<details name="recipes">` exclusive accordions, filterable by title, use-when text, and source object names. Signature: the wizard scrolls the chosen recipe into view and flashes a 200 ms accent outline. Each recipe shows its real source object name and embeds real banked code.

**Placeholder-code rule (hard):** recipe `code` comes from the snippet bank and names its real source object. If a code sample is a template with invented names (a `..._EXAMPLE_...` class), it is wrapped in a dashed `--warn` border with a corner label "TEMPLATE — adapt, do not paste" so no one ships fake code as real. Real banked source and placeholder templates must never look identical. (Observed failure: recipes shipped invented `zcl_..._example_h00` code indistinguishable from real source.)

### 5. Reference (Verify)
Dense tables from `cheatsheet`, glossary, gotchas sorted by severity. Print-ready: a `@media print` stylesheet renders this view alone as one clean page (nav hidden, forced light). When `challenges[]` exists (only from real bugs found), offer spot-the-bug cards.

Glossary terms anywhere: `<button popover>` tooltips via CSS anchor positioning, with a plain `title=` fallback (anchor positioning is the one riskier feature on older Edge). In a dense acronym domain these save constant context-switching — wire them, don't skip them.

Progress: visited objects and read recipes tick off in `localStorage` under `abapx:<solution-id>:*`; show "12/87 objects visited" in the rail. Theme: `color-scheme: light dark` follows the OS; a compact toggle (system/light/dark) persists and flips `color-scheme` on the root. Both schemes are required and must be tested — enterprise ABAP developers often run light-themed GUIs in bright rooms; a hardcoded dark-only palette is hostile. (Observed failure: blueprint asked for `light-dark()`, generator hardcoded dark tokens only.) Layout holds to ~900 px, then the rail collapses to icons.

## Lifecycle interaction contract (the trace stepper)

This is the view most often gotten wrong, so it is a contract, not a suggestion. The observed failure mode: all N steps rendered as one long vertical list, the active step tinted mid-list, Prev/Next buttons at the very bottom after every step. Result — you cannot see the active step and the Next control at once; clicking Next re-renders and snaps the page to the top; you lose your place every step. That layout is forbidden.

Required layout — two panes in a fixed-height grid that fills the viewport, each pane scrolling independently, controls pinned:

```
┌──────────────────────────────────────────────────────────────┐
│  |◀  ◀ Prev      Step 4 / 10  ── slider ──      Next ▶  ▶|    │ ← control bar, sticky top of the view
├───────────────────────────┬──────────────────────────────────┤
│ TIMELINE  (≈35%, scrolls) │ INSPECTOR (≈65%, scrolls)         │
│  ● 1 trigger fires        │ Step 4 · DB                       │
│  │ 2 authorize            │ Dispatcher reads ZREG_STEPS       │
│  │ 3 read config          │ <object link → Catalog>           │
│  ●▶4 dispatcher  (active) │ detail prose …                    │
│  │ 5 run step             │ ┌ code / payload (banked) ──────┐ │
│  │ …                      │ └───────────────────────────────┘ │
└───────────────────────────┴──────────────────────────────────┘
```

Hard rules:
- **The page never scrolls when advancing a step.** Advancing moves the active node into view *inside the left pane only* — `activeNode.scrollIntoView({block:'nearest'})` on the timeline's own scroll container, never `window.scroll`, never a full re-render that resets scroll. The inspector swaps content in place with no layout shift.
- **Controls are always visible.** The `|◀ ◀ Prev · Step X/N · Next ▶ ▶|` bar plus an `<input type="range">` scrubber are sticky at the top of the view, reachable without scrolling past the steps. Never place navigation below the step list.
- **Keyboard:** when the hash is on `#/lifecycle`, `←`/`→` step, `Home`/`End` jump to first/last. Guard so arrows in the palette input don't leak.
- **Active step is unmistakable:** accent node + connector, and the inspector header states "Step X / N". `is_async` steps get dashed connectors; `direction` renders as a badge (`RFC IN`, `DB UPDATE`).
- The object name in the inspector links to its Catalog dialog. No autoplay. `prefers-reduced-motion` kills smooth-scroll and pulse; stepping still works.
- Narrow (<720 px): panes stack — control bar stays pinned on top, timeline collapses to a compact strip above the inspector; still no page scroll to reach Next.

## Design system

**The design system ships as a literal stylesheet: `assets/explorer.css` next to this skill (same lookup as the references).** Embed it VERBATIM as the explorer's first stylesheet — path A imports it as global CSS, path B pastes it into the first `<style>` block — and append view-specific rules after it, never overriding its tokens. This is the consistency mechanism: prose descriptions of a design get re-improvised by every run (observed: each iteration shipped a different look — different palettes, fonts, radii); a shipped stylesheet renders identically every time while the content stays 100% data-driven from `solution.json`. The file carries a version-marker comment (`abapx-style v1`) that the Phase 6 self-check greps for in the built HTML. It provides: tokens, app chrome (`.ax-header/.ax-nav/.ax-main/.ax-footer`), coverage banner (`.ax-banner`), tables, bordered rows, badges (`.ax-badge is-core/is-impl/is-high/...`), code blocks with tokenizer classes (`.tok-kw/.tok-str/.tok-com/.tok-num`), the TEMPLATE marker (`.ax-template`), centered dialogs, inputs/buttons, accordions, the trace stepper (`.ax-trace-bar/.ax-trace/.ax-tl/.ax-step`), wizard chips, unmapped-reference styling, print and reduced-motion rules.

The tokens below describe that file for reference (the file is the source of truth):

```css
color-scheme: light dark;
--bg:         light-dark(oklch(0.98 0 0),  oklch(0.18 0 0));
--surface:    light-dark(oklch(1 0 0),     oklch(0.22 0 0));
--border:     light-dark(oklch(0.9 0 0),   oklch(0.3 0 0));
--text:       light-dark(oklch(0.2 0 0),   oklch(0.9 0 0));
--text-muted: light-dark(oklch(0.4 0 0),   oklch(0.7 0 0));
--accent:     oklch(0.55 0.15 250);   /* one sharp technical blue; derive hover/borders via color-mix() */
font-family:  system-ui, "Segoe UI", Roboto, "Helvetica Neue", sans-serif;
/* code: */   ui-monospace, "Cascadia Code", Consolas, monospace;
```

- Type scale, total five sizes: 12 (badges/meta), 14 (body, default), 16, 20, 24. Line-height 1.5, mono 1.4.
- Spacing on a strict 4 px grid: 4/8/16/24/32/48 only. Radii: 2 px interactive, 4 px containers, nothing above 6 px, no pills.
- Depth via 1 px borders, not shadows. Only `<dialog>` and popovers get a shadow: `0 8px 24px color-mix(in oklch, var(--text) 15%, transparent)`.
- Tables: 32 px rows, no vertical rules, 1 px bottom borders, even rows tinted `color-mix(in oklch, var(--text) 2%, transparent)`. Numeric columns right-aligned with `font-variant-numeric: tabular-nums`.
- Code blocks: `--surface` background, 1 px border, square corners, unselectable muted line numbers, `overflow-x: auto`, `white-space: pre`. Annotation highlights as `<mark>` rows tinted `color-mix(in oklch, var(--accent) 15%, transparent)`. Every code block gets a copy button; copied state flashes the block outline in accent for 200 ms.
- Focus: `outline: 2px solid var(--accent); outline-offset: -1px` via `:focus-visible` on every interactive element.
- Icons: inline monochrome SVG (`currentColor`, stroke <= 2), one consistent set, never emoji.
- Headings `text-wrap: balance`; long descriptions `text-wrap: pretty`. Empty states: one muted sentence plus the action that fills the view, no illustrations.
- Reference aesthetics: GitHub Primer table density and 1 px border discipline; Linear type scale and muted-text restraint. Steal numbers, not vibes.

## Platform features: use / skip

USE: same-document View Transitions (150 ms crossfade between views); `@starting-style` + `transition-behavior: allow-discrete` (dialog/popover enter-exit); popover + CSS anchor positioning (tooltips; with fallback); `<dialog>` (object inspector); `<details name>` + `::details-content` (recipe accordions); `:has()` (row/state styling); container queries + cq units (recipe cards adapt in dialog vs full width); CSS nesting; OKLCH + `color-mix()`; `light-dark()`; `@property` (trace pulse); `text-wrap`; `<search>`; subgrid (aligning catalog metadata columns); `scrollbar-gutter: stable`; `content-visibility: auto` (catalog rows).

SKIP: scroll-driven animations (scroll-jacking reads as slop), CSS scroll snap (fights code reading), `field-sizing` (no forms).

## Svelte 5 mapping (path A)

- `$state`: one root store: active view, trace id + step index, catalog filter + tab, wizard node, dialog target. No fractured local state for routing or filtering.
- `$derived`: filtered catalog rows, current trace step, wizard result recipe.
- `$effect`: hash sync both directions; `localStorage` persistence.
- `transition:`/`animate:flip`: catalog filtering, recipe open flash. All non-player animations <= 200 ms.
- `{#snippet}`: code block, badge, table row, SVG node templates.

## Determinism guardrails

REQUIRE: all content from `solution.json`; one root state object; native elements (`<dialog>`, `<details>`, `<input>`, `<select>`) before ARIA re-implementations; inline SVG only; keyboard path for every mouse path; optional data (`capabilities`, `challenges`, `onboarding_path`) renders only when present, never as an empty shell; `validate.mjs` green before every build; final file verified offline.

FORBID: `fetch`/XHR/any network reference in dist (`<script src>`, `<link href>`, `@import url`, web fonts, images); UI/CSS frameworks and component libraries; diagram/chart libraries (Mermaid, D3, Chart.js); SvelteKit; raster images of any kind; inline `onclick="..."` strings (path B uses delegated `addEventListener`); JS-computed colors (CSS variables + `color-mix()` only); content invented at SPA-build time that is not in `solution.json`.

## Anti-slop gate (all must pass before delivery)

1. Max 5 font sizes in the CSS.
2. Zero gradients.
3. Zero `box-shadow` outside `<dialog>`/popover.
4. Zero `border-radius` > 6 px.
5. Exactly one accent custom property.
6. No animation/transition > 200 ms except the trace player pulse.
7. Every interactive element has `:focus-visible`.
8. All spacing values from the 4/8/16/24/32/48 scale.
9. Zero external requests in dist (grep the file for `http://`, `https://`, `src=`, `@import`).
10. Text contrast >= 4.5:1 in both schemes.
11. Icons: one inline SVG set, `currentColor`, no emoji glyphs as UI.
12. Code blocks scroll horizontally, never wrap.
13. Numeric table columns right-aligned, `tabular-nums`.
14. No card grids for data lists; >5 items means a table or bordered rows.
15. `prefers-reduced-motion` honored (no pulse, no smooth scroll).
16. `<title>` is "<Solution> Explorer"; footer shows system, generated date, object count, coverage from `meta`.
17. Deep link to a recipe and an object survives a full reload from `file://`.
18. Dist size <= 1.5 MB (over budget: shorten recipe code samples, never remove views).
19. Tour, palette, and dialogs close on Esc and never trap focus.

Orientation and honesty (the regressions this rewrite exists to stop — each is pass/fail on the built file):
20. Default route is `#/overview`; its first rendered block is the hero + `onboarding_path` checklist, NOT a layer list or edge table.
21. `onboarding_path[]` present in data ⇒ rendered as a checklist on Overview; absent ⇒ the section is gone, never an empty shell.
22. No raw dependency-edge table on Overview.
23. Lifecycle control bar (`|◀ ◀ · X/N · ▶ ▶|` + scrubber) sits ABOVE the step list and is visible without scrolling; `←`/`→` step; advancing does not move the page (`window.scrollY` unchanged across a step).
24. Every link target is checked against `objects[]`; unmapped targets render muted+dashed, never as live links to blank pages.
25. Both light and dark render intentionally (no hardcoded single-scheme palette); `/` and `Ctrl+K` both open the palette.
26. Placeholder/template code is visually marked (dashed `--warn` + label); real banked code names its source object. The two never look identical.
27. `meta.coverage_pct < 100` ⇒ persistent partial-coverage banner naming unread domains.
28. Every code block is syntax-highlighted — Shiki at build time (path A) or the regex ABAP tokenizer (path B): keywords, comments, and string literals render in visibly distinct colors in BOTH schemes. A monochrome `<pre>` dump fails this gate; unhighlighted ABAP is unreadable at recipe length and the single most common reason the explorer goes unused. (Observed failure: all recipe code shipped as plain text.) Code also renders inside `<pre>` (or an element with `white-space: pre`) so linebreaks and indentation survive — ABAP collapsed onto one line by normal HTML whitespace handling fails this gate; the canonical stylesheet's `pre` rules provide this for free. (Observed failure: code blocks without linebreaks.)
29. The canonical `assets/explorer.css` is embedded unmodified as the first stylesheet — its `abapx-style v1` marker comment is present in the built file, its tokens unaltered, view-specific CSS only appended after it. Re-derived or restyled chrome fails this gate even if it looks nice: cross-run consistency IS the requirement.
30. Object dialogs open via `showModal()` and appear centered over a dimmed backdrop — a dialog pinned to a screen corner fails.

## Verification checklist (Phase 6 hook)

Open `dist/explorer.html` via `file://`, offline, and confirm each — a newcomer's path first:
- **Overview lands as a curriculum:** hero + `onboarding_path` checklist visible immediately; no edge table; coverage banner present when partial. A first-time reader can say what the solution is and what to read first without scrolling into architecture.
- **Lifecycle stepper:** control bar visible above the steps; `→` and Next advance without moving the page; the active step and the Next control are on screen together; scrubber jumps steps; narrow width stacks without breaking.
- Catalog filter narrows on each keystroke; a row dialog resolves its edges; an unmapped/standard edge is muted, not a live link to a blank page.
- Cookbook wizard reaches a recipe and opens it; recipe shows a real source object; any template code is visibly marked.
- Code blocks show real syntax colors in both schemes (open a recipe: keywords/comments/strings visibly distinct — not monochrome text).
- Click a catalog row: the object dialog opens CENTERED with a dimmed backdrop (not corner-pinned) and closes on Esc.
- The built file contains the `abapx-style v1` marker and the chrome visibly matches the canonical stylesheet (top nav with accent underline, bordered tables, badge colors).
- Command palette opens on both `/` and `Ctrl+K` and finds an object, a recipe, and a glossary term; tour shows once; ticks/visited survive reload; print preview of Reference is one clean page; both color schemes look intentional; anti-slop gate (all 30) re-checked on the built file.

If browser automation is available, run this there and screenshot Overview and Lifecycle at minimum; otherwise hand it to the user as a click-through list. Any failed item is a build bug, fixed before delivery — not a known limitation to note.
