# Project Capsule: agent-skills

Generated: 2026-11-16 (catchup on master; Key Invariants and Architecture unchanged)

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
- The memory funnel's judge is the model invocation boundary. PRD 00133
  (restrict its tools and inherited MCP config) is done.
- Qwen evaluation templates are extracted from Git archives
  (`use-qwen/scripts/eval_harness/trees.py`). PRDs 00156/00158 on its
  containment risk are no longer in the store; status unverified this pass.

## Active Work

- Measured 2026-11-16: no wip PRD. Backlog: 00050 (qwen ivan capability
  eval) and 00159 (retire bundled braid, gated by an `eligibility` check on
  gems#272 shipping a braid without `--config-root`). Hold: 00111 only.
- Recent focus: PRDs 00177-00179 done (sweep-fix pre-image verification,
  distil-memory prompt framing); Renovate onboarding merged a dozen dep PRs
  on 2026-11-16 (Node 26, jsdom 31, pymupdf 2, mermaid-cli 12, python-docx 1.2).
- Worktree `~/git/src/worktrees/agent-skills/retire-braid`
  (`feature/retire-braid`) is clean, zero own commits, one behind master.
  Staged for PRD 00159; may belong to a live session, so leave it.
- The 2026-10-30 closeout plans in `plans/` are NOT finished. PRs #15-#17
  are settled and archive PRDs 00155-00158 closed as fixed in `ff6e8af`, but
  lane PRD 00163 (Windows residue, CI `-ra`) exists only on
  `origin/ci/closeout-stage-1-*` and never reached master, and Session 4
  verification never ran. 00161 reached master inside the #17 squash merge.
  2026-11-17: 00163 tasks 2 and 4 (plus a `scripts/gate.py` subtest-parsing
  fix) reviewed, merged and closed after a green hosted Windows run (`4ddcc5a`);
  tasks 1 and 3 were superseded on master. `origin/ci/closeout-stage-1-*`
  deleted. Only the plan's Session 4 verification remains.
- 00111 has no branch of its own: PRD 00159 (task 3) closes it, since
  deleting the bundled braid deletes the defect.
- 00050 waits on an operator calibration record
  (`audit-results/qwen-ivan-calibration/protocol.md`); its eligibility fails.
- Autocodex is retired here (2026-11-15); Claude autopilot stays.
- Local-only branches kept on purpose: `custody/00111-*`, `custody/00135-*`
  (never push), `agoge/authored-tests-2026-10-26`. `docs/agoge-0.3.0` and
  `docs/structure-ignore-standard` also exist on origin, no open PR.

## Related context

- No topic this session: on master with no wip PRD, so engram queries were
  skipped. Review harvest ran: most review files upserted; many `*-audit.md`
  logs reported `parse_failed` (no decision blocks).

## GitHub State

- Measured 2026-11-16: 0 open issues, 0 open PRs.
- Releases v0.1.0 and v0.2.0 (both 2026-11-10); 431 commits on master since
  v0.2.0, unreleased.
- Master CI: last 8 runs success or cancelled (superseded by later pushes).
  Last failure 2026-11-10 (`f318ee2`): Windows, 2 failures in
  `sweep-fix/test_sweep_main.py` control-verification test; later runs green.

## Project Health

- CI green on all jobs including Windows since 2026-11-16 runs.
- Release cadence lags: 431 unreleased commits.
- Stale remote branches (`docs/structure-ignore-standard`,
  `ci/closeout-stage-1-20261103`) are 13 days old with no PR.
