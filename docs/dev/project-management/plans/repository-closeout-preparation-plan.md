# Repository closeout: preparation while Claude capacity is unavailable

Created: 2026-10-30. Status: ready for a new preparation session.

## Purpose and authority

Continue the useful, non-Claude-dependent parts of Stage 1 now: diagnose Windows
failures, inspect migration compatibility, rehearse integration, and prepare
implementation requirements and a concrete Windows CI proposal.

This supplements `repository-closeout-plan.md`; it does not replace its gates.
The user explicitly requested this additional preparation session after the
capacity-blocked attempt. Do not wait for the quota reset to begin preparation.
The previous handoff's wait instruction applies to retrying the required Claude
execution, not to this preparation session.

Do not implement production fixes, ship new regression tests, invoke the final
review workflow, advance autopilot state, publish, or begin Stage 2. Disposable
reproduction fixtures and diagnostic scripts are permitted. A preparation PASS
does not mean the Stage 1 exit gate passes. Even if capacity returns during this
session, finish preparation and hand off rather than expanding the scope.

## Starting evidence to refresh

- Last recorded local master: `0035e628f013bbe6147da9d78ac1a19d98c754b9`, clean.
- Tested source baseline: `9d1a6e681faab0f97af99f8dd9f471ba1a8becc5`.
- Remote master: `6b52b2ab74388753dce2c89a76f2915e2cdae124`.
- PR #17: `9249695b334f2a894bda8e016d974480cece918e`.
- PR #15: `34a06221d84b09d3b41fe9b40eca590086b5e73d`.
- PR #16: `78596dbb19dc22b0fd511ab903f03834fe68163c`.
- Original PRD 00133 state remains batch `202610271200`, build/build, zero of
  one task complete. Its hashes are in the execution record.
- Baseline suite: 4,258 passed, nine skipped, two archive warnings.
- Warning-as-error archive suite: two failed, 53 passed.
- Disposable archive probe: compatibility path changed an outside sentinel;
  filtered path refused the same crafted archive.
- Node 26.13.0: meeting-template build, byte-for-byte freshness, and 60 tests pass.
- Claude probe failed with a weekly limit, reset reported as
  2026-11-01 10:00 Europe/Prague. Do not repeat that probe before reset.

This plan may itself be an uncommitted file or a later documentation commit.
Inspect and preserve it; do not require the checkout to match the historical
tip exactly. Reconcile all newer changes before selecting a diagnostic base.

## Execution order

### 1. Establish custody and scope

Read global instructions, repository `AGENTS.md`, the main closeout plan, and
`audit-results/repository-closeout-execution.md`. Read held PRDs 00155–00158,
the excluded PRD 00133, and the migration branch's reserved PRD 00159.

Refresh refs, PR heads and states, CI, worktrees, stashes, and process ownership.
Preserve published ancestry, held branches, private recovery files, and active
migration reference material. Verify the 62-file preservation manifest at
`docs/dev/tmp/closeout-stage-1-20261030/preservation-before.json` when present.
If missing, record that limitation and capture a new baseline without claiming
it proves earlier preservation.

Do not clear locks because they are empty or old. The prior session's process
enumeration was denied; use supported ownership checks and record unresolved
ownership. Do not bypass an operating-system or tool refusal.

Use the current host for preparation. No Claude reviewer or substitute reviewer
is needed for investigation. Do not treat compatibility inspection as the
mandatory independent review. Do not launch autopilot or touch its original
state. Default to sequential work; concurrent editors, if separately authorized,
must have distinct worktrees and artifact directories.

### 2. Diagnose every Windows failure

Retrieve complete logs for the latest relevant runs, refreshing their SHAs:

- Master baseline: run `41032617118`, 61 failed, 4,166 passed, 40 skipped.
- Migration baseline: run `41030058506`, 65 failed, 4,062 passed, 43 skipped.

