# Repository closeout: three execution sessions and independent verification

Created: 2026-10-30. Status: ready for Stage 1.

## Outcome and scope

Complete implementation and integration in three execution sessions.
Use a fourth, independent session to verify the result.
The planning session does not count as an execution session.

The user's requirement is:

> Expected is that after three sessions the whole plan is implemented. Fourth session will verify that

Include archive safety, Windows CI repairs, migration PR #17, dependency PRs #15/#16, and final repository hygiene.
Cover related archive findings 00155–00158 together, avoiding separate overlapping fixes.
Exclude PRD 00133 implementation and unrelated held PRDs.
Preserve their work and leave PRD 00133 ready for a later session.

Three sessions is the intended path, not permission to bypass a failed gate.
Unavailable reviewers, denied approvals, unexpected defects, or changing remote heads can require another session.
Record a blocked outcome instead of claiming completion or silently dropping work.

## Verified starting state

Treat this snapshot as historical evidence. Refresh it at every stage entry.

| Item | Observed state on 2026-10-30 |
|---|---|
| Checkout | `~/git/src/github.com/buvis/agent-skills`, branch `master` |
| Local and remote master | `6b52b2ab74388753dce2c89a76f2915e2cdae124`; clean before this plan |
| History | 147 original published ancestors, 12 grouped commits, one hygiene commit |
| Shared migration base | `6091e02c41e823f3bd061434edf8bd389ffea8d0` |
| Migration PR #17 | `feat/skill-migration-bundle`, `9249695b334f2a894bda8e016d974480cece918e`; eight commits |
| Dependency PR #15 | setup-uv 10.3.3, `34a06221d84b09d3b41fe9b40eca590086b5e73d` |
| Dependency PR #16 | Node 26, `78596dbb19dc22b0fd511ab903f03834fe68163c` |
| Master CI | Run `41032617118`, completed/failure at `6b52b2a`; inspect current failed-job logs |
| Master Windows result | 61 failed, 4166 passed, 40 skipped; all other jobs passed |
| Migration CI | Run `41030058506`, Windows failed; Linux 3.10/3.13, lint, Node, and shell passed |
| Migration Windows result | 65 failed, 4062 passed, 43 skipped; do not reuse the older 60-failure baseline |
| Existing autopilot state | Stopped batch `202610271200`; PRD 00133, build phase, zero tasks complete |
| Local recovery checks | 4258 passed, 9 skipped during this conversation; not rerun for this plan |
| Plan-time checks | Ruff passed; `braid --check` reported zero drift |
| Recovery material | `.git/recovery-20261030/`; private, local, never stage or publish |

Read these durable sources:

- `AGENTS.md`: repository and global authority.
- `docs/dev/project-management/audit-results/unpublished-review-2026-10-30.md`: findings and retained branches.
- `docs/dev/project-management/audit-results/brush-report.md`: cleanup decisions.
- `docs/dev/project-management/meta/project-capsule.md`: component boundaries; refresh stale GitHub facts.
- Held PRDs 00155–00158: coverage, metadata filtering, warnings, and symlink escape findings.
- `docs/dev/project-management/prds/wip/00133-transcript-judge-inherits-tools-v1.md`: excluded work to preserve.

## Shared execution rules

1. Load global instructions and repository `AGENTS.md` before changing files.
2. Refresh branches, remote heads, PR states, CI results, worktrees, stashes, and active processes.
3. Preserve published history, including the 147 ancestors the user explicitly chose to retain.
4. Treat the entire published master history as immutable; do not repeat the earlier filter-branch operation.
5. Keep recovery bundles, held-work branches, and active migration reference material.
6. Give every concurrent editor a separate worktree and branch.
7. Give every autopilot execution an explicit target and isolated state store.
8. Verify state paths resolve separately before starting concurrent runs.
9. Preserve the existing PRD 00133 state; never select it through a default autopilot invocation.
10. Use the runnable installed autopilot for end-to-end PRD execution and its code-selected lane and roster.
11. Treat `docs/plugin-skills/` as documentation, not an installed executable plugin.
12. Check required reviewer availability before depending on the three-session schedule.
13. Preserve every mandated review lens, fresh-session boundary, implementation-model guard, and workflow cap.
14. Do not replace a required unavailable reviewer with an invented fallback or silently reduce the roster.
15. Execute routine reversible fixes and checks under standing authorization.
16. Prepare external merges, closures, metadata edits, and deletions before requesting any missing approval.
17. Reuse explicit approvals within their recorded scope; do not ask for the same approval again.
18. Do not infer blanket remote-merge or force-push approval from this planning request.
19. Use normal fast-forward pushes where authorized; keep unreviewed production changes off master.
20. Record failures honestly; skips and stale test results are not passes.

