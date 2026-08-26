---
name: web-performance
description: Use when optimizing web performance - Core Web Vitals, bundle budgets, loading strategy, images, and fonts. Triggers on .css/.svelte/.ts/.tsx/.jsx/.html/.vue file edits, "core web vitals", "lighthouse", "bundle size", "LCP", "CLS", "web performance".
compatibility: "Portable standalone compatibility copy of the strunk plugin skill for agents without that plugin; Claude Code uses the namespaced plugin skill."
---

# Web Performance

Pick a side. These are the rulings, not a tutorial.

## Targets

| Metric | Target |
|--------|--------|
| LCP | < 2.5s |
| INP | < 200ms |
| CLS | < 0.1 |
| FCP | < 1.5s |
| TBT | < 200ms |

## Bundle budget (gzipped)

| Page type | JS | CSS |
|-----------|-----|-----|
| Landing page | < 150kb | < 30kb |
| App page | < 300kb | < 50kb |
| Microsite | < 80kb | < 15kb |

## Loading

1. Inline critical above-the-fold CSS where justified.
2. Preload the hero image and the primary font — nothing else.
3. Defer non-critical CSS and JS.
4. Dynamically `import()` heavy libraries.

## Images

Explicit `width` and `height` on every image. `loading="eager"` + `fetchpriority="high"` for hero media **only**; `loading="lazy"` below the fold. Prefer AVIF or WebP with fallbacks. Never ship a source image far beyond its rendered size.

## Fonts

Max two families unless there is a clear exception. `font-display: swap`. Subset where possible. Preload only the truly critical weight and style.

## Animation

Compositor-friendly properties only. Use `will-change` narrowly and remove it when done. CSS for simple transitions; `requestAnimationFrame` or an established library for JS motion. Never churn a scroll handler — use `IntersectionObserver`.

## Checklist

- [ ] Every image has explicit dimensions
- [ ] No accidental render-blocking resources
- [ ] No layout shift from dynamic content
- [ ] Motion stays on compositor-friendly properties
- [ ] Third-party scripts load async/defer, and only when needed
