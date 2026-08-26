---
name: web-patterns
description: Use when building framework-agnostic web UI - CSS, semantic HTML, component composition, state, and data fetching. Triggers on .css/.svelte/.ts/.tsx/.jsx/.html/.vue file edits, "css units", "web patterns", "component composition", "url state".
compatibility: "Portable standalone compatibility copy of the strunk plugin skill for agents without that plugin; Claude Code uses the namespaced plugin skill."
---

# Web Patterns

Framework-agnostic web craft. Pick a side. These are the rulings, not a tutorial.

> Svelte 5 / SvelteKit specifics live in `frontend-patterns`; tokens, visual audits and slop checks in `apply-design-system`; Core Web Vitals and budgets in `web-performance`.

## CSS

| Rule | Why |
|------|-----|
| **Never use px for sizing** | font-size, padding, margin, width, height, border-radius — all `rem` on a 16px base (4px = 0.25rem, 8px = 0.5rem, 16px = 1rem). px is acceptable only for border-width, box-shadow offsets, and media-query breakpoints. |
| Design tokens are CSS custom properties | Palette, type scale, spacing, duration and easing defined once in `:root`. Never repeat a raw value. |
| Animate compositor-friendly properties only | `transform`, `opacity`, `clip-path`, `filter` (sparingly). Never animate `width`, `height`, `top`, `left`, `margin`, `padding`, `border`, `font-size` — they hit layout. |

Notification badges: wrap icon and badge in a `position: relative` inline-block container, then `position: absolute; top: 0; right: 0; transform: translate(40%, -20%)` on the badge.

## Semantic HTML

`<header>`, `<nav aria-label="...">`, `<main>`, `<section aria-labelledby="...">`, `<footer>`. Never a generic wrapper `div` stack where a semantic element exists.

## Organization and naming

Organize by feature or surface area, not by file type — `components/hero/`, `components/scrolly-section/`, `stores/`, `actions/`, `styles/tokens.css`.

- Components: PascalCase filenames (`ScrollySection.svelte`)
- Stores: camelCase (`reducedMotion`, `scrollProgress`)
- Actions: camelCase with a verb (`clickOutside`, `trapFocus`)
- Animation timelines: camelCase with intent (`heroRevealTl`)
- CSS classes: kebab-case or utility classes

## Composition

- **Compound components** when related UI shares state and interaction semantics (`<Tabs>` / `<Tabs.List>` / `<Tabs.Trigger>`): the parent owns state, children consume via context. Beats prop drilling for complex widgets.
- **Render props / slots** when behaviour is shared but markup must vary. Keyboard handling, ARIA and focus logic stay in the headless layer.
- **Container / presentational split**: containers own data loading and side effects; presentational components take props and stay pure.

## State

| Concern | Tooling |
|---------|---------|
| Server state | TanStack Query, SWR, tRPC |
| Client state | Zustand, Jotai, signals |
| URL state | search params, route segments |

- **Never duplicate server state into a client store.**
- **Derive values; never store redundant computed state.**
- **URL-as-state** for anything shareable: filters, sort order, pagination, active tab, search query.

## Data fetching

- **Stale-while-revalidate**: return cached data immediately, revalidate in the background. Use an existing library; never roll this by hand.
- **Optimistic updates**: snapshot, apply, roll back on failure, and show a visible error when you do.
- **Parallel loading**: fetch independent data concurrently. No parent-child request waterfalls. Prefetch the likely next route or state when it is justified.
