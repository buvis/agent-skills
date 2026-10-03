# Backlog review - agent-skills - 2026-09-01

Verdict: GO (all findings resolved in the 2026-09-01 walkthrough; Blocking cluster hardened by applied edits)

Reviewed against: create-prd SKILL.md + assets (read today), autopilot plugin 0.2.2 plan-tasks steps 4-4.7 (installed version confirmed via installed_plugins.json).

## Map

| # | PRD | template | lines | subsystems | depends on | verdict |
|---|-----|----------|-------|------------|------------|---------|
| 00010 | qwen38-multifile-capability-eval-v1 | standard | 372 (post-edit) | use-qwen (eval procedure + docs) | none | READY (hardened for unattended) |

Hygiene: backlog contains only the one well-formed PRD file. Sequence 00010 unique across backlog/wip/done/hold (discovery/ absent; 00005 is a harmless gap - allocated nowhere). Citation check (check_links.py): 0 findings under prds/backlog + prds/wip. No template stubs, no `(guess)` markers (control-verified scan).

## Findings

### Blocking

- [00010] B (executability): **Phases 1-3 are attended-operator work queued for an unattended loop.** Four legs, one decision:
  1. **User decision mid-loop.** Phase 3 task 1 acceptance: report "presented to the user as a decision point ... not silently acted on"; Phase 3 task 2 then records that decision in SKILL.md. Target Users names the maintainer as the decider. create-prd's Unattended rule calls such a PRD incorrectly created. -> fails as: unattended hang.
  2. **External service unpinned.** `qwen-run.sh` requires a llama-server already serving the exact quant ("Requires a llama.cpp server running with the model loaded"; hard errors `endpoint_unreachable` / "Start llama-server first"). No task or acceptance establishes or pre-checks it. -> fails as: all 6 qwen dispatches fail mid-batch (rework thrash / batch failure).
  3. **Worktree root unpinned vs write fence.** The PRD's own vetted method requires surgical Edit-tool reverts; the unattended fence (enforce_write_scope.py) allows only repo, dev/local, $TMPDIR, /tmp. Worktrees for ddb/gems/claude-warden at unspecified paths (e.g. ~/git siblings) mean every surgical revert is denied. -> fails as: stall mid-Phase-2. (Same failure class as 4 of 8 PRDs in the 2026-08-29 review.)
  4. **Evidence production under tests-are-the-spec.** autopilot:work hands each task to an implementor whose spec is "make the failing test pass"; Phase 2's acceptance is log content, satisfiable by writing the log without running the dispatches. Self-consistent fabricated evidence would pass every gate and poison the trust-scope decision - the PRD's entire deliverable. Suspected-by-construction, not observed. The PRD's own Feature 1 Behavior also says vetting "requires human judgment". -> fails as: goal reversal.
  Fix: HOLD for attended run (recommended), or split Phase 0 out for autopilot and hold the eval, or harden all four legs and keep it queued.

### Non-blocking

- [00010] A: standard-template structure incomplete - no `### Module:` blocks ("A file tree alone is not sufficient") and no `## Dependency Graph` section ("Even single-phase PRDs MUST include this section"). plan-tasks 0.2.2 step 3 explicitly derives ordering when the section is absent, so the loop survives; this is law-compliance drift, not a stall. Fix: add both sections (~10 lines).
- [00010] C: Phase 1/2 artifacts (TSV manifest, prompt files, evidence logs) have no stated home - the Repository Structure names only eval-runbook.md and the final report, so the planner invents paths. Fix: name `dev/local/tmp/00010-multifile-eval/` (or similar) in the tree and exit criteria.
- [00010] B (prose tax): Problem Statement paragraph 2 (~15 lines) restates Feature 1's Outputs nearly verbatim, and session-deictic phrasing ("this session's", "my own after-the-fact review") dangles for any future reader. Every task pays the PRD slice against the 150K budget. Fix: trim the duplicate narrative, reword deictics.
- [00010] A (frontmatter): none set (all defaults, which is valid). If it stays queued: `design: skip` - the eval procedure is already fully specified; a Phase 1.5 design doc adds cost without content.

### Questions

None - the confusion notes all resolved into the findings above.

## Reshapes

