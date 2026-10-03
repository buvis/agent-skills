# Qwen3.8 Multi-File Capability Eval vs. Sonnet

Source: this session's 2026-08-31 single-file qualification of
`unsloth/Qwen3.8-27B-GGUF:UD-Q6_K_XL` (6/6, zero false claims, matched Sonnet
6/6 on the identical tasks) - see `skills/use-qwen/scripts/approved-models.txt`
and `SKILL.md`'s Model Selection section. That eval, like every qualification
before it, was deliberately single-file per task. This PRD tests the
documented, still-open gap: **multi-file work remains unproven** for this
quant.

## Overview

### Problem Statement

Qwen3.8-27B is now autopilot's default engine for `--approved-only` dispatches,
qualified and promoted on a 6-task single-file eval. But autopilot's real task
mix is not single-file: a typical PRD task touches an implementation file and
its test file, or an implementation file and a caller site elsewhere. The
*previous* default (Qwen3.6-27B-MTP) had this exact documented failure mode -
finishing one file and silently dropping the rest, while over-claiming
completeness in its final report. Nothing has yet tested whether Qwen3.8
inherited or fixed that weakness, because every eval to date (this model and
its predecessors) has controlled the variable away by only ever testing one
file per task.

Separately, the 2026-08-31 eval run surfaced three real methodology bugs in
the manual harness process, caught only through my own after-the-fact review:
a killed-and-restarted run left one task's target file already fixed before
its re-dispatch (contaminating that result until caught and corrected); a
whole-file `git checkout <commit>^ -- <path>` revert silently erased *other*,
unrelated later commits to files with substantial ongoing history, corrupting
two of six original candidate tasks before they were ever dispatched; and
running two `cargo test` invocations concurrently against the same disposable
worktree nearly deadlocked on the project's own file-locking test suite. None
of these are exotic - they will recur on any future eval run unless the
procedure itself carries the fix, not just this session's memory of it.

### Target Users

The solo maintainer, deciding whether Qwen3.8's `--approved-only` autopilot
trust scope should extend beyond single-file tasks, or stay restricted to them
per the current SKILL.md caveat.

### Success Metrics

- `eval-runbook.md` carries the three isolation-safety lessons above as
  checklist items, so a future eval run cannot repeat them silently.
- 6 genuinely multi-file candidate tasks are sourced and vetted with the same
  rigor as the single-file round: every touched file's post-task commit
  history checked for later behavior changes (not just presence in a task
  ledger), each task confirmed to require correlated changes across 2+ files
  to pass its real gate (not two files that happen to be touched but
  independently sufficient).
- Both Qwen3.8 and Sonnet run the identical 6 multi-file tasks from
  independently-verified clean pre-task state; every transcript is read for
  false claims before either score is trusted.
- A report states, per engine: score, false-claim count, and for any FAIL -
  whether it dropped a file (the documented failure mode), got confused across
  files, or a genuine logic error unrelated to being multi-file.
- A stated decision, produced by the recorded Phase 3 decision rule: keep
  Qwen3.8's `--approved-only` scope single-file-only, extend it to full
  multi-file, or qualify a narrower subset (impl+test pairs only).

## Functional Decomposition

### Capability: Isolation-safety methodology (fixes this session's bugs)

#### Feature: Codify the three isolation bugs as a pre-flight checklist

- **Description**: Extend `eval-runbook.md` with the lessons from the
  2026-08-31 run so they are checked, not remembered.
- **Inputs**: This PRD's Problem Statement; the corrected
  `approved-models.txt` comment block, which already narrates the ddb
  contamination incident.
- **Outputs**: A new `eval-runbook.md` section (or a linked addendum file)
  stating, as checklist items: (1) after any interrupted/restarted dispatch,
  re-verify every in-flight task's target file(s) are still at genuine
  pre-task state before trusting a re-dispatch's result; (2) before reverting
  a file via `git checkout <commit>^ -- <path>`, run `git log --oneline -L`
  (not `-G` pickaxe, which misses in-body edits) across the file's *entire*
  history from that commit forward - any later commit touching the same lines
  means a surgical text-level revert is required instead of a whole-file
  checkout, or the task is disqualified; (3) never run two test/build
  invocations concurrently against the same disposable worktree - dispatch and
  fully verify one engine's task before starting the other's for that
  worktree.
- **Behavior**: This is a documentation-only feature - no new code, since
  each rule is operator discipline a script cannot cheaply enforce (the
  `-L` check already requires case-by-case judgment, exercised by the
  session running the eval, on "is this later commit a behavior change or a
  pure refactor", which is exactly the call that caught 3 of the original 6
  single-file candidates last time).

### Capability: Multi-file candidate sourcing

