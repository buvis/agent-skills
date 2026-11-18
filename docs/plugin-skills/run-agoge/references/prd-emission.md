# PRD emission

How an accepted finding becomes a backlog PRD. Read this at step 9, after a
human has accepted something, and never before.

## The gate

**Only explicit per-finding acceptance emits anything.** Deferred and rejected
findings stay in the report and nowhere else. An unattended run emits nothing at
all, whatever it found — a machine that files its own findings as work has
approved them on the operator's behalf, which is the one thing this pack must
not do.

One PRD per accepted finding, or one per cluster the human explicitly approved
as a cluster. Never bundle on your own initiative: the human accepted findings,
not a grouping.

## Claiming the number

Numbers are claimed, not chosen. The claimer is `allocate_prd_number.py`, which
ships in the agoge plugin:

```bash
python3 "<agoge-plugin-root>/skills/run-agoge/scripts/allocate_prd_number.py" /absolute/target/repo <kebab-slug>
```

**Check that the path resolved before trusting it.** Substitute the absolute
directory the agoge plugin was loaded from; a half-substituted path becomes
`/skills/run-agoge/scripts/...` and fails. Without the plugin the script is
absent: say so and stop. Do not fall back to picking a number yourself, because
that is the one thing this script exists to prevent.

It scans every `docs/dev/project-management/prds/` lifecycle directory plus `docs/dev/project-management/discovery/`,
creates an **empty** file at the next free number with an exclusive create, and
prints the path. Write the body into that path.

Do not compute the number yourself and do not re-scan afterwards. The exclusive
create is what makes two concurrent writers impossible to reconcile wrongly: one
of them gets the name, the other moves on. A scan-then-write has a window; this
does not.

The slug comes from the finding's title: lowercase, words joined by hyphens, no
articles, five words at most. `A book added through the form never appears in the
catalogue` becomes `added-book-missing-from-catalogue`.

## The PRD shape

An emitted PRD is usually drained by an unattended autopilot loop. That loop
parses the literal headings of create-prd's `minimal.md`, and nobody is there to
answer a question. So the PRD takes this shape, with the headings in this order
and worded exactly like this. `## Test Strategy` is agoge's own addition and
carries the evidence. If the target repo has its own PRD template, use that one
instead and fill it from the same sources.

````markdown
---
design: skip
default_model: sonnet
model_tier_rationale: <one line: why this tier>
---
# <the finding's title, as a problem, not a solution>

Source: agoge run <YYYY-MM-DD>, finding <n> of <total> (<severity>, <status>, lane <lane>), `<report path>`.

## Problem

<the packet's what plus its if-unchanged: the symptom and the cost of leaving it>

## Solution

<the chosen option as exact behaviour: names, kinds, messages, formats, exit codes>

## Requirements

### Must have
- <each observation that must flip, checkable by a command or test>
- <the CHANGELOG line, when the target keeps one>

### Nice to have
- None.

## Implementation

### Module: <short name>
- **Location**: <every file a task touches, repo-relative, no globs>
- **Responsibility**: <one line>
- **Exports**: <changed or new public names, or none>
- New symbols: `<new test function>`, `<new function or constant>`
- **Risk**: <the chosen option's drawback and what the change could break>

### Dependencies
- <short name>: No dependencies (foundation)

## Test Strategy

<the regression check, then the finding's evidence verbatim:>

```
<the reproduction as it ran>
```

## Tasks

### Phase 0: Fix
- [ ] Add `<test name>`; watch it fail - Acceptance: `pytest -k <filter>` fails on the unmodified code.
- [ ] <the change> (depends on: previous task) - Acceptance: `pytest -k <filter>` passes.

## Success Criteria

- `pytest -k <filter>` passes; the project's full test gate passes.
````

Fill it like this:

- **Title, Problem and Source line.** These come from the finding's `title` and
  its *what* and *if unchanged*. The Source line names the run, so whoever picks
  the PRD up can find where it came from.
- **Solution.** Write the packet's **recommended option**, or the one the human
  chose. Be exact wherever a test will check it: violation kinds, message text,
  output formats, thresholds. The test author sees only the task line, so a
  contract that reads two ways becomes a wrong test.
- **Location.** Use the finding's `paths` plus every test file and the CHANGELOG
  the tasks touch. Write each path repo-relative, never as a glob.
- **Tasks.** Use one phase unless the chosen option names more. Every task line
  ends with `Acceptance:` and a runnable check: a named test, a `pytest -k`
  filter, or an `rg` against a named file. Never write a manual check. Never use
  a line number or a test count, because neighbouring PRDs move them. Name
  every new test, and list it on the `New symbols:` line.
- **Success Criteria.** This is the only place the full test gate appears.
- **Test Strategy.** Put the finding's `evidence` here **verbatim**, in a fenced
  block. This matters more than anything else in the mapping, because the
  evidence is a reproduction someone already ran. A PRD that says "the API
  returns an empty list" is a claim. One that carries the `curl` and its
  two-byte body is a reproduction the implementer can run before writing a line.
  If the evidence is `mocked`, say so, and say where the real check can run.
- **Frontmatter.**
  - Set `default_model: opus` for concurrency, an invented algorithm or
    predicate, or a byte-level or cross-module contract.
  - Set `sonnet` when every task carries exact text and every check fails
    loudly.
  - Drop `default_model` (keep the rationale) for a one-token fix or a docs-only
    change.
  - Write no comment on the `default_model:` line.

## After writing

State in the report's minutes, on the finding's line, that a PRD was emitted and
under which number. A finding whose minutes say "accepted" with no number is a
finding that was lost between the walkthrough and the backlog.

Emitted PRDs are ordinary backlog PRDs from that moment on. Whatever backlog
review the repo runs applies to them like any other, and nothing about their
origin exempts them from it.
