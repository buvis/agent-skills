---
default_model: sonnet
model_tier_rationale: exact replace expressions given, one additive smoke test
design: skip
---

# "Copy open as markdown" emits todo text unescaped, so a newline in an action injects a checklist line

## Problem

The clipboard export in `skills/brief-portfolio/app/src/components/Todos.svelte`
(about line 67) interpolates each open todo's `repo` and `action` into a markdown
checklist with no escaping. An `epics.json` action containing `\n- [ ] ...`
becomes its own checklist line in the pasted text, and
`[click me](javascript:...)` survives as a link. Needs a hostile `epics.json`.
Source: agoge run `dev/local/audit-results/agoge-2026-09-05.md`, finding 21
(LOW, security lane, status mocked: stubbed clipboard in jsdom); decision
2026-09-05: collapse whitespace and escape brackets.

```
Stubbed navigator.clipboard.writeText captured "- [ ] demo/repo: MARK_A2 line
one" then "- [ ] MARK_INJECTED_LINE injected todo" as a separate line, 35
lines total for 34 open todos.
```

## Solution

Before interpolating, normalise the action with
`action.replace(/\s+/g, ' ').replace(/[\[\]]/g, '\\$&')` after first escaping literal backslashes. Preserve the current clipboard
format `- [ ] <repo>: <action>`; this PRD adds no URL suffix. One line per open todo,
always. Intentional formatting inside an action is flattened; that was the
option's named drawback.

## Requirements

### Must have

- The copied markdown has exactly one line per open todo.
- Square brackets in an action are escaped; whitespace runs collapse to one
  space.
- Existing backslashes are escaped before brackets, so they cannot cancel
  the added escaping. Preserve the current repo/action-only format.

### Nice to have

- none

## Implementation

### Module: Todos.svelte

- **Location**: `skills/brief-portfolio/app/src/components/`
- **Responsibility**: Build the clipboard text from sanitised fields.
- **Exports**: component, props unchanged

### Module: smoke.todos.test.js

- **Location**: `skills/brief-portfolio/app/`
- **Responsibility**: Pin the line count under a hostile action.
- **Exports**: `node --test` cases

### Dependencies

- Todos.svelte: No dependencies (foundation)
- smoke.todos.test.js: Depends on [Todos.svelte]

## Tasks

### Phase 0: Foundation

- [ ] Sanitise `action` in the clipboard builder, then rebuild (`npm --prefix skills/brief-portfolio/app run build`) and copy the template (`cp skills/brief-portfolio/app/dist/index.html skills/brief-portfolio/assets/template.html`) - Acceptance: a new smoke test `copy open as markdown emits exactly one line per open todo whatever the action contains` stubs `navigator.clipboard.writeText`, mounts an epics.json todo whose action is `"line one\n- [ ] injected todo [x](javascript:1)"`, clicks the copy button, and asserts the captured text has as many lines as open todos and that `injected todo` stays on the same line with the action's brackets escaped; a pre-existing backslash-before-bracket case asserts the exact escaped output; `npm --prefix skills/brief-portfolio/app test` reports 0 failing.

### Phase 1: Core

- none

## Success Criteria

- The new smoke test passes; the existing copy-button tests pass unchanged.
- The report's reproduction yields one line per open todo, whatever the execution-time fixture count.