#### Feature: Source and vet genuinely multi-file tasks

- **Description**: Find 6 completed PRD tasks where passing the real gate
  requires correlated edits across 2+ files.
- **Inputs**: `dev/local/prds/done/*.md` task ledgers across all
  gita-registered repos (same sourcing ground as the single-file round).
- **Outputs**: 6 candidates, each with: repo path, all target files (relative
  paths), the exact original task description (verbatim), the task's commit
  hash and parent hash per touched file, and the verify command.
- **Behavior**: Eligibility adds one condition on top of the single-file bar
  (single logical unit of work, test-gated, backend, re-verifiable today):
  the task's own commit(s) must span 2+ files where the gate cannot pass with
  only one of them reverted-and-fixed - e.g. an implementation file plus its
  test file where the test was *also* added or changed by this task (not a
  pre-existing test, which would make it single-file-equivalent once the impl
  file is reverted), or an implementation file plus a genuine caller-site
  change elsewhere. Apply the corrected vetting checklist from the Isolation
  capability above to *every* touched file, not just one.

### Capability: Comparative dispatch and reporting

#### Feature: Run the identical 6-task set against both engines

- **Description**: Dispatch each multi-file task to Qwen3.8 and to Sonnet from
  independently-verified clean state, exactly as the 2026-08-31 single-file
  round did once corrected.
- **Inputs**: The 6 vetted multi-file tasks; existing dispatch tooling
  (`skills/use-qwen/scripts/qwen-run.sh`, the `use-sonnet` skill's
  `sonnet-run.sh`) - no new dispatch tooling is being built, per the
  Isolation capability's documentation-only scope; a live llama.cpp server
  serving `unsloth/Qwen3.8-27B-GGUF:UD-Q6_K_XL` (operator-started before the
  batch - the Phase 2 preflight gate verifies it and fails loud; nothing in
  this PRD starts a server).
- **Outputs**: Two evidence logs (or one combined log), one score per engine,
  a false-claim audit per transcript.
- **Behavior**: Per task: create or reuse a disposable git worktree under
  `/tmp/qwen-eval-00010/`, `mise trust` it if it carries a mise config,
  revert every touched file per the
  vetted method (whole-file checkout only where the `-L` check found no later
  unrelated history, surgical edit otherwise), verify the baseline gate
  genuinely fails, dispatch to engine A, verify its gate, restore the
  pre-task state again, dispatch to engine B, verify its gate. Never run
  engine A's and engine B's gate concurrently against the same worktree.

#### Feature: Report with a trust-scope recommendation

- **Description**: Turn the two scores into a decision, not just a number.
- **Inputs**: Both evidence logs.
- **Outputs**: A report under `dev/local/audit-results/` and a recommendation
  on Qwen3.8's `--approved-only` scope.
- **Behavior**: For any FAIL, classify it: dropped-a-file (the documented
  historical failure mode - finished one file, silently left the other
  untouched), cross-file-confusion (edited the wrong file, or duplicated logic
  instead of correlating it), or an unrelated logic error. This classification
  is what actually answers "did the multi-file weakness get fixed", not the
  raw pass count alone.

## Structural Decomposition

### Repository Structure

```
skills/
└── use-qwen/
    └── references/
        └── eval-runbook.md          # Extended: isolation-safety checklist
dev/local/
├── audit-results/
│   └── qwen38-vs-sonnet-multifile-<date>.md   # New: comparative report
├── tmp/
│   └── 00010-multifile-eval/         # New: manifest.tsv, prompt files, captured engine output
└── prds/
    └── backlog/
        └── 00010-....md              # This PRD
```

### Module: eval-runbook isolation-safety addendum
- **Maps to capability**: Isolation-safety methodology
- **Responsibility**: Carry the three isolation-safety rules as checklist
  items a future eval run walks instead of remembering
- **Exports**: the checklist section in
  `skills/use-qwen/references/eval-runbook.md` (documentation, no code)

### Module: multi-file eval artifacts
- **Maps to capability**: Multi-file candidate sourcing; Comparative dispatch
  and reporting
- **Responsibility**: Hold the manifest, prompt files, captured engine
  output, and the comparative report the eval produces
- **Exports**: `dev/local/tmp/00010-multifile-eval/` (manifest.tsv, prompt
  files, captured engine output),
  `dev/local/audit-results/qwen38-vs-sonnet-multifile-<date>.md`

No new modules, scripts, or skills - this PRD extends one existing reference
doc and produces evidence artifacts, per the Isolation capability's decision
to keep the fix as documented operator discipline rather than new tooling.

## Dependency Graph

### Foundation Layer (Phase 0)
No dependencies - built first.

- **eval-runbook isolation-safety addendum**: the vetting and dispatch rules
  every later phase applies

