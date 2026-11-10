# Skills adopt repository project memory

Status: intake, not yet specced. Recorded 2026-11-10.

Source: Engram intake 00010, specced as Engram PRDs 00010 and 00011
(`buvis/engram`, `docs/dev/project-management/intake/processed/00010-shared-project-memory/discovery.md`).

## Idea (from Engram Session 6)

Authoritative project memory moves from Claude auto-memory
(`~/.claude/projects/<encoded-path>/memory/`) into each repository at
`docs/dev/project-management/memory/`. Each fact is one `<slug>.md` file, with
frontmatter `name`, `description`, and `type` (`project`, `feedback`, or
`reference`), plus `source` and a non-empty `evidence` list. The directory has a
sorted `MEMORY.md` index, marked `merge=union` in `.gitattributes`. Git carries
the author, date, and revisions. Content must be public-safe. `engram memory
check` validates a directory.

Skills that read or write the Claude directory must follow:

- `skills/catchup/scripts/load-memories.sh`: read repository memory first, and
  fall back to the Claude directory. Its `tr '/.' '-'` encoding also misses `_`
  and other characters that Claude encodes; Engram fixed the same defect in
  Session 1 (`re.sub(r"[^a-zA-Z0-9]", "-", path)`).
- `skills/distil-memory` (`scripts/write.py --store`, SKILL.md step "write the
  saved entry"): write proposals into the repository memory directory in the
  new schema (`source` = transcript session, `evidence` from the proposal), then
  commit `docs(memory): add <slug>`.
- `skills/manage-agents-md/references/promote-memories.md`: promote from
  repository memory. `AGENTS.md` now also carries Engram's canonical
  "Project memory" section; do not duplicate it.
- `skills/structure-git-repo/references/layout.md`: add `memory/` to the
  `docs/dev/project-management/` vocabulary, matching the autopilot hook change
  (agent-plugins intake 00065).
- `skills/brush/SKILL.md`: check its memory references.

Order: after Engram PRD 00010 ships (schema and `engram memory check`), and
after the layout vocabulary change, since agents cannot write the directory
before that.
