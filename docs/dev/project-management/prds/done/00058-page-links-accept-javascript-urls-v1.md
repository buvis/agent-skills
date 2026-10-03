---
default_model: sonnet
model_tier_rationale: exact helper expression and sink list given, additive smoke tests
design: skip
---

# Page links accept javascript: and data: URLs verbatim from data.json and epics.json

## Problem

Six `href={...}` sinks in the brief's Svelte app take `url` straight from
`data.json` (GitHub's `html_url` on issues, PRs, workflow runs and alerts) and
from `epics.json` (todos the model writes from third-party commit subjects) with
no scheme check, so a hostile value becomes a clickable `javascript:` or `data:`
link on the Todo, Work and RepoDetail tabs. GitHub never returns such URLs; the
realistic path is an `epics.json` written by a model that followed a commit
subject (report finding 23), and this fix removes that payoff. Modern browsers
neuter both schemes on `target=_blank` links, so impact is bounded. Source: agoge
run `dev/local/audit-results/agoge-2026-09-05.md`, finding 5 (MEDIUM, security
lane, status mocked: jsdom mount, confirmed attribute value, suspected impact);
decision 2026-09-05: one `safeUrl` helper in `derive.js` applied at every sink,
plus a hostile-payload smoke test.

```
jsdom mount of a shim-built page, Todo tab:
{"href":"javascript:window.__m=1","protocol":"javascript:"} from a workflow
html_url and again from an epics.json todo; Work tab: protocol "data:".
```

## Solution

Export `safeUrl(u)` from `skills/brief-portfolio/app/src/lib/derive.js`:
`return typeof u === 'string' && /^https?:\/\//i.test(u) ? u : undefined`.
Apply it after every object spread where `derive.js` assigns `url` onto derived
todos, including manual and external entries, and wrap the raw
`href` sinks in `Work.svelte`, `Todos.svelte`, `Matrix.svelte` and
`RepoDetail.svelte` with it, so an anchor with no safe URL renders as text (the
components' safe-URL branch must render plain text for rejected values).
Include Brief's window.open consumer of derived todos: a rejected manual URL
must never reach it. Inputs use the collector's normalized url schema, not
GitHub's raw html_url fields; keep an HTTP(S) positive control at each surface. A dropped URL
is not reported on the page: surfacing bad data was the option's named drawback
and was accepted.

## Requirements

### Must have

- `safeUrl` returns the input only when it starts with `http://` or `https://`
  (case-insensitive) and `undefined` otherwise, including for non-strings.
- No `href` in the built page carries a `javascript:` or `data:` value taken
  from `data.json` or `epics.json`.
- Every existing smoke test passes unchanged; the template is rebuilt and
  copied in the same task.

### Nice to have

- none

## Implementation

### Module: derive.js

- **Location**: `skills/brief-portfolio/app/src/lib/`
- **Responsibility**: Own URL policy for every derived link.
- **Exports**: `safeUrl()` plus today's exports

### Module: Work.svelte, Todos.svelte, Matrix.svelte, RepoDetail.svelte

- **Location**: `skills/brief-portfolio/app/src/components/`
- **Responsibility**: Render anchors only through `safeUrl`.
- **Exports**: components, props unchanged

### Module: smoke.work.test.js

- **Location**: `skills/brief-portfolio/app/`
- **Responsibility**: Mount a hostile payload and assert every anchor's protocol.
- **Exports**: `node --test` cases

### Dependencies

- derive.js: No dependencies (foundation)
- components: Depends on [derive.js]
- smoke.work.test.js: Depends on [derive.js, components]

## Tasks

### Phase 0: Foundation

- [ ] Add `safeUrl` to `derive.js` and apply it where `url` is assigned on derived todos - Acceptance: a new smoke test `safeUrl keeps http and https and drops every other scheme` asserts `safeUrl('https://a')` and `safeUrl('HTTP://a')` return their input and `safeUrl('javascript:1')`, `safeUrl('data:text/html,x')`, `safeUrl('')` and `safeUrl(undefined)` return `undefined`; `npm --prefix skills/brief-portfolio/app test` reports 0 failing.

### Phase 1: Core

- [ ] Wrap the raw `href` sinks in the four components with `safeUrl`, then `npm --prefix skills/brief-portfolio/app run build` and `cp skills/brief-portfolio/app/dist/index.html skills/brief-portfolio/assets/template.html` (depends on: Phase 0) - Acceptance: a new smoke test `no anchor on any tab carries a javascript: or data: URL from the payload` mounts a payload whose workflow `url`, external-PR `url`, security-alert `url` and an `epics.json` todo `url` are `javascript:window.__m=1` and `data:text/html,x`, clicks through the Todo, Work and Matrix tabs and opens one RepoDetail, and asserts every `a[href]` in the document has `protocol` equal to `https:` or `http:`; `npm --prefix skills/brief-portfolio/app test` reports 0 failing and the copied template is byte-identical to the successful build artifact. Run the hostile and allowed-URL controls against that built bundle; no assertion depends on minified function names.

## Success Criteria

- The two new smoke tests pass; every pre-existing smoke test passes unchanged.
- The report's reproduction, re-run against the rebuilt template, finds no
  anchor with protocol `javascript:` or `data:`.
