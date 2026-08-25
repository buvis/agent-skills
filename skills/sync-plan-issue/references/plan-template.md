# Plan Summary Template

Based on Linear Method + Shape Up. Fill the template; drop optional sections when they don't apply.

```markdown
## Plan Summary

### Problem
{1-2 sentences: what's broken/missing and why it matters. One concrete scenario beats abstraction.}

### Appetite
{Scope constraint: "Small batch (1-2 days)", "Medium (3-5 days)", "Full cycle (1-2 weeks)", or custom. If longer, split.}

### Solution
{2-4 sentences: high-level approach and key technical decisions. Not implementation steps.}

### Scope
| Path | Change |
|------|--------|
| `src/path/file.ts` | {brief description} |

### Tasks
- [ ] {verb} {object}   # plain imperative, specific enough to verify done; 5-10 typical, order = dependency order

### Rabbit Holes
{Known risks, complexity, scope-creep temptations that could derail. Skip if none.}

### No-Gos
{Explicitly out of scope — features/edge cases/future work deliberately excluded. Skip if obvious.}

---
*Synced: {YYYY-MM-DD}*
```

## Rules

- **Problem first.** Without it you can't judge whether the solution is good.
- **Appetite constrains scope.** State the time budget to prevent gold-plating.
- **Tasks are deliverables, not stories.** Verb + object, concrete, verifiable.
- **No-gos prevent scope creep.** Name what you're deliberately not doing.

## Updating an existing issue

1. Body has `## Plan Summary` → replace that whole section. Match it with:
   ```
   ## Plan Summary.*?---\n\*Synced:.*?\*
   ```
2. No plan section → append after existing content with a `---` separator.
3. Preserve labels, assignees, milestone, and the original issue description.
