---
name: handoff-session
description: Use when a session is ending or about to lose its context and the next agent session must continue from a pasted prompt. Triggers on "handoff", "hand off session", "continuation prompt", "wrap up session", "prepare next session".
---

# handoff-session

Turns what this session knows into one paste-ready continuation prompt for the
next session: state, work done, work ahead, and everything that exists only in
this conversation. Writes it to a file, shows it, and copies it to the system
clipboard on request.

## Dependencies

- `git` (external CLI): source of the State section. Outside a git repo the
  section says so and the rest proceeds.
- One clipboard CLI per OS (external, see step 5): `pbcopy`, `wl-copy`,
  `xclip`/`xsel`, or `clip.exe`. Missing: report which one and leave the file
  as the only copy; never feed the prompt to a shell command by other means.
- A yes/no question to the user (`AskUserQuestion` on hosts that have it, a
  plain question elsewhere). Unattended sessions skip the question and the
  clipboard step.

## Scope

Request-only: never fires on its own at session end or compaction. If the
request names the target host ("hand off to Codex"), write skill and tool
names for that host; otherwise stay host-neutral.

---

## Step 1 - Ground truth (run, do not recall)

```bash
git rev-parse --abbrev-ref HEAD
git status --short
git stash list
git log --oneline -15
```

Also list `dev/local/prds/wip/` and `dev/local/plans/` when they exist, and
the host's task list when it keeps one. If the project's verify command
(tests, lint, build) runs in under a minute, run it now; otherwise report the
last run with its time. A result not observed this session is "not run",
never "passing".

## Step 2 - Flush durable facts

A fact that already has a durable home (project capsule,
`dev/local/meta/decisions.md`, AGENTS.md, the host's memory when it keeps one)
goes there first, and the prompt points at it. Do not invent new documents
for this.

## Step 3 - Compose the prompt

Two sorting rules decide what goes in:

- **On disk: pointer.** Files, commits, PRDs, plans, capsule: name the path
  (with line numbers when useful), never restate the content.
- **Conversation only: verbatim.** Requirements the user stated, decisions and
  their reasons, rejected approaches, observations from runs, preferences.
  Nothing on disk records these; after the context clears they are gone.

Writing rules:

- Second person, imperative, addressed to the next agent. No narrative, no
  "successfully", no praise.
- Absolute dates, absolute or repo-relative paths, short hashes. Never
  "above", "earlier", "as discussed": the reader has no earlier.
- No secrets. Name the env var or file that holds a value, never the value;
  the prompt travels through clipboards and other tools.
- Every section stays; an empty one reads `none`. A dropped section reads as
  "nothing to say", which is a different claim.
- Mark what you did not verify `(unverified)`.
- Aim under 80 lines. Past that, the usual cause is restating what is on
  disk; replace with pointers.

Template:

```markdown
# Continuation: <one-line mission>

You are continuing work handed off from a previous session on <YYYY-MM-DD HH:MM>
by <agent/model>. Verify State before changing anything; treat Decisions as
settled. <If compacted: "That session lost its early context at compaction;
anything before <HH:MM> comes from disk, not memory.">

## Start here
1. <exact first action: a command, or a file and the change to make>
2. <second action>
Activate first: <mode or skill, e.g. `/ponytail full`, `/work`> | none

## Goal
<what the user wants, in their words where possible; acceptance criteria if known>

## State
- Repo: <path>, branch `<branch>` (base `<base>`)
- Last commit: `<hash> <subject>`
- Uncommitted: none | <`git status --short` output>
- Stashes: none | <list>
- Active PRD/plan: none | <paths>
- Verify: `<command>` -> <N passed, M failed, K xfail/skipped at HH:MM> | not run this session

## Done this session
- <outcome> (`<hash>` | <path>)

## Open tasks (in order)
- [ ] <task> - <where/how; what "done" looks like>

## Decisions (settled, do not reopen)
- <decision> - because <reason> (<user | agent>)

## Dead ends (do not retry)
- <approach> - failed because <reason>; evidence: <error, path, or measurement>

## Gotchas
- <environment, tool, or repo quirk discovered this session>

## Read first
- `<path>` - <why; which lines>

## Needs the user
- <question to answer, or action only they can take> - <what waits on it>

## Rules for this work
- <constraints the user stated this session: scope limits, style, "never touch X". Standing rules load on their own on the same host; for another host, name the ones that matter>
```

## Step 4 - Write the file

Inside a repo: `dev/local/tmp/handoff-<YYYYMMDD-HHMM>.md` (stamp from
`date +%Y%m%d-%H%M`), prefixed with the 5-digit PRD number when the session
works one
(`dev/local/tmp/00123-handoff-20260905-1830.md`). Create `dev/local/tmp/` if
absent. Outside a repo: `$TMPDIR/handoff-<YYYYMMDD-HHMM>.md`. The file is the
prompt, byte for byte: it is what the clipboard step reads.

## Step 5 - Show, then offer the clipboard

Show the prompt in chat. Then ask one yes/no question: "Copy the prompt to the
clipboard?" On yes, run the command for the host OS (`uname -s`; WSL when
`uname -r` mentions `microsoft`), reading from the file:

| OS | Command |
|---|---|
| macOS | `pbcopy < <file>` |
| Linux, Wayland | `wl-copy < <file>` |
| Linux, X11 | `xclip -selection clipboard < <file>` or `xsel --clipboard --input < <file>` |
| WSL | `clip.exe < <file>` |
| Windows, PowerShell | `Set-Clipboard -Value (Get-Content <file> -Raw)` |

Report the exit status as it was: "copied with pbcopy" only when it returned
0. If the tool is missing, say which one and where the file is; do not
install anything and do not try another route.

Unattended session (no human to answer): skip the question and the clipboard;
report the file path.

## Step 6 - Report

One line: the file path, whether it was copied and with what, and the line
count. Nothing else; the prompt itself was already shown.

## Edge cases

- **Not a git repo**: State says `not a git repo`; skip the git commands.
- **Detached HEAD**: record the commit hash and flag it in State.
- **Compacted session**: keep the window sentence in the opening paragraph;
  pull what happened before compaction from disk (git log, files), not from
  memory.
- **Several repos touched**: one prompt, one State block per repo.
- **Nothing done yet**: still produce it; Done reads `none`, Start here still
  names the first action.
- **Prompt exceeds 80 lines after replacing content with pointers**: keep it
  complete; length is a smell, not a cap.
