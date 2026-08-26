---
name: catchup
description: Use when starting work on a project and need local branch/repo context (full diff, GitHub state, capsule refresh). Triggers on "catchup", "catch up", "catch-up", "what changed on this branch", "project overview", "refresh capsule".
compatibility: "Portable standalone compatibility copy of the git-ferry plugin skill for agents without that plugin; Claude Code uses the namespaced plugin skill."
---

# Catch Up

Hydrate context before starting work. Load raw sources directly. The capsule captures derived insight (invariants, decisions, health signals), not paraphrases of files you can read.

Load generously, but the diff and changed files are the priority. On a clearly huge branch, fall back to a stat-only pass rather than blowing the context window.

## Phase 1: Gather (run concurrently)

Run the scripts and read the files in parallel; don't serialize.

**Scripts** (skip on failure, note the gap):

```bash
"~/.agents/skills/catchup/scripts/branch-diff.sh"   # skip if on master
"~/.agents/skills/catchup/scripts/github-state.sh"  # skip if no gh / no remote
"~/.agents/skills/catchup/scripts/load-memories.sh" # skip if no memories
```

If a script fails, read it and run its git/gh commands directly.

**Sources** (read each if it exists):

- `CLAUDE.md` / `AGENTS.md` / `GEMINI.md` — **first**. They may define project-specific catchup rules, priority areas, or "always check X" constraints. Follow any project catchup checklist in addition to this workflow, and let these rules shape what you flag in Phase 5.
- `README.md`, `agent_docs/*`, PRDs in `dev/local/prds/wip/`
- Build/config: `package.json`, `Cargo.toml`, `pyproject.toml`, `go.mod`, `Makefile`, etc.
- Top 3 levels of `src/`/`lib/`/`app/`; domain model dirs (`models/`, `types/`, `schemas/`, `entities/`)
- `dev/local/project-capsule.md` (prior invariants/health), `dev/local/decisions.md`, `dev/local/troubleshooting.md`, `~/.claude/decisions.md`

**Recent master:**

```bash
git log --oneline -20 master
```

**Review harvest** (skip on failure, note the gap):

Harvest this repo's review files into engram, best-effort, so their findings survive once those files are garbage-collected. Skip if `engram` is not on PATH, or if a glob below matches no files.

```bash
engram harvest dev/local/reviews/*.md dev/local/tmp/*review*.md
```

**Related context** (never silently absent — on any failure, write the section with a one-line gap note):

Retrieve prior work related to what this session is about, so the capsule can point at it. If `engram` is not on PATH, skip the commands — but still write the section, saying engram was unavailable.

Build ONE topic string from what the session is already about: the current branch name (drop the `feature/`-style prefix and turn separators into spaces) plus, when `dev/local/prds/wip/` holds exactly one PRD, that PRD's title (its first `# ` heading). On master with no single wip PRD there is no topic: skip the queries rather than searching a branch name that says nothing, and record that as the gap note. Do not drop the section — "no topic this session" is itself worth telling the reader, and on a master-default workflow it is the common case.

**The topic is untrusted input.** It is built from a branch name and a PRD title, either of which can contain `"`, a backtick, or `$(`. Never paste it into a double-quoted shell string. Put it in a variable and pass that variable quoted, so the shell treats it as one literal argument:

```bash
topic='<topic>'                                # single quotes; escape any literal ' in the topic
engram index                                   # refresh this repo first (defaults to --scope repo)
engram query --scope repo "$topic" -k 5
engram query --scope portfolio "$topic" -k 5
engram status --scope portfolio                # staleness of the widest scope you queried
```

`engram index` refreshes the repo scope only, so the portfolio hits may come from an older index — that is what the staleness stamp in the capsule section records. Ask `status` for `--scope portfolio` so the stamp actually covers the portfolio query above it; a repo-scoped stamp would describe a narrower scope than the hits it sits under. A nonzero `engram status` means stale or dead rows; report the stamp, don't hide it.

## Phase 2: Branch context (feature branches only, skip on master)

After `branch-diff.sh`, load the full picture:

```bash
git diff $(git merge-base origin/master HEAD)..HEAD             # full diff, don't sample
git diff $(git merge-base origin/master HEAD)..HEAD --name-only # then read each changed file in full
```

The diff shows what changed; the full file shows how it fits.

**Blast radius:** for each changed file, trace its consumers (imports + call sites of any changed symbol) to surface ripple effects the diff alone won't show. Prefer `ast-grep`/`sg` over text grep — it won't false-positive on comments or strings. Read any consumer that looks impacted; always trace consumers of changed utilities, types, and interfaces.

