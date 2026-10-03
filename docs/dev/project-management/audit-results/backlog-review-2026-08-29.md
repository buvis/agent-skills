# Backlog review - agent-skills - 2026-08-29

Verdict: GO, after one prerequisite command (below). All 5 Blocking findings
resolved by applied edits; 00005 left the backlog for the `~/.claude` repo.

**Before launching the batch**: run `/plugin update claude-checkup@buvis-plugins`.
claude-checkup `0.2.2` was released during this review, but the plugin cache on
this machine still holds only `0.2.1`, and PRD 00007 refuses to parse below
`0.2.2`. Its premise re-check stops and reports rather than lowering the bar, so
a batch launched without the update loses 00007, 00008 and 00009.

## Map

| # | PRD | template | lines | subsystems | depends on | verdict |
|---|-----|----------|------:|------------|------------|---------|
| 00002 | Sweep a Fix Across the Portfolio | standard | 275 | `skills/sweep-fix/` (new) | - | READY |
| 00003 | Plan a Port and Retire the Original at Parity | standard | 258 | `skills/plan-port/` (new) | - | READY |
| 00004 | Capture Playground Experiments as Zettels | standard | 259 | `skills/capture-experiment/` (new) | - | READY |
| 00006 | Put Config Maintenance on a Calendar | standard | 251 | `skills/brief-portfolio/` (edit) | - | READY |
| 00007 | Distil Memory: Extraction and Funnel | standard | 306 | `skills/distil-memory/` (new) | claude-checkup >= 0.2.2 | READY |
| 00008 | Distil Memory: Distiller and Dedup | standard | 280 | `skills/distil-memory/` | 00007 | READY |
| 00009 | Distil Memory: Queue and Walkthrough | standard | 282 | `skills/distil-memory/` | 00008, 00007 | READY |

Moved out: 00005 (Encode an Incident as an Invariant) is now `~/.claude` PRD
00156, where its `encode-incident` skill will be built. See finding 4.

Hygiene: filenames all match `NNNNN-{slug}-v{n}.md`; sequence numbers unique
across `backlog/`, `done/` and (absent) `wip/`, `hold/`, `discovery/`; no stray
files in `backlog/`. Cross-PRD dependencies all point at lower numbers, so drain
order is sound.

Citation check re-run after the edits: every hit is a forward reference to an
output the citing task creates (`dev/local/tmp/`, `dev/local/audit-results/`,
`dev/local/.trash/<date>/`) or a `[[links]]` false positive (memory wikilink
syntax, not a citation). The two cross-repo pointers in 00003 (gems PRDs 00071
and 00063-00068) sit outside this checker's root and were verified by hand: both
still exist in the gems backlog.

## Findings

### Blocking (all resolved)

1. **[00003, 00004, 00005, 00009] B: every Phase 2 needed a human the loop does
   not have.** Each PRD ended by running the finished skill for real, and each of
   those skills stops to ask: plan-port walks drop rulings, capture-experiment
   harvests a playground session that does not exist in a build session,
   encode-incident asks its one question, the distil walkthrough decides
   proposals one at a time. -> would have failed as: unattended hang.
   **Resolved**: each Phase 2 is now fixture-driven with headless acceptance, and
   the live run is recorded in the PRD as an attended follow-up. 00003 uses its
   own stated no-drop edge case; 00004 composes from a fixture experiment; 00009
   drives a seeded queue through a scripted decision sequence.
2. **[00004, 00005, 00006, 00009] B: Phase 2 writes landed outside the write
   fence.** `hooks/enforce_write_scope.py` allows only the repo, `<repo>/dev/local`,
   `$TMPDIR` and `/tmp` once `CLAUDE_UNATTENDED=1`; the tasks wrote to `~/bim/`,
   `~/.claude/projects/<hash>/memory/`, `~/.buvis` and (via `build.py`'s default)
   `~/.local/share/agents/portfolio-brief/`. -> would have failed as: hard deny
   mid-task, then rework thrash. **Resolved**: finding 1's fixture rewrite moved
   three of them to `dev/local/tmp/`; 00006 now passes
   `build.py --out dev/local/tmp/brief-check.html` explicitly.
3. **[00007, cascading to 00008 and 00009] D/G: the required version did not
   exist.** The contract check pinned claude-checkup at commit `d10ecb1`, which
   was committed to master but never released: the newest tag, `plugin.json` and
   the only cached version were all `0.2.1`, and Phase 0's fixture invented
   `0.3.0`. -> would have failed as: stall plus wrong-TDD lock-in on an invented
   minimum. **Resolved**: claude-checkup `v0.2.2` released during this review
   (108 tests passed, tag pushed, central marketplace bumped). 00007 now pins the
   minimum at `0.2.2`, its fixture uses `0.2.1` / `0.2.2`, its Phase 2 premise
   requires `0.2.2` installed, and it carries `catchup: force`.
4. **[00005, 00007, 00008, 00009] H: Claude-only skills placed in a cross-agent
   tree.** Both new skills targeted `skills/`, which every host discovers.
   `encode-incident` sweeps Claude's own config surface (`settings.json`,
   `dispatch.py` `ROUTES`, plugin `hooks.json`, `warden.yaml`) and has nothing to
   say on another host; this repo's README keeps that class out of `skills/`
   because `.braidignore` cannot hide it from Codex or Copilot. -> would have
   failed as: goal reversal. **Resolved**: 00005 moved to the `~/.claude` backlog
   as PRD 00156, with the reasoning written into its Structural Decomposition.
   distil-memory stays here: its coupling is an installed plugin and a corpus
   path, not the host itself, which matches existing precedent (`brief-portfolio`
   reads the gita registry, `audit-qwen` reads the plugin cache).