## Evidence and handoff contract

Maintain one execution record:
`docs/dev/project-management/audit-results/repository-closeout-execution.md`.
Record separate Stage 1, Stage 2, Stage 3, and Verification entries.
Keep bulky logs and temporary reproduction fixtures under ignored `docs/dev/tmp/`.
Keep acceptance criteria, review decisions, and evidence summaries in the tracked execution record.

Every stage must record:

- Goal, completed work, remaining tasks, and settled decisions.
- Exact branch tips, base commits, worktree paths, dirty files, and stashes.
- Target PRDs, isolated state paths, and the original PRD 00133 preservation check.
- Candidate commit order and the source/test/config tree expected at each integration step.
- Checks, exact tested SHAs, platform/runtime, result counts, skips, timestamps, and log locations.
- Review roles, their actual availability, coverage, findings, and adjudications.
- Remote actions, approvals, PR heads, CI run URLs, and unresolved blockers.
- Failed approaches to avoid and any unverified assumptions.

At each boundary, write a paste-ready numbered handoff under `docs/dev/tmp/`.
Use `handoff-closeout-stage-N-YYYYMMDD-HHMM.md` for the destination stage.
Supplement the destination initiation prompt with the measured state above.
Use one instruction per sentence and at most 20 words per instruction.
Place preconditions before commands that require them.
Print the handoff, then end the turn. Do not start the next stage.
When blocked, address the handoff to a retry of the same stage and name the blocking condition.

## Stage 1 — implement and prepare integration

Owner: a new implementation session. No final review or production integration in this session.

Parallel work is allowed after preflight:

| Lane | Work | Isolation |
|---|---|---|
| A | Archive containment, safe metadata handling, compatibility behavior, regression tests | Dedicated worktree; owns `eval_harness/trees.py` and its focused tests |
| B | Diagnose and repair the actual Windows CI failures | Dedicated worktree; coordinate overlapping Qwen paths with lane A |
| C | Review migration/dependency diffs and prepare compatibility changes | Read-only first; separate worktree for necessary edits |

Use inherited models unless the applicable workflow requires otherwise.
Use parallel agents only when the executing host supports them and the workflow permits them.
The coordinator owns integration conflicts, shared documentation, and the combined candidate.
Never let two lanes edit the same files in a shared checkout.

Execute these tasks:

1. Create the execution record with current repository and remote evidence.
2. Establish explicit requirements and task ownership using existing PRDs before allocating new identifiers.
3. Reserve PRD 00159 for the migration validator follow-up; inspect all relevant branches before allocating identifiers.
4. Establish isolated autopilot state without replacing the stopped PRD 00133 state.
5. Reproduce the archive escape inside disposable directories with an outside sentinel.
6. Implement safe behavior both with and without `tarfile.data_filter`.
7. Preserve supported Python versions and valid inputs; justify any deliberate refusal behavior against the requirements.
8. Cover symlink ancestors, traversal, absolute paths, duplicates, landing collisions, hardlinks, special files, modes, and ownership metadata.
9. Assert refusals happen before outside writes and leave no accepted partial template.
10. Test omitted-filter warnings as errors and retain valid archive controls.
11. Diagnose current Windows failures from actual logs, including path, symlink, line-ending, and timeout behavior.
12. Repair causes without disabling the Windows lane, weakening assertions, or converting failures into unexplained skips.
13. Review the seven migration skills and their declared dependencies against the corrected base.
14. Evaluate setup-uv 10.3.3 and Node 26 separately, including the meeting-template build and freshness check.
15. Prepare a supported merge or rejection recommendation for each dependency PR.
16. Assemble a disposable combined candidate in the intended integration order: fixes, PR #17, PR #15, PR #16.
17. Resolve anticipated conflicts and compatibility issues in this session, before independent review.
18. Record expected trees and exact PR heads for every proposed integration step.
19. Run focused regressions, the required full suite, skill validation, lint, braid checks, and relevant Node/shell checks.
20. Obtain real Windows evidence through an available runner using the required approval for any new remote action.
21. Preserve the complete test matrix; report dependency-related skips explicitly.
22. Commit the prepared implementation and record its tested SHAs.
23. Set the workflow's next phase through its supported transition mechanism.
24. Write the Stage 2 handoff and stop before invoking the review phase.

Exit gate: implementation and anticipated integration repairs are complete, checks pass on the candidate, and review inputs are prepared.
Do not mark the PRDs reviewed or complete merely because implementation checks pass.
If required Windows evidence or runtime capacity is unavailable, record the gap and a blocked Stage 1 handoff.