### Core Layer (Phases 1-2)
- **multi-file eval artifacts (sourcing, dispatch evidence)**: depends on
  [eval-runbook isolation-safety addendum]

### Integration Layer (Phase 3)
- **comparative report + recorded decision**: depends on [multi-file eval
  artifacts]

## Implementation Phases

### Phase 0: Isolation-safety addendum

**Goal**: The three bugs from 2026-08-31 cannot silently recur.

**Tasks**:

- [ ] Add the three-item isolation-safety checklist to
  `skills/use-qwen/references/eval-runbook.md` (no deps)
  - Acceptance: the checklist names all three failure modes (interrupted-run
    contamination, whole-file-revert erasing unrelated history, concurrent
    same-worktree test runs) and the concrete check or rule that prevents
    each; a reader unfamiliar with the 2026-08-31 incident can follow it
    without needing this PRD as context.

**Exit Criteria**: `eval-runbook.md` diff reviewed and committed.

### Phase 1: Multi-file candidate sourcing

**Goal**: 6 real, rigorously vetted multi-file tasks exist to dispatch.

**Tasks**:

- [ ] Survey `dev/local/prds/done/*.md` across all gita-registered repos for
  candidate multi-file tasks (depends on: Phase 0)
  - Acceptance: at least 10 candidates found, each with a documented
    file list and commit hash, so 6 can be selected for diversity (language,
    repo, shape) - the selected 6 must include at least 3 impl+test-pair
    tasks (decision-rule branch (4) in Phase 3 needs that sample) and at
    least 1 impl+caller task.
- [ ] Vet each candidate against the Phase 0 checklist - every touched file
  checked via `git log --oneline -L`, not just the introducing commit's
  `--stat` (depends on: Phase 1 survey)
  - Acceptance: for each of the 6 selected, a note states which files were
    checked, what (if anything) touched them later, and why that's either
    disqualifying or a confirmed pure refactor; any task where a touched file
    needs a surgical (not whole-file) revert has that surgical diff written
    out before dispatch, not improvised during it.

**Exit Criteria**: A 6-task TSV manifest at
`dev/local/tmp/00010-multifile-eval/manifest.tsv`
(`<prompt-file><TAB><verify-shell-command>` per line, the `run-eval.sh`
format), prompt files beside it, and all revert steps pre-computed and
written down in the same directory.

### Phase 2: Comparative dispatch

**Goal**: Both engines run the identical 6 tasks from genuinely clean state.

**Tasks**:

- [ ] Prepare disposable worktrees for all repos involved under
  `/tmp/qwen-eval-00010/` (inside the unattended write fence, so surgical
  Edit-tool reverts are permitted), `mise trust` each (depends on: Phase 1)
  - Acceptance: every worktree path starts with `/tmp/qwen-eval-00010/` and
    `mise env -s bash` exits 0 in each before any dispatch begins.
- [ ] Gate on engine availability: run
  `~/.agents/skills/use-qwen/scripts/qwen-run.sh --approved-only -P llamacpp8002 --preflight`
  (depends on: Phase 2 worktree prep). The `-P` pin is mandatory: without it,
  auto-detect takes the lowest live port, and a second llama-server serving a
  different approved model would be blessed instead (the runbook's
  pin-the-provider rule; observed live 2026-09-01 with the stale Qwen3.6
  server on :8001).
  - Acceptance: exit 0, and the evidence log opens with the verbatim
    `preflight: healthy (provider 'llamacpp8002', model 'unsloth/Qwen3.8-27B-GGUF:UD-Q6_K_XL')`
    line naming exactly that provider and quant; on any preflight failure the
    phase stops and reports the failure - no dispatch is attempted (the gate
    verifies the operator-started server, it never starts one).
- [ ] Per task: revert, verify baseline fails, dispatch to Qwen3.8, verify
  gate, restore pre-task state, dispatch to Sonnet, verify gate - never
  concurrently for the same worktree (depends on: Phase 2 preflight gate)
  - Acceptance: for every task, the pre-dispatch baseline check is logged as
    failing for *both* engine's turns (proving neither ran against an
    already-fixed file); gate exit codes are logged for both engines; the
    evidence log embeds, per task per engine: the exact dispatch command
    line (every qwen dispatch passes `-P llamacpp8002`, same pin as the
    preflight gate), the engine-identity evidence (qwen-run.sh's first
    `Using provider '...' model '...'` line, which must name
    `llamacpp8002` and the Qwen3.8 quant; for sonnet-run.sh the command
    line showing its model flag), the path of the full captured engine
    output under `dev/local/tmp/00010-multifile-eval/` (file must exist -
    use `qwen-run.sh` stdout capture and `sonnet-run.sh -o`), and the
    verbatim gate output including its exit-code line. Summaries alone are
    not acceptable evidence.