The prior `*-failed-excerpt.log` files are truncated. Do not use them as a
complete failure inventory. Capture logs through supported tooling into ignored
`docs/dev/tmp/closeout-preparation-<timestamp>/`; shell redirection into development
artifact paths is rejected by the local hook.

Build a failure matrix with one row per failed node ID and run. Group shared
causes, but reconcile the row counts against each run's test summary. For every
row or shared cause, record:

- Exact run, SHA, node ID, traceback location, assertion, and log location.
- Relevant production and fixture code, with line references.
- Proven root cause or explicitly labelled hypothesis.
- Smallest supported repair and proposed owner/files.
- Regression design and what must fail before the repair.
- Which evidence is local, platform-simulated, or real Windows evidence.

Cover braid link identity and cleanup; PRD path parsing; docket errors and path
rendering; memory write bytes; glean separators; illegal Windows filenames and
manifest carriage returns; POSIX-only permission fixtures; Qwen archive links,
containment, Git checkout bytes, MSYS/native paths, output sizes, and warmup
timeouts. Do not assume these groupings explain every failure.

Use disposable reproductions where helpful. Distinguish OS constraints from
application defects and fixture assumptions. Do not propose weakening checks,
disabling Windows, broad timeout increases, or unexplained skips. For genuine
platform-inapplicable behavior, specify equivalent coverage and rationale.
Record remaining unknowns that require a Windows runner.

### 3. Prepare the archive implementation contract

Consolidate held findings 00155–00158 into one proposed implementation target
without changing their lifecycle status or allocating a new identifier.
Reuse existing disposable probe evidence unless a new question requires rerunning it.

Write an acceptance matrix covering both available and absent `tarfile.data_filter`:
symlink ancestors and chains; traversal; absolute and Windows-specific paths;
duplicate members; landing collisions; hardlinks; special files; modes; ownership;
refusal before outside writes; cleanup of partial templates; warning-as-error
behavior; and supported valid archives, executable files, and safe links.

Identify the supported Python versions and the required runtime-specific checks.
Specify safe compatibility behavior and justify any deliberate refusal against
valid-input requirements. Describe regression cases as requirements or disposable
fixtures; do not modify shipped code or tests. Coordinate archive ownership of
`eval_harness/trees.py` with proposed Windows changes to the same file.

### 4. Inspect the seven migration skills

Inspect PR #17's actual eight-commit diff and all seven skills:
build-mcp-server, create-adr, document-abap-solution, explore-abap-solution,
publish-confluence-docs, review-abap-solution-documentation, and write-abap-specs.

Check declared dependencies, portable paths, shipped helpers, runtime/package
requirements, tests and discovery, compatibility classification, changelog,
validator expectations, and interactions with the current base. Use current
primary documentation when a version-dependent claim requires verification.
Do not run skill actions that publish externally merely to test availability.

Record findings with severity, concrete evidence, affected files, proposed
repair, and verification. Keep PRD 00159 reserved for the validator follow-up.
Prepare the precise PR #17 description correction from 00150 to 00159 without
editing remote metadata. This inspection is input to Stage 1 and Stage 2, not
a substitute for either gate.

### 5. Inspect dependencies and rehearse integration

Evaluate setup-uv 10.3.3 and Node 26 separately. Preserve the existing Node build,
freshness, and 60-test evidence when its inputs match; rerun only for changed
inputs or unresolved questions. Distinguish old PR CI from corrected-base CI.
Record npm's two low-severity findings without unrelated dependency upgrades.

Use Git's non-publishing merge inspection first. If checkout-based inspection is
needed, create an owned local rehearsal branch and separate worktree from the
measured base. Never switch, reset, or merge into the user's master checkout.

The intended production order is still fixes → #17 → #15 → #16. Fixes do not
exist yet, so label any current-base rehearsal **diagnostic only**. Record
input SHAs, merge bases, conflicts, clean tree IDs where available, and expected
changes at each step. Do not invent a corrected-base tree or call a diagnostic
tree the prepared integration candidate.

