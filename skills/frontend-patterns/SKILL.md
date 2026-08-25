---
name: frontend-patterns
description: Use when building Svelte 5 / SvelteKit components. Covers runes, reactivity, data loading, forms, animations, and accessibility. Triggers on .svelte file edits, "svelte", "sveltekit", "runes".
compatibility: "Portable standalone compatibility copy of the strunk plugin skill for agents without that plugin; Claude Code uses the namespaced plugin skill."
---

# Frontend Patterns

Svelte 5 and SvelteKit. Pick a side.

## Runes

```svelte
let count = $state(0)
let doubled = $derived(count * 2)
$effect(() => { const id = setInterval(tick, 1000); return () => clearInterval(id) })
let { items, variant = 'default' }: Props = $props()
{#snippet header()}...{/snippet}  {@render header()}
```

- **Derive with `$derived`, never `$effect`.** Using `$effect` to compute state from state is the #1 Svelte 5 footgun — it cascades and desyncs. `$effect` is for side effects (DOM, subscriptions, timers) only.
- `$derived.by(() => {...})` when the computation needs a block, not an expression.
- No memoization helpers. Runes are fine-grained by default; `$derived` is your `useMemo`.
- Shared state: a class with `$state` fields (`export class Cart { items = $state([]) }`) reads cleaner than stores. Stores/context only when state must cross many component boundaries.
- Snippets replace slots. Reach for slots only for legacy interop.
- Debounce with two values (`query` + `debounced`) and a small `$effect`, not by debouncing inside the render path.

## Data loading

- Server `load` in `+page.server.ts` for data; **form actions with `<form method="POST" use:enhance>`** for mutations, not hand-rolled client `fetch` — reach for `superforms` once the form grows real validation. Native forms survive JS failures.
- Stream slow data by returning unresolved promises from `load` and awaiting them in `{#await}`.

## Performance & a11y (non-negotiable)

- Virtualize (`@tanstack/svelte-virtual`) past ~100 rows or tall items — reactivity alone won't save a giant list.
- Lazy-load heavy libs (charts, editors) via dynamic `import()` in an `$effect`; show a skeleton meanwhile.
- Modals: `role="dialog"` + `aria-modal="true"`, a `trapFocus` action (Tab wraps), Escape to close, `clickOutside`, and **restore focus** to the trigger on close. Save `previousFocus` before opening.