- Considered a size split (297 lines > create-prd's ~200 rule): rejected on coupling - Phases 0-3 are one sequential procedure; only the attended/unattended seam (Phase 0 vs 1-3) is a clean cut, and that is Blocking-1 option 2, not a size remedy.

## Gaps

- If the trust decision extends scope to multi-file, `eval-runbook.md` step 1's eligibility rule (explicitly single-file) gains no multi-file variant from any task - Phase 3 updates SKILL.md only. Worth folding a runbook update into Phase 3 if the PRD is hardened for unattended; covered by the attended operator naturally otherwise.
- Repo nit (outside this PRD): `approved-models.txt:24` still says "Not yet promoted to default" while SKILL.md now names Qwen3.8 the default (commit e87f23d). One-line stale comment.

## End state after this batch

If Blocking-1 resolves to HOLD: the unattended batch has nothing to run; the eval executes attended with the PRD as its script, producing the hardened runbook, the comparative evidence, and the trust-scope decision in one session. If hardened instead: the batch delivers all of it unattended, with the fabrication risk mitigated but not removed. Either way the project ends with the isolation-safety lessons codified and the multi-file question answered - the direct continuation of the 2026-08-31 qualification trajectory (lens H: aligned, no goal reversal, no discovery doc existed to trace against).

## Grounding verified (lens D)

`eval-runbook.md` exists and lacks the checklist (genuinely new work); `qwen-run.sh`, `run-eval.sh` (TSV manifest `<prompt-file><TAB><verify-cmd>`), `promote-default.sh`, autopilot 0.2.2 `use-sonnet/scripts/sonnet-run.sh` all exist; `SKILL.md:66` confirms Qwen3.8 default, `:69` the verbatim single-file caveat; approved-models.txt narrates the ddb contamination; no prior multifile report in audit-results; wip/ empty (no overlap), hold/ empty (no dead dependencies).

## Frontmatter tuning

| PRD | suggestion | why |
|-----|------------|-----|
| 00010 | `design: skip` | procedure PRD, already fully specified; design phase would add cost without content (only if it stays queued) |

## Decisions applied

1. Blocking B (attended-work cluster, 4 legs): user chose **harden for unattended** - APPLIED.
   - Leg 1 (user decision mid-loop): Phase 3 task 2 now applies a recorded mechanical decision rule (user-approved in this walkthrough): (1) any Qwen false claim -> single-file-only; (2) both-engines-fail tasks excluded as suspect, <5 scored left -> single-file-only; (3) zero dropped-a-file AND <=1 scored fail -> full multi-file; (4) else all impl+test-pair tasks clean (>=3 guaranteed by Phase 1 manifest) -> impl+test pairs only; (5) else single-file-only. Sonnet gates nothing beyond the exclusion. Report still ships walkthrough packets; user can overturn post-batch. Phase 3 task 1's "presented to the user as a decision point" rewritten accordingly; Success Metrics aligned; Phase 1 acceptance now requires >=3 impl+test-pair + >=1 impl+caller tasks.
   - Leg 2 (llama-server): new Phase 2 gate task `qwen-run.sh --approved-only --preflight`, exit 0 + healthy line naming the exact quant, fails loud before any dispatch; server named as operator pre-condition in the dispatch feature's Inputs.
   - Leg 3 (write fence): worktrees pinned under `/tmp/qwen-eval-00010/` in the dispatch feature Behavior and the Phase 2 prep task acceptance.
   - Leg 4 (fabricable evidence): dispatch acceptance now requires, per task per engine, the exact dispatch command line, engine-identity evidence (qwen `Using provider ...` line / sonnet model flag), captured full engine output file under `dev/local/tmp/00010-multifile-eval/` (must exist; `sonnet-run.sh -o`), and verbatim gate output with exit-code line; transcript-audit acceptance cites captured files by path; "requires human judgment" reworded to session-exercised judgment.
2. Non-blocking A (template sections): APPLIED - two `### Module:` blocks and a `## Dependency Graph` (Foundation/Core/Integration) added; heading walk re-verified against standard.md.
3. Non-blocking C (artifact home): APPLIED - `dev/local/tmp/00010-multifile-eval/` pinned in the tree, Phase 1 exit criteria (manifest.tsv path + run-eval.sh TSV format), and Phase 2 acceptances.
4. Non-blocking B (prose trim): REJECTED by user - narrative stays.
5. Non-blocking A (design: skip frontmatter): REJECTED by user - design phase stays (no frontmatter added).

6. Follow-up (2026-09-01, same session): server check found Qwen3.8 already live on :8002 (pinned preflight healthy) but a stale Qwen3.6 server on :8001 makes unpinned `--approved-only` resolution pick the wrong (old) model - lowest live port wins. APPLIED: the PRD's preflight gate and dispatch tasks now pin `-P llamacpp8002` and the acceptance requires that provider name in the healthy/identity lines. The stale :8001 server (PID at the time: 39083) and the stale `start_qwen` helper (still launches Qwen3.6 on :8001) were surfaced to the user.

Post-apply lens A re-run: heading structure matches assets/standard.md top-to-bottom (Overview / Functional Decomposition / Structural Decomposition with tree + Module blocks / Dependency Graph with three layers / Implementation Phases / Test Strategy / Risks); unattended-indicator sweep clean (remaining "user"/"manual" hits are historical narrative or explicitly post-batch).