### Stage 1 initiation prompt

```text
1. Open ~/git/src/github.com/buvis/agent-skills.
2. Read AGENTS.md and docs/dev/project-management/plans/repository-closeout-plan.md.
3. Verify the plan's starting state against the current repository and remote.
4. Execute only Stage 1 of the plan.
5. Check required runtime and reviewer availability before dispatching work.
6. Preserve published history, held-work branches, private backups, and PRD 00133 state.
7. Use separate worktrees and isolated state for concurrent implementation lanes.
8. Complete the archive, Windows, and PR compatibility work specified by Stage 1.
9. Run the required checks against the combined candidate.
10. Update docs/dev/project-management/audit-results/repository-closeout-execution.md with exact evidence.
11. Write and print the Stage 2 initiation prompt with the measured handoff state.
12. Write a same-stage blocked handoff if the Stage 1 exit gate fails.
13. Stop and end the turn; do not invoke review or begin Stage 2.
```

## Stage 2 — independent review and bounded rework

Owner: a fresh review session, separate from Stage 1's implementation coordinator.
The review must cover the archive fix, Windows repairs, migration changes, dependencies, and combined integration candidate.

1. Verify Stage 1's exit gate and exact candidate SHAs before starting review.
2. Load the installed review workflow and its code-selected roster for each explicit target.
3. Preserve consensus, PRD-only blind, and doubt/de-slop lenses, including the required R1–R5 rubric.
4. Apply any additional reviewer requirement triggered by Codex-authored implementation.
5. Give blind reviewers requirements only, excluding implementation narratives, diffs, and earlier review conclusions.
6. Run `/autopilot:review-work-completion` from this fresh session using the actual installed runtime.
7. Review each target separately, then inspect the combined candidate for interactions and conflict-resolution mistakes.
8. Resolve supported in-scope findings through isolated implementers and the workflow's bounded rework process.
9. Run every mandatory lens in each review cycle; preserve the workflow's convergence and deferral rules.
10. Re-run affected checks and the required final gates after rework.
11. Record evidence before closing held findings or changing PRD status.
12. Freeze the approved integration order, candidate trees, PR heads, and test evidence.
13. Prepare concrete remote actions and identify which still require approval.
14. Write the Stage 3 handoff and stop without publishing or merging.

Exit gate: mandatory reviews pass, no unresolved release blocker remains, and the exact integration candidates are approved.
Keep rework inside Stage 2's prescribed isolated review/build process where supported.
If required capacity or the review cap blocks convergence, stop with a same-stage blocked handoff.
Do not move the review into Stage 3 or rename a blocked implementation as ready.

### Stage 2 initiation prompt

```text
1. Open ~/git/src/github.com/buvis/agent-skills in a fresh session.
2. Read AGENTS.md and docs/dev/project-management/plans/repository-closeout-plan.md.
3. Read the Stage 1 handoff and repository-closeout-execution.md in the audit-results directory.
4. Verify Stage 1's exit gate and exact candidate SHAs.
5. Execute only Stage 2 through the installed review workflow.
6. Preserve all mandatory lenses, blind context isolation, and implementation-model safeguards.
7. Review each target and the combined integration candidate.
8. Resolve supported findings through isolated implementers within the workflow's existing caps.
9. Record final review decisions, test evidence, approved trees, PR heads, and required remote approvals.
10. Write and print the Stage 3 initiation prompt with the measured handoff state.
11. Write a same-stage blocked handoff if the Stage 2 exit gate fails.
12. Stop and end the turn; do not publish or begin Stage 3.
```

## Stage 3 — integrate, publish, and close out

Owner: a new integration session. Only this session owns final remote changes.

1. Verify the reviewed candidate, approvals, remote heads, and proposed integration order.
2. Reconcile harmless metadata drift; return unexpected source, test, or configuration changes for fresh review.
3. Present one concrete batch of remote actions when explicit approval is still required.
4. Publish the approved fixes through normal fast-forward updates or the repository's approved PR route.
5. Wait for all required CI jobs on the published fix tip, including Windows.
6. Stop integration if CI contradicts the reviewed evidence; do not implement unreviewed repairs on master.
7. Integrate PR #17 using the reviewed candidate and record its final merge SHA.
8. Correct its follow-up PRD reference to 00159 in the approved metadata update.
9. Resolve PR #15, then PR #16, using the reviewed merge or explicitly approved closure decision.
10. Verify the expected candidate tree and required CI after each integration step.
11. Confirm the final remote master contains the intended features, security behavior, and dependency versions.
12. Delete only approved, verified-merged remote branches and safely disposable local branches.
13. Retain unrelated held-work branches and private recovery evidence.
14. Remove this plan's temporary worktrees and files without disturbing other sessions or active reference material.
15. Update the capsule, execution record, linked PRD statuses, and documented CI results.
16. Preserve PRD 00133 and update its resume baseline through the supported state mechanism when necessary.
17. Commit closeout records and ensure the intended final commits are published.
18. Leave this plan available until the fourth session verifies completion.
19. Write the Verification session handoff and stop.