5. **[00007, 00008] B: two PRDs called a model, neither said how.** `triage()`
   was "a Haiku-tier pass" and `distil()` "the strong-model call", with no
   invocation contract and no test seam, one PRD apart in the same `scripts/`
   directory. -> would have failed as: wrong-TDD lock-in. **Resolved**: 00007
   defines one seam, `judge(prompt, tier)`, defaulting to the headless `claude`
   CLI, exported from `funnel.py` and injectable in tests; 00008's `distil()`
   imports it and defines no second path. Both acceptance criteria now require a
   stub judge and a test that fails if the default is reached.

### Non-blocking

- **[00002] D: hardcoded repo count.** Applied: "the seven repos currently
  missing from the registry" became "every on-disk repo absent from the registry
  and how many there were". Measured 26 registry rows against 34 directories
  under `~/git/src/github.com/*/*`, so the literal seven was already wrong.
- **[00005, 00009] E: memory-plane writers.** Applied: both PRDs now carry the
  same settled split instead of "whichever ships second reconciles".
  `encode-incident` writes `feedback` memories only, `distil-memory` writes
  `project` memories only, and neither rewrites the other's type.
- **[00005] C: rationalization feature had no task.** Applied: it now has its own
  Phase 1 task and acceptance naming the entry shape and
  `hooks/cartographer-echo.py` as the live consumer.
- **Frontmatter tuning.** Applied: `design: skip` on 00003, `catchup: force` on
  00007, `default_model: opus` and `rework_cap: 5` on 00008. All three blocks
  verified well-formed at the top of their files.
- **[all] A/F: line counts of 251-306, above create-prd's ~200 split rule.**
  Accepted, no change. The rule targets loose coupling; these are single-skill
  PRDs whose prose costs roughly 4K tokens against a 150K per-task budget.
- **[00008] A: Foundation Layer carries a dependency** where the template says
  "No dependencies - built first". Accepted, no change; cosmetic.

### Questions

None. The PRDs are unusually specific: contracts, enum values and thresholds are
named, premises carry execution-time re-checks, and rejected alternatives are
recorded with reasons.

## Reshapes

One, applied: 00005 moved to `~/.claude` as PRD 00156 (finding 4). No merges and
no splits. The three distil-memory slices are correctly ordered and their source
discovery doc forbids merging them; the remaining new-skill PRDs are unrelated
scopes, so merging them to save ceremony would only make review findings noisy.

## Gaps

- Closed: claude-checkup 0.2.2 is released, so nothing outside this backlog
  blocks 00007 except installing it.
- Closed: the memory-plane split is written into both sides.
- Open, by design: `distil-memory` will be discoverable by Codex and Copilot,
  where it fails on a missing plugin. Judged acceptable under finding 4; revisit
  if that failure ever costs a real session.

## End state after this batch

The repo gains three standalone skills (sweep-fix, plan-port, capture-experiment)
and one three-part feature (distil-memory), plus per-audit cadence rows in the
portfolio brief that replace the newest-mtime proxy. Every skill ships with a
headless proof that its plumbing works, and each carries one attended follow-up
you run by hand to prove its judgment. The memory plane gains one writer here and
one in `~/.claude`, with a stated contract between them. Nothing in the batch is
left half-finished waiting on a human mid-loop.

## Decisions applied

| # | Scope | Decision | Status |
|---|-------|----------|--------|
| 1 | 00003, 00004, 00005, 00009 | Phase 2 becomes fixture-driven; live run recorded as attended follow-up | applied |
| 2 | 00006 | Phase 2 runs `build.py --out dev/local/tmp/brief-check.html` | applied |
| 3 | 00007 | Release claude-checkup 0.2.2, pin the minimum at 0.2.2 | applied (v0.2.2 pushed, marketplace bumped) |
| 4 | 00005 | Move to the `~/.claude` backlog as PRD 00156; distil-memory stays | applied |
| 5 | 00007, 00008 | One `judge()` seam in 00007, imported by 00008 | applied |
| 6 | 00002 | Replace the hardcoded "seven repos" with a reported count | applied |
| 7 | 00005, 00009 | Write the memory-plane owner split into both | applied |
| 8 | 00005 | Rationalization write gets its own task | applied |
| 9 | 00003, 00007, 00008 | Frontmatter tuning | applied |
| 10 | all 8, 00008 | Line counts and Foundation Layer wording | accepted, no change |

Side effect worth knowing: claude-checkup's working tree held an uncommitted
formatting pass (trailing commas, rewrapping, quote style in `parser.py` and
`test_analyze.py`, no behavior change). It was stashed for the release and popped
back afterwards, so that tree is exactly as it was found, still dirty.

## Gate honesty

- Lenses A-H all ran. Lens D was run inline rather than fanned out to subagents
  (8 PRDs, at the threshold, not over it).
- Every grounding claim was checked against the machine, not taken from the PRD:
  `collect.py:429`, `collect_claude_maintenance`, `collect_brush`,
  `MAINT_DUE_DAYS`, `externalTodos`, `_resolve_rg`, `resolve_strunk_skills_dir`,
  `skills.jsonl`, `repos.csv`, `rationalizations.md`, `~/bim/inbox/automated/`,
  the ast-grep install, loupe's rule pack, the gems backlog, the claude-checkup
  tags and cache, and the write-fence root list.
- `autopilot:plan-tasks` steps 4-4.7 were consulted for the budget rule (150K
  threshold, 55K overhead constant). No PRD comes near it, so no budget finding
  was raised.
- The "seven repos" count in finding 6 is suspected, not confirmed: 26 registry
  rows against 34 on-disk directories implies 8, but the registry may hold paths
  outside `~/git/src/github.com/*/*`. The fix removes the number either way.
