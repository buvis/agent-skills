---
design: run
---

# Per-host projection policy for braid

## Problem

`.braidignore` can only say "do not give this to Claude". Braid links the whole
inventory into the union view at `~/.agents/skills`, then filters that set once
on its way to `~/.claude/skills` (`src/agent_skills_braid/cli.py:359-373`; the
filter is applied at line 360, inside the `project_claude` branch).

Both other hosts read the union view directly, so the filter never reaches them:

- GitHub Copilot lists `~/.agents/skills` as a personal skill source
  (`copilot skill --help`), and `copilot skill list` returns all 48 skills.
- The Codex binary interns `.agents/skills` alongside `.codex/config.toml` and
  `.codex/hooks`, so it resolves the same root.

Since 2026-08-26 this repository publishes 15 documentation copies of
runtime-bound plugin skills (`run-autopilot`, `work`, `review-work-completion`
and the rest). They carry a procedure whose scripts, CLI and agents live in the
autopilot plugin, which exists only on Claude Code. Copilot and Codex now list
and can route to skills that cannot run there.

`State.hosts` is already a `dict[str, dict]` keyed by host name (`cli.py:358`),
but only the key `"claude"` is ever written. The data model anticipates this
feature; the CLI does not implement it.

## Capabilities and features

### Capability: express a per-host exclusion

**Feature: host-scoped policy files**

- Description: braid reads `.braidignore` (all hosts) plus
  `.braidignore.<host>` (that host only) from each policy root it already
  scans.
- Inputs: the policy roots resolved at `cli.py:446-455`; host names known to
  braid.
- Outputs: a mapping host -> ignored-name set, replacing today's single set.
- Behavior: a name in `.braidignore` is excluded from every host projection; a
  name in `.braidignore.copilot` is excluded from the Copilot projection only.
  The union view keeps linking everything, since it is the source the host
  views are built from (guess: alternatively the union itself could be
  filtered per host, which would require one union per host and is rejected
  here as more machinery than the problem needs).

**Feature: a Codex and Copilot projection**

- Description: braid projects to the hosts that read the union view, so an
  exclusion for them has somewhere to apply.
- Inputs: `--no-copilot` / `--no-codex` flags mirroring today's `--no-claude`;
  `AGENTS_ROOT`-style env overrides for each host root.
- Outputs: entries under `State.hosts["copilot"]` and `State.hosts["codex"]`.
- Behavior: Copilot and Codex read `~/.agents/skills` natively, so the
  projection for them is the filter, not a second link farm: a name excluded
  for a host must not appear in the union view that host reads. This is the
  one real design question and the design phase owns it - the two candidate
  shapes are (a) per-host link farms under `~/.agents/skills-<host>` with the
  host pointed at its own root, and (b) keeping one union and accepting that
  an exclusion is only enforceable for hosts with a private root (guess: (a)
  is the honest one, (b) is cheaper and covers Claude only, which is where we
  already are).

### Capability: keep the state file readable across the change

**Feature: state migration**

- Description: `.braid-state.json` gains host keys beyond `"claude"`.
- Inputs: an existing state file written by the current version.
- Outputs: a state file carrying every projected host.
- Behavior: an old state file loads without error and is treated as having no
  entries for the new hosts, so the first sync after the upgrade links them
  rather than reporting spurious drift.

## Structural decomposition

```
src/agent_skills_braid/
├── cli.py          # read_ignored -> per-host sets; run() projects each host
tests/
└── test_braid.py   # per-host policy and projection cases
.braidignore        # unchanged: the all-hosts list
.braidignore.claude # the 15 documentation copies move here (or stay shared)
```

**Module: agent_skills_braid.cli**

- Maps-to-capability: express a per-host exclusion; keep state readable.
- Responsibility: policy discovery and parsing, host projection, state I/O.
- Exports: `read_ignored` (signature changes), `run`, `Settings`, `State`.

**Module: tests.test_braid**