- [ ] Read every transcript from both engines for false claims, the same bar
  as the single-file round (depends on: Phase 2 dispatch)
  - Acceptance: each transcript is marked either clean or flagged, with the
    specific claim and the real gate output it was checked against; each
    audited transcript is the captured output file under
    `dev/local/tmp/00010-multifile-eval/`, cited by path per verdict.

**Exit Criteria**: Two complete evidence logs (or one combined), scores and
false-claim audits recorded for both engines on all 6 tasks.

### Phase 3: Report and decision

**Goal**: A stated, evidence-backed answer on Qwen3.8's multi-file capability
and its autopilot trust scope.

**Tasks**:

- [ ] Write the comparative report under `dev/local/audit-results/`,
  classifying every FAIL as dropped-a-file, cross-file-confusion, or
  unrelated logic error (depends on: Phase 2)
  - Acceptance: the report states both scores, both false-claim counts, and
    a failure classification for every non-pass; it carries decision packets
    in the standing findings-walkthrough shape for the post-batch
    walkthrough - the recorded decision rule in the next task governs the
    interim scope edit, and the user can overturn it on return.
- [ ] Apply the recorded decision rule to the Phase 2 evidence and record
  the outcome (single-file-only / full multi-file / impl+test pairs only)
  wherever `--approved-only` scope is documented (depends on: Phase 3
  report). Decision rule (user-approved 2026-09-01; applied mechanically,
  overturnable in the post-batch walkthrough): (1) any Qwen3.8 false claim
  in any transcript -> keep single-file-only, full stop; (2) a task whose
  gate fails for BOTH engines is excluded from scoring as a suspect task and
  named in the report - if fewer than 5 scored tasks remain, keep
  single-file-only (insufficient sample); (3) zero dropped-a-file failures
  AND at most one scored Qwen3.8 fail -> extend to full multi-file; (4)
  else, if every impl+test-pair task passed cleanly (no gate fail, no
  dropped-a-file, no false claim among them; the Phase 1 manifest guarantees
  at least 3 such tasks) -> extend to impl+test pairs only; (5) else keep
  single-file-only. Sonnet's score is reported as frontier context and gates
  nothing beyond the both-fail exclusion in (2).
  - Acceptance: `SKILL.md`'s Model Selection section reflects the rule's
    outcome and its evidence, matching the fact-only-then-hand-authored-rationale
    pattern `promote-default.sh` already uses; the report names which rule
    branch fired.

**Exit Criteria**: The decision is recorded and evidenced, not left as an
implicit "well it passed once."

## Test Strategy

### Critical Scenarios

- **Happy path**: a clean impl+test multi-file task, both engines pass,
  neither drops a file.
- **Happy path**: `mise trust` pre-flight prevents the exact silent-kill
  failure mode this session hit on the ddb, gems, and claude-warden
  worktrees.
- **Edge case**: a candidate task's non-introducing file (e.g. the test file)
  has unrelated later history - caught by the Phase 0 checklist during
  vetting, before it ever reaches dispatch.
- **Edge case**: an interrupted dispatch mid-run - the Phase 0 checklist's
  first item is followed: re-verify pre-task state before trusting any
  re-dispatch, exactly where the 2026-08-31 run failed to.
- **Failure case (the one this PRD exists to observe)**: an engine edits one
  file correctly and leaves the other untouched or wrong - classified as
  dropped-a-file in the Phase 3 report, not just scored as a bare FAIL.

## Risks

- **Multi-file candidates are scarce or hard to isolate cleanly**: the
  single-file round already found that most "single-commit" tasks in
  actively-developed repos have follow-up commits; multi-file tasks may be
  scarcer still or harder to vet. Mitigation: Phase 1 asks for 10+ candidates
  to select the best 6 from, same margin the single-file round used.
- **The isolation-safety checklist is followed loosely under time pressure**:
  the exact failure mode that produced the ddb contamination in the first
  place. Mitigation: Phase 2's acceptance criteria require the baseline-fails
  log for *both* engines' turns, which cannot be produced after the fact if
  the check was skipped.
- **A "multi-file fail" gets mis-scored as a plain logic bug**: would hide
  the actual signal this PRD is built to surface. Mitigation: Phase 3's
  explicit three-way failure classification, not a bare pass/fail count.
- **Re-running two full model-agentic dispatches per task (12 total) plus
  their gates is slow**: the single-file round's Rust task alone took ~16
  minutes per gate run; multi-file tasks may be slower still. Mitigation:
  none proposed here beyond patience and background dispatch - not a
  correctness risk, just a time-budget one to flag before starting.
