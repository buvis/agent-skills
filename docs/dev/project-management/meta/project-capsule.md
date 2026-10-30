# Project Capsule: agent-skills

Generated: 2026-10-30 (Git hygiene and unpublished-change review)

## Key Invariants

- `skills/` is the only directory `braid` scans and projects to other hosts
  (`~/.agents/skills`, `~/.claude/skills`). A `SKILL.md` placed there is
  advertised as runnable on Claude Code, Codex, and Copilot alike — a
  half-implemented skill (prose without the code it describes) must live
  under `docs/plugin-skills/<name>/` instead, or it gets routed to and fails
  on hosts without the backing plugin.
- Every path inside a `SKILL.md` must resolve on all hosts: same-skill files
  use `~/.agents/skills/<name>/...`, never `${CLAUDE_SKILL_DIR}` (Claude-only)
  and never a bare `/Users/<name>/...` (single-machine). `${CLAUDE_SKILL_DIR}`
  is expanded by Claude Code before the model even reads the file, so a
  session that writes rendered text back to disk destroys the placeholder and
  bakes in an absolute path — this already happened to `create-skill`
  (fixed 2026-08-26).
- This repo is public: no personal paths, usernames, hostnames, employer
  names, or private project names, including in examples.
- Working documents moved from `dev/local/` to `docs/dev/project-management/`
  (temporary assets to `docs/dev/tmp/`) in cdcb888; any `dev/local/` path in
  older notes is pre-move. `docs/dev/project-management/meta/` is the only
  home for the capsule/decisions/keeper files
  (root went directories-only 2026-08-27 per `~/.claude` PRD 00139); an
  unmigrated store may still carry a root copy, so code that reads keepers
  checks `meta/` first and falls back to root.

## Architecture Decisions

- Skills are portable-first: the repo is the canonical source, `~/.agents/skills`
  is a generated symlink farm (`braid`), and Claude gets a second-hop link via
  `~/.claude/skills`. Compatibility classes (`compatibility:` frontmatter) say
  whether a skill runs everywhere, is a compat copy of a Claude plugin skill
  (skipped by `braid` on the way to Claude), or is a documentation-only copy.
- `docs/plugin-skills/` is deliberately outside `skills/` so no host discovers
  it — that's the only way to keep a "spec, not runnable procedure" from being
  routed to and failing on Codex/Copilot.

## Component Boundaries

- `src/agent_skills_braid/cli.py` owns source composition and managed host links.
  `bin/braid.py` and the installed entry point reach that implementation.
- Each skill owns its scripts and tests. Pytest collects `tests/`, `skills/`,
  and `scripts/`; the shell CI job additionally runs the Bash suites.
- Ruff excludes the skill and documentation trees intentionally. Validate
  changed skills with `skills/create-skill/scripts/validate_skill.py`.
- The memory funnel's judge is the model invocation boundary. PRD 00133 will
  restrict its tools and inherited MCP configuration; that work is unfinished.
- Qwen evaluation templates are extracted from Git archives. The compatibility
  extraction path still has confirmed containment risk; see held PRDs 00156
  and 00158 and the unpublished review below.

## Active Work

- Batch 202610271200 is stopped after 33 completed PRDs. PRD 00133 remains in
  `wip/`, build phase, zero completed tasks. The interrupted run's telemetry
  and unchanged backlog-to-wip move are committed.
- The store contains 19 backlog, 1 wip, 20 hold, and 100 done PRDs.
- PRD 00111's four code/test commits were manually reverted. Custody is closed;
  the later state-decoding fix remains. Its original persistence defect remains
  unresolved, and its custody branch is retained for follow-up.
- Master retains the original 147 commits already published through the
  migration branch, then 12 grouped local commits and the hygiene record.
  The grouping preserved the pre-groom tree exactly; only the subsequent
  capsule/report update changes documentation.
- Migration PR #17 remains eight commits on base `6091e02`, tip `9249695`.
  Its validator-consolidation PRD is now 00159, avoiding master's 00155.
- Do not merge or discard the three fast-track branches: each carries a
  separate held PRD's unmerged implementation. The audit test branch and
  custody branch also retain deliberate recovery material.

## Related context

- `prds/wip/00133-transcript-judge-inherits-tools-v1.md:7` — score 0.0328;
  the interrupted work's tool restriction boundary.
- `prds/done/00072-distil-judge-no-persistence-v1.md:7` — score 0.0159;
  related judge invocation history.
- Topic: “Transcript instructions reach a judge without tool restrictions”.
  Repo and portfolio queries ran. Portfolio status reports stale/dead rows
  (memory 24/1, PRD 0/3087, transcripts 0/17604, code 54/21); portfolio
  recall is incomplete. Review harvest succeeded partially; 89 files lacked
  parseable frontmatter. No prior task session was available to restore.

## GitHub State

- Remote master remains `02a1423`; grooming has not pushed it.
- Open PRs: #17 migration skills; #16 Node 26; #15 setup-uv 10.3.3.
  All three remote branches have live PRs and are retained.
- Latest remote-master CI, run 40584704851, failed on Windows with 60 Qwen
  harness clone-path/hash tests. This is historical baseline failure, not
  proof that the regrouped local tip was tested on Windows.
- Migration run 41030058506 at `9249695`: Linux Python 3.10/3.13, lint,
  Node, and shell jobs passed; Windows was still running at this snapshot.
- PR #17's body still names PRD 00150; its branch now carries PRD 00159.
  Correct that description when next updating PR metadata.
- One open issue: Dependency Dashboard. No GitHub releases were returned.

## Project Health

- Local recovery verification: 4258 tests passed, 9 skipped; Ruff passed;
  all 12 affected skills validated; `braid --check` reported zero drift.
- Migration verification: 4158 tests passed, 12 skipped, plus 4 subtests;
  210 braid tests also passed against that branch's own source.
- These green suites do not close the archive compatibility finding. A
  disposable crafted-archive probe changed a sentinel outside the destination
  with `data_filter` unavailable; the filtered path refused it.
- See `audit-results/unpublished-review-2026-10-30.md` for review scope,
  grouped commits, retained branches, and remaining release risks.
- `audit-results/brush-report.md` records the Git hygiene outcome. Active
  migration reference material remains local; the purge preview was withheld.