- Maps-to-capability: both.
- Responsibility: cover the new branch and the migration.
- Exports: none.

## Dependency graph

**Foundation layer** — `agent_skills_braid.cli` policy parsing. No dependencies;
built first.

**Core layer** — host projection in `run()`. Depends on policy parsing.

**Integration layer** — `tests/test_braid.py`. Depends on both.

## Implementation phases

1. **Per-host policy parsing.** `read_ignored` returns host -> set instead of a
   single set; `.braidignore` populates every host, `.braidignore.<host>` only
   its own. Depends on nothing. Acceptance: a new test in `tests/test_braid.py`
   writes both file kinds and asserts the returned mapping; `uv run pytest`
   passes.

2. **Host projection.** `run()` iterates the hosts it is configured for instead
   of special-casing Claude, writing one `State.hosts` entry each. Depends on
   phase 1. Acceptance: a test asserts a name excluded for one host is absent
   from that host's projection and present in another's; `uv run pytest` passes.

3. **State migration.** Loading a state file with only a `"claude"` key reports
   zero drift for hosts that have no entries yet. Depends on phase 2.
   Acceptance: a test loads a fixture state file in the old shape and asserts
   `braid --check` reports no drift for it.

4. **Move the runtime-bound names.** The 15 documentation copies are excluded
   from whichever hosts cannot run them. Premise: `.braidignore` currently
   lists them under the autopilot and checkup stanzas; re-check that the file
   still carries those names before editing, and skip with a report if it does
   not. Depends on phase 3. Acceptance: `braid --check` reports zero drift, and
   `copilot skill list` no longer lists `run-autopilot`.

5. **Document it.** `AGENTS.md` and `README.md` describe the per-host files and
   the host table states what was verified rather than assumed. Depends on
   phase 4. Acceptance: `README.md` contains no unqualified "Native. No extra
   link is needed." claim for a host nobody has tested.

## Out of scope

Kiro. `~/.kiro` does not exist on this machine and the README's row for it
describes manual wiring that has never been run, so any Kiro projection would
be written blind. Verify Kiro's real discovery path first, in its own PRD.

## Outcome (2026-08-26): resolved without building the feature

The problem is fixed. The design in this PRD was not built, and should not be.

Two findings closed it. First, both candidate shapes under "a Codex and Copilot
projection" are dead. Copilot's personal source list is fixed
(`copilot skill --help`) and the Codex binary interns `.agents/skills`, so
neither host can be pointed at a private root; shape (a) would have built link
farms nobody reads. Second, the 15 names never belonged in `skills/`. They are
specifications - `SKILL.md` and `references/`, with the scripts, CLI and agents
left in the plugins - and `skills/` is the one directory braid scans
(`_skills_directory`, `cli.py:114-121`), so anything placed there is advertised
as runnable on every host.

Moving them to `docs/plugin-skills/` took the union view from 51 to 36 and left
Claude at 15. `copilot skill list` no longer returns `run-autopilot` or the
other 14, and `braid --check` reports zero drift. That is phase 4's acceptance
criterion, met by a `git mv` instead of five phases of policy parsing, host
projection and state migration.

Phase 4 also had the split backwards. `.braidignore` mixes 21 compatibility
copies, which run fine on Codex and Copilot and are excluded from Claude only to
avoid a duplicate unnamespaced command, with the 15 runtime-bound copies. Had
`.braidignore` been redefined as "every host" the way phase 1 proposed, all 36
names would have left the union at once and Copilot would have lost the 21
skills it can actually run.

`State.hosts` stays a dict with one key. The data model still anticipates a
second host; nothing needs one yet, and the first that does will have to own a
discovery path braid can control.

Successor work, not filed: `docs/plugin-skills/` is a holding pen. Each entry
should be deleted once its plugin is installable on the hosts that need it,
along with the compatibility copy of any plugin that gets there - otherwise the
standalone copy recreates the duplicate-command problem on three hosts, where
`.braidignore` can only fix one.