Exit gate: all in-scope implementation is integrated; required final CI is green; all three PRs have evidenced final dispositions.
Only independent verification remains. An unapproved action or unresolved PR is not a completed disposition.
Do not declare implementation complete if new code needs another review cycle.

### Stage 3 initiation prompt

```text
1. Open ~/git/src/github.com/buvis/agent-skills in a new session.
2. Read AGENTS.md and docs/dev/project-management/plans/repository-closeout-plan.md.
3. Read the Stage 2 handoff and repository-closeout-execution.md in the audit-results directory.
4. Verify the review gate, approved trees, remote heads, and existing approvals.
5. Execute only Stage 3 in the reviewed integration order.
6. Obtain missing approval for the prepared external-action batch before executing those actions.
7. Publish reviewed fixes and verify their required CI before integrating the feature and dependency PRs.
8. Reject unexpected source changes from integration and return them for fresh review.
9. Complete approved branch cleanup and preserve PRD 00133's resumable state.
10. Record final SHAs, PR dispositions, CI URLs, approvals, and remaining work.
11. Write and print the Verification initiation prompt with the measured handoff state.
12. Write a blocked handoff if any implementation or integration remains incomplete.
13. Stop and end the turn; do not perform the independent verification yourself.
```

## Session 4 — independent verification

This session verifies the completed plan. It does not silently repair production code.
It may write verification evidence and archive the executed plan after a pass.

1. Fetch current remote state without changing production files.
2. Read the plan and execution record, then independently check their assertions.
3. Map every acceptance criterion to code, tests, review evidence, and final published commits.
4. Reproduce archive refusal and safe-input controls on both filter paths in disposable directories.
5. Confirm unsupported or unsafe compatibility behavior fails closed without outside writes or unsafe metadata application.
6. Verify warning-as-error coverage and supported Python behavior.
7. Verify final-master CI results for Windows, Linux, lint, shell, and relevant Node/template checks.
8. Re-run the required local verification against the final tip and distinguish every skip from a pass.
9. Verify PR #17 and dependency PRs #15/#16 have the approved dispositions and matching code/version results.
10. Verify published ancestry remains preserved and the private migration plan is absent from branch histories.
11. Verify the working tree, temporary worktrees, retained branches, and PRD 00133 state match the recorded disposition.
12. Write `docs/dev/project-management/audit-results/repository-closeout-verification.md` with PASS or FAIL and exact evidence.
13. On PASS, archive this executed plan under `docs/dev/project-management/audit-results/repository-closeout-plan-completed.md`.
14. Commit the verification record and completed-plan move through the permitted normal route.
15. On FAIL, identify the failed criterion and provide a corrective handoff without marking the plan complete.
16. Stop after reporting the verification result.

### Verification initiation prompt

```text
1. Open ~/git/src/github.com/buvis/agent-skills in a fresh independent session.
2. Read AGENTS.md and docs/dev/project-management/plans/repository-closeout-plan.md.
3. Read the Stage 3 handoff and repository-closeout-execution.md in the audit-results directory.
4. Execute only Session 4 verification.
5. Verify final remote SHAs and CI results directly rather than trusting handoff summaries.
6. Reproduce the security acceptance criteria and run the required checks on the final tip.
7. Verify PR outcomes, preserved ancestry, repository hygiene, and PRD 00133 state.
8. Write the verification report with a justified PASS or FAIL.
9. Archive the executed plan only after a PASS.
10. Provide a corrective handoff after a FAIL; do not silently repair production code.
11. Stop and end the turn after reporting the result.
```

## Completion checklist

- [ ] Stage 1: archive, Windows, and compatibility implementation prepared and tested.
- [ ] Stage 2: mandatory independent reviews and bounded rework completed.
- [ ] Stage 3: reviewed implementation published, PRs resolved, required CI green, and hygiene complete.
- [ ] Session 4: independent verification passed and the executed plan archived.

## Unresolved questions

None about scope or session order.
Reviewer capacity, current remote heads, and missing external approvals must be verified during execution.
