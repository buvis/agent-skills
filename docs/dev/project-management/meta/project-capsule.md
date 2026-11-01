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

- `plans/repository-closeout-plan.md` defines three execution sessions and a
  fourth independent verification session. It covers archive safety, Windows
  CI, and PRs #17/#15/#16; PRD 00133 implementation remains outside its scope.
- 2026-11-01: this worktree (`agent-skills-closeout/windows`, branch
  `closeout/windows`) ran Stage 1 lane B — PRD 00044 (Windows CI junction
  claim) under autopilot batch `202611011930`. **Stalled at the plan-expansion
  gate (`module_drift`) and moved to `hold/`**: the PRD's own module list
  (`## Repository Structure`) describes the ORIGINAL greenfield design
  (new `conftest.py`, new Windows CI job, new testpaths) — all of which are
  ALREADY SHIPPED on this branch (verified: `conftest.py` exists with all four
  fixtures, `.github/workflows/ci.yml` has a `windows-latest` job,
  `pyproject.toml` already sets `testpaths = ["tests","skills","scripts"]`).
  The real remaining work is 16 specific hosted-Windows test failures
  (causes B1-B2, P1-P2, D1-D3, G1, U1-U2, S1, Q1-Q3, Q7, Q8 — excluding Q4-Q6,
  which PRD 00160/archive-lane owns, and excluding `funnel.py`, which PRD
  00133 owns), documented in detail (exact files/lines/node IDs/proposed
  repairs) ONLY in an **UNTRACKED** file:
  `~/git/src/github.com/buvis/agent-skills/docs/dev/project-management/audit-results/repository-closeout-preparation.md`
  (plus a session addendum, `...-preparation-session-123534.md`, and an
  untracked `...-preparation-plan.md`) in the MAIN checkout — none of this
  exists on `closeout/windows` or any other closeout worktree's branch
  history. A future session resuming PRD 00044 (from `hold/`) MUST refresh
  the PRD's scope/Repository-Structure section against that evidence (or the
  coordinator must commit it somewhere every lane can reach) before
  replanning, or the plan-expansion gate will stall again. The 6 real
  implementation tasks planned and then discarded this session were, for the
  record: W1 braid link-identity/chmod (B1,B2), W2 ground_prd citation
  parsing (P1,P2), W3 distil-memory docket/write (D1,D2,D3), W4
  glean/purge-devtmp/sweep-fix (G1,U1,U2,S1), W5 use-qwen eval_harness
  (Q1,Q2,Q3,Q7), W7 use-qwen vetting deadline (Q8) — each with exact failing
  node IDs and proposed repairs already drafted; a resuming session can likely
  reuse this breakdown nearly verbatim once the PRD doc itself is updated.
  **Batch `202611011930` marked drained (not relaunched)** specifically so the
  loop driver's next default PRD selection cannot pick up PRD 00133, which
  remains alone in `wip/` in this worktree and is explicitly off-limits to
  default selection per the repository closeout plan's shared rule 9
  (`plans/repository-closeout-plan.md`): "Preserve the existing PRD 00133
  state; never select it through a default autopilot invocation."
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

- Remote master was observed at `6b52b2a` during closeout planning, after the
  grooming session ended. The grouped history is now published.
- Open PRs: #17 migration skills; #16 Node 26; #15 setup-uv 10.3.3.
  All three remote branches have live PRs and are retained.
- Latest remote-master CI, run 41032617118 at `6b52b2a`, failed on Windows:
  61 failed, 4166 passed, 40 skipped. Linux 3.10/3.13, lint, Node, and shell
  passed. Use its current logs instead of the older 60-failure baseline.
- Migration run 41030058506 at `9249695`: Linux Python 3.10/3.13, lint,
  Node, and shell jobs passed; Windows failed with 65 failed, 4062 passed,
  and 43 skipped.
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
