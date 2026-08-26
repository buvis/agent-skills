---
name: apply-design-system
description: Use when generating design tokens, scoring visual consistency, or catching generic AI-design slop. Triggers on .css/.svelte/.ts/.tsx/.jsx/.html/.vue file edits, "design system", "design tokens", "visual audit", "UI scoring", "slop check".
compatibility: "Portable standalone compatibility copy of the strunk plugin skill for agents without that plugin; Claude Code uses the namespaced plugin skill."
---

# Apply Design System

Pick a side. These are the rulings, not a tutorial. Framework-agnostic — the visual half that `frontend-patterns` (Svelte specifics) leaves open. Three jobs: generate a token set, audit a UI, or catch AI slop.

## Generate

| Rule | Why |
|------|-----|
| Extract before you invent | Read existing CSS/Tailwind/styled-components first; the codebase is the source of truth, not your taste. |
| One scale per axis | Spacing on a 4px/8px step, type on a modular scale. No arbitrary values. |
| Name by role, not value | `--color-surface`, not `--color-gray-100`. Values change; roles don't. |
| Ship three artifacts | `design-tokens.json`, CSS custom properties, and a `DESIGN.md` stating the rationale for each decision. |

Competitor research is optional, not a gate. Use a browser MCP if one is present; when none is available, work from the codebase and the brief alone — never block on a tool that isn't there.

## Audit

Score each axis 0-10. Every score cites a `file:line` example as evidence; a score without one is an opinion, not an audit. Anything below 8 also ships an exact fix.

The axes that earn their keep:

- **Token adherence** — your palette and scale, or scattered hex and magic numbers?
- **Type hierarchy** — clear h1 > h2 > body > caption, or flat?
- **Spacing rhythm** — one scale, or arbitrary gaps?
- **Component consistency** — do similar elements look similar?
- **Responsive integrity** — fluid, or broken at breakpoints?
- **State coverage** — hover, focus, loading, empty, error all handled?
- **Accessibility** — contrast ratios, focus rings, touch targets.

## Slop check

Flag and kill the generic AI-design tells:

- Clichéd colour schemes — the purple-to-blue gradient on white above all.
- Glassmorphism cards with no depth purpose.
- Rounded corners on elements that read as flat (tables, code blocks).
- Scroll-triggered animation that delays the content.
- Centered hero text over a stock gradient.
- A personality-free sans stack picked by default.
- Default card grids: uniform spacing, no hierarchy.
- Unmodified library defaults passed off as finished design.
- Flat layouts with no layering, depth, or motion.
- Uniform radius, spacing, and shadows across every component.
- Dashboard-by-numbers: sidebar + cards + charts with no point of view.
- Safe gray-on-white with one decorative accent colour.

## Required qualities (at least 4 of 10)

Every meaningful surface demonstrates **at least four**:

1. Hierarchy through scale contrast. 2. Intentional spacing rhythm, not uniform padding. 3. Depth via overlap, shadow, surface, or motion. 4. Typography with a real pairing strategy. 5. Colour used semantically, not decoratively. 6. Hover/focus/active states that feel designed. 7. Grid-breaking editorial or bento composition where it fits. 8. Texture, grain, or atmosphere when it suits the direction. 9. Motion that clarifies flow. 10. Data visualisation treated as part of the system.

Fewer than four is a fail, not a style opinion.

## Before writing frontend code

Pick a specific style direction — "clean minimal" is not one. Worth considering: editorial/magazine, neo-brutalism, glassmorphism with real depth, dark or light luxury with disciplined contrast, bento, scrollytelling, 3D integration, Swiss/International, retro-futurism. **Do not default to dark mode** — choose what the product wants.

Define the palette deliberately. Choose type deliberately: **not Arial, Inter, or Roboto**. Every token is a CSS variable.

Ship checklist: does it avoid looking like a default Tailwind or shadcn template? Are hover/focus/active states intentional? Is there hierarchy rather than uniform emphasis? Would it look believable in a real product screenshot? If both themes exist, do both feel intentional?
