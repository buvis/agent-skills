# Project Capsule: agent-skills

Generated: 2026-11-02 (closeout/archive-windows-2 worktree — PRD 00164 catchup)

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

- This worktree (`agent-skills/closeout-archive-windows-2`, branch
  `closeout/archive-windows-2`, forked from `closeout/archive-windows` at
  `73386d6`) is a follow-on Stage 1 Lane B session: PRD 00164 repairs the
  last 6 native-Windows failures the hosted run found against candidate
  `5bc7cc4` (4 clone-link-text failures in `_copytree_links_typed`, 2
  disk-executable-bit assertions that read a bit Windows does not keep).
  `closeout/archive-windows` (sibling worktree `closeout-archive-windows`)
  already carries 00160 and 00162 fully committed through CHANGELOG; this
  branch builds on that tip rather than redoing it. Lane A (archive
  containment, `closeout/archive`) and Lane C (migration/dependency PRs) run
  in separate worktrees; never touch their files from here.
- Autopilot batch `202611022121` was minted here for PRD 00164. `wip/` also
  holds 00133, 00160 and 00162 — informational only, not this worktree's to
  advance (00160/00162 await review on `closeout/archive-windows`; 00133 is
  the unrelated main-checkout batch). `default_model: opus` per frontmatter
  (clone path of a security-containment module, native Windows semantics
  verifiable only on the hosted runner).
- Remote master's latest run (41419919382, 2026-11-02) still fails Windows
  with 61 failed / 4166 passed / 40 skipped — a different, larger failure
  set than this PRD's 6 (clone-fixture path ordering in
  `test_run_eval_*`/`test_eval_vet`, not the clone-link/disk-mode pair 00164
  targets). That run is from master, not from this branch's candidate; do
  not conflate the two when judging 00164's exit criteria.
- A fresh autopilot batch (`202611011931`) was minted in this worktree for
  PRD 00160 (`template-archive-extraction-fails-closed`), which promotes held
  triage stubs 00155-00158 against done PRD 00131's `build_template`/
  `fresh_clone`/`hash_paths` in `skills/use-qwen/scripts/eval_harness/trees.py`.
  00131 already landed partial containment (commit `147d146`); open gaps are
  the symlink-ancestor bypass (00158), the unfiltered `extractall` fallback's
  setuid/ownership leak and `DeprecationWarning` (00156/00157), and missing
  refusal-path regression coverage (00155). `default_model: opus` per the PRD
  frontmatter (security containment predicate, filter-parity equivalence).
- `plans/repository-closeout-plan.md` defines three execution sessions and a
  fourth independent verification session. It covers archive safety, Windows
  CI, and PRs #17/#15/#16; PRD 00133 implementation remains outside its scope.
- Batch 202610271200 (main checkout) is stopped after 33 completed PRDs. PRD
  00133 remains in `wip/` there, build phase, zero completed tasks — unrelated
  to this worktree's batch and must not be touched from here.
- The store contains 18 backlog, 2 wip (00133, 00160), 20 hold, and 100 done
  PRDs, as seen from this worktree.
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

- No topic query this session: `wip/` holds three PRDs (00133, 00160, 00162),
  so the single-PRD topic rule does not apply, and `engram` was skipped by
  `catchup-probe` for this run regardless. Prior-session related context
  (below) is unchanged from the last query that ran it.
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

- Remote master is at `7dd93cf` (2026-11-02); `closeout/archive-windows-2`
  forked from `closeout/archive-windows` at `0035e628`.
- Open PRs: #17 migration skills (base `6091e02`, tip now `9249695` per
  earlier session); #16 Node 26; #15 setup-uv 10.3.3. All three remain live.
- Latest remote-master CI, run 41419919382 (2026-11-02, commit `7dd93cf`),
  failed on Windows: 61 failed, 4166 passed, 40 skipped — fixture-path
  ordering in `test_run_eval_cli`/`test_run_eval_harness*`/`test_run_eval_vet`
  (clones list empty where populated clones were expected), unrelated to
  00164's clone-link-text/disk-mode pair. Linux, lint, Node, shell passed.
- PR #17's body still names PRD 00150; its branch now carries PRD 00159.
  Correct that description when next updating PR metadata.
- One open issue: Dependency Dashboard. No GitHub releases returned.

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