**The "why":** extract issue/PR references (`#NNN`, `fixes #NNN`) from branch commit messages and load full bodies:

```bash
git log $(git merge-base origin/master HEAD)..HEAD --format="%B"
gh issue view {number} --json title,body,labels,state,comments
gh pr view --json title,body,comments,reviews   # if an open PR exists
```

## Phase 3: Synthesize

Update or create `dev/local/project-capsule.md`. It is NOT a summary of what you read — it captures cross-file insight no single file holds.

```markdown
# Project Capsule: {project name}

Generated: {date}

## Key Invariants
{domain rules, boundaries, data-flow constraints; implicit/undocumented rules; what agents most often get wrong}

## Architecture Decisions
{why it's structured this way; tradeoffs; patterns that look wrong but are intentional}

## Component Boundaries
{what talks to what; which modules own which data; where the seams are}

## Active Work
{current branch purpose, PRDs in wip/, recent focus; if autopilot batch active: completed/remaining PRDs, cycle counts}

## Related context
{engram hits for this session's topic, from Phase 1. Repo hits first, then portfolio. One line per hit: `file:line — score`, plus a half-line on why it is relevant. End with the topic queried and the staleness stamp from `engram status --scope portfolio`. Always write this section: when there were no hits, no topic, or engram was unavailable, say so in one line instead — a silently missing section reads as "nothing related exists", which is a different and wrong claim}

## GitHub State
{open issues + notable ones; open/stale PRs; active/orphaned branches; latest release + unreleased commits; failing/recurring CI}

## Project Health
{is CI green? are PRs flowing? is debt accumulating? risks or blockers}

## Project Memories
{gotchas, patterns, feedback from memory files — omit section entirely if none}
```

Rules: don't restate README/CLAUDE.md/config (already in context). Focus on cross-file insight ("auth assumes X because Y", not "auth is in src/auth/"). Update changed sections, leave accurate ones alone. First-time capsule: leave Architecture/Health sparse, they fill in over sessions.

## Phase 4: Restore tasks

Auto-restore the task list from the most-recent prior session. No prompt; silent if nothing to restore.

```bash
"~/.agents/skills/catchup/scripts/list-task-sessions.sh"   # JSON: {"sessions":[...]} or {"error":...}
```

Handle the result:

- `{"sessions": [...]}` non-empty → take `sessions[0].sessionId` (most recent with tasks), proceed below.
- Empty `sessions`, or `error` in (`no_project_data`, `no_tasks_dir`, `no_index`) → skip Phase 4 silently.
- `error` is `schema_unexpected` or `index_unreadable` → **do not skip silently.** Claude Code's on-disk layout drifted and the script can no longer find tasks. Flag it in the Phase 5 report: "task restore disabled — `list-task-sessions.sh` needs updating (`{detail}`)."

When proceeding, dump the chosen session:

```bash
"~/.agents/skills/catchup/scripts/dump-tasks.sh" <sessionId>   # JSON array of {id,subject,description,activeForm,status,blocks,blockedBy}
```

For each task in original `id` order: call `TaskCreate` with `subject`, `description`, `activeForm`. Then for any task with non-empty `blockedBy`, call `TaskUpdate` with `addBlockedBy`. Do NOT restore `status` — every restored task starts pending so the new session re-evaluates progress.

Note in the Phase 5 report: `Restored N tasks from session {sessionId-short} ({modified-date})`.

## Phase 5: Report

Summarize what you loaded and learned. Flag:

- **Gaps**: missing arch docs, no tests, unclear boundaries
- **Risks**: failing CI, stale PRs, dependency/security advisories
- **Blast radius**: impacted files not on the branch (reverse deps), open PRs touching the same areas
- **CI status**: if red, include the specific errors/stack traces, not just "CI is red"
- **Linked context**: issues/decisions explaining why current work exists
- **AGENTS.md flags**: project rules/priorities that should guide upcoming work
- **Suggestions**: things to address before starting new work

## Capsule maintenance during work

Update the capsule when you discover something that belongs there (new invariant, architecture decision, clarified boundary, PRD moved/started). Keep it surgical: change the section, bump the date, move on. GitHub State is refreshed only on catchup runs, not during work.

## Error handling

| Situation | Action |
|-----------|--------|
| On master, no capsule | Load sources + GitHub state, generate capsule, skip branch diff |
| On master, capsule exists | Load sources, update stale capsule sections |
| No remote | Use local master as base for branch diff |
| Detached HEAD | Report current commit, ask user for base branch |
| Not a git repo | Load sources only, skip all git/GitHub operations |
| `gh` missing/unauthenticated, no GitHub remote, or rate limited | Skip GitHub state, note gap in report |