Do not resolve semantic conflicts in this session. Capture conflicting paths
and proposed resolutions. Abort only this session's own unfinished merge after
preserving evidence. If conflicts block an ordered rehearsal, mark downstream
trees unmeasured and inspect later PR diffs separately. Follow repository checks
before any local commits; do not bypass hooks to manufacture rehearsal commits.

Produce a conditional merge or rejection recommendation for each dependency,
with supporting evidence and remaining gates. Do not close or merge PRs.

### 6. Prepare tasks and the Windows CI proposal

Prepare an implementation packet in the durable preparation report. Map every
failure and acceptance criterion to an existing PRD/finding, proposed task,
owned files, dependencies, and exact verification commands. Separate shared-file
work and ordering constraints so future implementation lanes cannot race.
Leave formal PRD selection, task execution, and lane routing to the installed
autopilot workflow when execution resumes.

Prepare a concrete Windows evidence proposal: existing workflow, proposed
temporary branch/ref, exact publish/dispatch commands, expected jobs and matrix,
artifact retrieval, and eventual cleanup. Label any candidate SHA still unknown.
The current workflow runs automatically on master pushes and PRs; a temporary
branch push alone needs the appropriate explicit workflow dispatch or PR route.
Explain the publication and CI consequence of the selected route.

Do not request approval for a placeholder candidate. Record that approval must
be obtained once the corrected candidate and exact action are ready. Do not
push, dispatch, open a PR, edit metadata, or delete remote branches now.

### 7. Record evidence and hand off

Write `audit-results/repository-closeout-preparation.md` with the matrices,
findings, task packet, diagnostic merge results, dependency recommendations,
CI proposal, remaining unknowns, and acceptance status. Keep raw logs and
fixtures ignored; keep public reports free of personal or private material.

Append a separate preparation entry to `repository-closeout-execution.md`.
Preserve the historical blocked attempt and distinguish fresh measurements from
reused evidence. Record tested SHAs, runtimes, commands, counts, skips, times,
log locations, branch/worktree custody, and original-state preservation.

Remove only this session's safely disposable rehearsal worktrees after saving
their evidence. Retain any still-needed worktree with its branch, purpose, and
recovery instructions. Do not clean unrelated work or private backups.

Write and print `docs/dev/tmp/handoff-closeout-stage-1-prepared-<timestamp>.md`.
Use one numbered list, commands in execution order, preconditions first, and
instructions of at most 20 words. State whether preparation passed, but keep
Stage 1 blocked until implementation and its complete exit gate pass.
End the session without invoking review or starting Stage 2.

## Preparation exit criteria

- Every Windows failure is accounted for, including explicitly unresolved causes.
- Archive acceptance requirements cover all four held findings and valid controls.
- All seven migration skills and their dependencies have inspection evidence.
- Both dependency PRs have separate, justified conditional recommendations.
- Diagnostic integration conflicts and unmeasured trees are explicit.
- Implementation ownership and the proposed Windows CI action are concrete.
- Preservation checks, execution record, and same-stage handoff are complete.

If a preparation item is blocked, finish independent items and hand off the
specific gap. Do not convert this preparation session into unreviewed repair work.

## New-session initiation prompt

```text
1. Open the agent-skills repository in a fresh session.
2. Read AGENTS.md and docs/dev/project-management/plans/repository-closeout-preparation-plan.md.
3. Execute only that preparation plan without waiting for Claude capacity.
4. Preserve published history, held work, private backups, and PRD 00133 state.
5. Record evidence and print the Stage 1 implementation handoff.
6. Stop before implementation, independent review, publication, or Stage 2.
```

## Unresolved questions

None requiring user input before preparation. Windows-only unknowns, remote
approval, and future runtime capacity must remain explicit in the handoff.
