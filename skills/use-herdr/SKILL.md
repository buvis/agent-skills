---
name: use-herdr
description: Use when operating Herdr spaces, tabs, worktrees, terminals or agents, or customizing its layouts and mods. Triggers on "use herdr", "open worktree in herdr", "herdr-app", "herdr-core".
---

# Use Herdr

Operate the installed Herdr version using its own documentation, then apply
the observations below.

## Dependencies

- `herdr-app` and its home directory: required for window operations. Default
  home is `~/.config/herdr-app`; honor `HERDR_APP_HOME`. If unavailable, report
  the missing component; do not claim the window changed.
- `hc`: required for terminal inspection and orchestration; read `hc --skill`
  before using it. A failed `mise which hc` alone does not prove it is absent:
  check PATH and the installed Herdr guide.
- Git: required for worktrees. Without it, report the blocker.

## Start here

1. Read `AGENTS.md` in the active Herdr home first. It is generated on startup;
   never edit it or the adjacent generated `.d.ts` files.
2. Run `herdr-app --skill`, then `herdr-app commands`, `herdr-app ls`, and
   `herdr-app status`. Inspect existing IDs, folders and machine before acting.
   Bare `herdr-app` opens the app; it is not an inspection command.
3. Use `herdr-app do` for visible structure; use `hc` for running, reading,
   sending to and waiting on terminals. Neither a window request nor loading
   this skill authorizes starting agents or implementing their tasks.

## Choose the right object

- For repository work, a space represents a checkout. A tab holds work inside it.
- For opening or creating worktrees, read
  [references/worktrees.md](references/worktrees.md). Create/select a separate
  **space per worktree**; tabs in the original space do not produce the
  worktree entries the user expects in the sidebar.
- Reuse matching spaces instead of duplicating them. Pass explicit folders
  and target IDs; names and creation folders can differ from live terminal
  folders. Remote spaces require operations on their machine.
- Follow the installed `hc --skill` for terminal lifecycle, task delivery and
  status. Preserve the user's launcher and model choices; Codex under hc
  requires `--no-daemon`. Check task delivery and read actual results before
  reporting completion. Do not stop another session's terminals or restart
  the app/core without authorization.

## Customization and verification

Read the relevant generated types and current mod source before changing a
layout or mod. Clone shipped files first: startup replaces them, while clones
remain user-owned and do not receive upstream updates automatically.

After a mod edit, run `herdr-app check <mod-folder>`, inspect `status`, and
exercise the changed state in the app. A passing check does not cover later
async states or prove the layout renders correctly. Capture `herdr-app shot`
to a temporary PNG and inspect it for visual changes.

After structural commands, verify `ls`/`status` and the relevant terminal
folder through hc. A successful launch response proves creation only. Report
separately what exists on disk, what is visible, and any unfinished step.
