---
default_model: opus
model_tier_rationale: full-suite Windows portability includes persisted-directory publication and destructive-path protection
catchup: force
design: run
---

# Run the entire Python suite on Windows

## Overview

### Problem Statement
CI runs Python tests only on Ubuntu, while README describes Windows behavior.
The previously proposed Windows job copied checkout/setup-uv but omitted tools
and assumed POSIX fixtures would work unchanged. The September 5 backlog review
found native-executable, permission, symlink and path assumptions, plus two
product defects: brush compares native paths with Git slash paths, and memory
publication replaces a reserved directory using an operation unsupported on Windows.
Source: `dev/local/audit-results/agoge-2026-08-31.md`, finding 40, expanded by the
2026-09-05 backlog review. User decision: support the entire Python suite, including
required tool provisioning and portability fixes, rather than narrow the job.

Scope includes all tests collected by the repository's pytest configuration and
repo-level Python tests introduced by earlier PRDs. Standalone shell suites retain
their existing Linux job; Bash integrations collected by pytest also run on Windows.
Re-check the listed defects before edits; already-correct behavior is retained
and reported, never replaced to force an obsolete premise.

Parked 2026-10-17 (backlog review): the `windows` job, `.gitattributes`, the
testpaths, the root `conftest.py` fixtures, brush path identity and proposal
publication have all shipped; what remains is an attended push-fix-rerun loop
over the 63 failures the `windows` job reports at `43f9600` (braid 13,
braid_check 7, ground_prd 2, distil-memory CRLF 9, glean 2, sweep-fix
`os.geteuid` 2, use-qwen 27), which no unattended session can bound. The Ubuntu
matrix is red on glean too. Unpark for an attended run.

Update 2026-10-25: 60 failures at b2e6fcd (glean down to 1, the Ubuntu matrix
is green again), plus one intermittent failure that the next run showed and the
previous did not: `test_the_warmup_budget_runs_down_across_every_earlier_segment`
in skills/use-qwen/scripts/test_run_eval_vet.py raises WinError 32 (file in use)
on its temporary output file after the warm-up timeout kills the child.

Update 2026-11-01 (repository closeout, Stage 1): unparked for the attended
closeout. The current failure set is the 126-row matrix in
`docs/dev/project-management/audit-results/repository-closeout-preparation.md`
(Windows appendix). It holds 61 failures at master run 41032617118 and 65 at
PR #17 run 41030058506, grouped into causes B1-B2, P1-P2, D1-D3, G1, U1-U2, S1
and Q1-Q8. That report's "Windows diagnosis and ownership" table gives each
cause's minimal repair and the regression that must detect the old behavior.
The custody addendum
`docs/dev/project-management/audit-results/repository-closeout-preparation-session-123534.md`
refines Q3 (`eval_harness_run_helpers.py` pwd logging) and Q4-Q5. Rules for this run:

- Causes Q4, Q5 and Q6 belong to PRD 00160. This PRD never edits
  `skills/use-qwen/scripts/eval_harness/trees.py`,
  `skills/use-qwen/scripts/test_eval_tree_links.py` or
  `skills/use-qwen/scripts/test_eval_tree_state.py`.
- Do not edit `skills/distil-memory/scripts/funnel.py` (PRD 00133 owns it).
- Hypothesis rows (B1, Q2, Q4, Q8) get a portable repair plus a local
  regression that simulates the Windows behavior. Mark each one unverified
  until the native run confirms it.
- This build makes no push, branch publication or workflow dispatch. The
  closeout coordinator runs the native Windows job once, on the combined
  candidate, after explicit user approval of its exact SHA.

### Target Users
Maintainers changing portable skills or Braid, and Windows users relying on the README.

### Success Metrics
- The complete configured Python suite passes on Ubuntu and native windows-latest at the changed commit.
- No Windows-wide skip, deselection, xfail, continue-on-error or reduced testpath hides a failing capability.
- Real resolver, symlink, path-protection and publication regressions retain their assertions.
- README's command uses one backslash, and its claims match the coverage actually exercised.

## Functional Decomposition

### Capability: Complete Windows verification
Run the same Python collection on both operating systems with explicit prerequisites.

#### Feature: Native Windows job and toolchain
- **Description**: Add a Windows job alongside the current jobs, including the Node job from PRD 00022.
- **Inputs**: .github/workflows/ci.yml, pyproject.toml, uv, mise, rg, ast-grep and Git Bash.
- **Outputs**: jobs.windows on windows-latest with a full `uv run --python 3.13 pytest` step.
- **Behavior**: Use the workflow's current checkout/setup-uv versions; install native Windows
  mise and its managed rg/ast-grep. Preserve the resolver's PATH preference and mise fallback
  tests; provision ast-grep through mise rather than accidentally selecting an unrelated shim.
  Make Git Bash and its utilities callable from Python. Set PYTHONUTF8=1 for Python children
  and ensure shell files use LF via .gitattributes. Check real file/directory symlink creation
  before testing; an unavailable required runner capability fails with a named diagnostic.
  Existing jobs survive; assert their presence, not a fixed total job count.
  Extend pytest testpaths to include repo-level scripts tests from 00020, retaining tests and skills.

#### Feature: Portable fixtures without coverage loss
- **Description**: Remove host assumptions while preserving the behavior each test observes.
- **Inputs**: resolver/search, Bash assembly, unreadable-file, symlink, home and path fixtures.
- **Outputs**: The same regression behaviors execute on Windows and POSIX.
- **Behavior**: Replace extensionless shebang stubs with platform-runnable fixtures and keep
  real subprocess integration, tool preference/fallback/cache and timed-search cases.
  Use os.pathsep and controlled search roots; isolate HOME on POSIX and the effective Windows
  home variables when testing Path.home. Simulate denied reads at the filesystem boundary
  instead of assuming chmod(0) prevents access. Keep actual symlink containment tests runnable.
  Convert native paths passed to Git Bash as needed, including spaces. Construct malicious
  backslash-path fixtures appropriately for the host without weakening rejection checks.
  Compare platform-native diagnostics or normalize only their path representation.
  Preserve existing strict defect xfails outside this PRD; add no new platform skips.
  Existing optional tree-sitter/local-corpus skips remain optional on both hosts.

### Capability: Portable data safety
Keep trash protection and memory publication semantics across filesystem implementations.

#### Feature: Brush path identity
- **Description**: Compare every repository-relative path in one representation before protection checks.
- **Inputs**: trash_untracked.py, Git's tracked-path set, user paths and the existing brush tests.
- **Outputs**: Equivalent protection and report/manifest path identity on Windows and POSIX.
- **Behavior**: Normalize relative paths before the tracked/protected comparisons using Git's
  slash-form representation; reject escapes and protect dev/local, docs and .git as before.
  Preserve literal POSIX filename semantics when a backslash is an ordinary character;
  do not blindly rewrite backslashes on every host. No expansion of the deletion scope.

#### Feature: Memory publication ownership
- **Description**: Publish proposals without replacing an existing directory on Windows.
- **Inputs**: proposal.write_proposals, its publication/funnel tests and existing output schema.
- **Outputs**: Exclusively owned, fully published proposal directories or the existing failure outcome.
- **Behavior**: Preserve rejection of existing empty/nonempty destinations, exclusive reservation
  between competing writers, staging, all-or-nothing publication and cleanup after failure.
  A failed writer must not remove another writer's directory. Keep retry behavior and output
  bytes/schema unchanged. Adapt tests that pin POSIX-specific reservation mechanics to assert
  these ownership guarantees, without dropping concurrent-writer or rollback scenarios.

### Capability: Accurate Windows documentation

#### Feature: Command and coverage note
- **Description**: Fix the copyable command and explain exactly what the runner proves.
- **Inputs**: README install/Windows paragraphs and the actual Windows validation record.
- **Outputs**: `py bin\braid.py` with one backslash; a correct full-suite coverage statement.
- **Behavior**: State that the Python suite runs on windows-latest. Preserve the distinction
  between Braid itself needing no Bash runtime and Bash-backed tests needing Git Bash.
  The junction fallback remains described as stub-tested unless a real fallback invocation
  is actually exercised; a passing Windows job alone does not prove that branch ran.

## Structural Decomposition

Refreshed 2026-11-01 after the build stalled at the plan-expansion gate
(module drift): the Windows job, `.gitattributes`, testpaths, root
`conftest.py`, brush path identity and proposal publication have all shipped
(the 2026-10-17 parking note). The remaining work is the cause rows below.
Evidence for each row is in
`docs/dev/project-management/audit-results/repository-closeout-preparation.md`
("Windows diagnosis and ownership" and the Windows appendix), committed on this
branch with its addendum
`docs/dev/project-management/audit-results/repository-closeout-preparation-session-123534.md`.

### Repository Structure
```text
.github/workflows/ci.yml                                   # Windows runner (unchanged; coordinator dispatches)
README.md                                                  # Phase 2 coverage wording only
CHANGELOG.md                                               # per-task fix entries, rules/changelog.md
src/agent_skills_braid/cli.py                              # W1: B1 link identity
tests/test_braid.py                                        # W1: B1, B2 regressions
tests/test_braid_check.py                                  # W1: B1 regressions
skills/create-prd/scripts/ground_prd.py                    # W2: P1 citation parsing, P2 exclusion globs
skills/create-prd/scripts/test_ground_prd.py               # W2
skills/distil-memory/scripts/docket.py                     # W3: D1 directory diagnosis, D2 entry id rendering
skills/distil-memory/scripts/write.py                      # W3: D3 untranslated atomic writes
skills/distil-memory/scripts/test_docket_refusals.py       # W3
skills/distil-memory/scripts/test_docket_unpublished.py    # W3
skills/distil-memory/scripts/test_write_atomicity.py       # W3
skills/distil-memory/scripts/test_write_crash_safety.py    # W3
skills/glean/scripts/glean.py                              # W4: G1 portable report ids
skills/glean/scripts/test_glean.py                         # W4
skills/purge-devtmp/scripts/purge_devtmp.py                # W4: U2 LF record delimiters
skills/purge-devtmp/scripts/test_purge_devtmp_manifest.py  # W4: U1 seam, U2 regressions
skills/sweep-fix/scripts/test_sweep_enumerate.py           # W4: S1 denied-read seam
skills/sweep-fix/scripts/test_sweep_main_setup_errors.py   # W4: S1
skills/use-qwen/scripts/eval_harness_fixtures.py           # W5: Q2 authored bytes, Q3 native cwd
skills/use-qwen/scripts/eval_harness_run_helpers.py        # W5: Q3 pwd logging
skills/use-qwen/scripts/eval_harness/events.py             # W5: Q1 (production only if demonstrated)
skills/use-qwen/scripts/eval_harness/report.py             # W5: Q7 (production only if demonstrated)
skills/use-qwen/scripts/eval_harness/vetting.py            # W7: Q8 (accounting only if reproduced)
skills/use-qwen/scripts/test_eval_events.py                # W5: Q1
skills/use-qwen/scripts/test_eval_evidence.py              # W5: Q2
skills/use-qwen/scripts/test_eval_gates.py                 # W5: Q3
skills/use-qwen/scripts/test_report.py                     # W5: Q7
skills/use-qwen/scripts/test_run_eval_cli.py               # W5: Q3
skills/use-qwen/scripts/test_run_eval_harness.py           # W5: Q3
skills/use-qwen/scripts/test_run_eval_harness_outcomes.py  # W5: Q3
skills/use-qwen/scripts/test_run_eval_vet.py               # W5: Q2; W7: Q8
docs/dev/project-management/audit-results/repository-closeout-preparation.md
docs/dev/project-management/audit-results/repository-closeout-preparation-session-123534.md
docs/dev/project-management/audit-results/repository-closeout-execution.md  # Phase 2 evidence log
```
Out of bounds: `skills/use-qwen/scripts/eval_harness/trees.py`,
`skills/use-qwen/scripts/test_eval_tree_links.py`,
`skills/use-qwen/scripts/test_eval_tree_state.py` (PRD 00160, causes Q4-Q6) and
`skills/distil-memory/scripts/funnel.py` (PRD 00133).

### Module: Braid portability (W1)
- **Maps to capability**: Complete Windows verification
- **Location**: `src/agent_skills_braid/cli.py`, `tests/test_braid.py`, `tests/test_braid_check.py`
- **Responsibility**: B1: compare equivalent Windows link targets in one spelling without following away the ownership hop. B2: assert observable mode preservation on Windows and keep the exact POSIX 0640 assertion on POSIX.
- **Exports**: Unchanged CLI and drift semantics.

### Module: PRD grounding portability (W2)
- **Maps to capability**: Complete Windows verification
- **Location**: `skills/create-prd/scripts/ground_prd.py`, `skills/create-prd/scripts/test_ground_prd.py`
- **Responsibility**: P1: parse drive, UNC and mixed-slash citations without confusing the line-number colon; the fixture controls native home lookup. P2: pass slash-form exclusion globs to ripgrep.
- **Exports**: Unchanged table/JSON output.

### Module: Memory store portability (W3)
- **Maps to capability**: Portable data safety
- **Location**: `skills/distil-memory/scripts/docket.py`, `skills/distil-memory/scripts/write.py` and the four named tests
- **Responsibility**: D1: name a directory input explicitly. D2: render the malformed entry id deliberately and assert that exact rendering. D3: write the intended bytes with no newline translation, keeping every rename-instant, rollback and retry byte assertion.
- **Exports**: Unchanged CLI exits and store bytes.

### Module: Small-skill portability (W4)
- **Maps to capability**: Complete Windows verification
- **Location**: glean, purge-devtmp and sweep-fix files listed above
- **Responsibility**: G1: `as_posix()` report ids. U1: exercise the invalid-name refusal through the enumeration seam before any mutation. U2: LF record delimiters that preserve embedded CR. S1: the existing denied-read seam in place of `os.geteuid`.
- **Exports**: Unchanged reports and exit codes.

### Module: Qwen harness fixtures (W5, W7)
- **Maps to capability**: Complete Windows verification
- **Location**: use-qwen files listed above
- **Responsibility**: Q1/Q2: authored bytes, with explicit LF and CRLF controls. Q3: native cwd logging, or explicit MSYS conversion. Q7: Path-joined expectations. Q8: a deterministic clock-seam regression for the cumulative warm-up deadline, plus a real bounded-process test.
- **Exports**: Unchanged harness behavior unless a defect is demonstrated.

### Module: Windows documentation
- **Maps to capability**: Accurate Windows documentation
- **Location**: `README.md`
- **Responsibility**: Own README's install/Windows wording and validation evidence references.
- **Exports**: Copyable command and claims limited to observed coverage.

## Dependency Graph

### Foundation Layer (Phase 0)
No dependencies - built first.

- **Braid portability (W1)**, **PRD grounding portability (W2)**, **Memory store portability (W3)**, **Small-skill portability (W4)**: independent of each other.

### Core Layer (Phase 1)
- **Qwen harness fixtures (W5, W7)**: Depends on [] (independent; sequenced after Phase 0 because it shares `skills/use-qwen/scripts/eval_harness_fixtures.py` across Q2 and Q3).

### Integration Layer (Phase 2)
- **Windows documentation**: Depends on [all modules, and the coordinator's native Windows run].

## Implementation Phases

### Phase 0: Foundation
**Goal**: Repair the non-Qwen Windows causes with regressions that would catch the old behavior.

**Tasks**:
- [ ] W1: repair B1 and B2 in `src/agent_skills_braid/cli.py`, `tests/test_braid.py` and `tests/test_braid_check.py` (no deps) - Acceptance: `uv run pytest tests/test_braid.py tests/test_braid_check.py` passes, and a new test that simulates Windows extended-path readlink spelling fails against the old comparison.
- [ ] W2: repair P1 and P2 in `skills/create-prd/scripts/ground_prd.py` (no deps) - Acceptance: `uv run pytest skills/create-prd/scripts/test_ground_prd.py` passes, with new drive/UNC/mixed-slash and backslash-exclusion cases that fail against the old code.
- [ ] W3: repair D1, D2 and D3 in `skills/distil-memory/scripts/docket.py` and `skills/distil-memory/scripts/write.py` (no deps) - Acceptance: `uv run pytest skills/distil-memory/scripts/test_docket_refusals.py skills/distil-memory/scripts/test_docket_unpublished.py skills/distil-memory/scripts/test_write_atomicity.py skills/distil-memory/scripts/test_write_crash_safety.py` passes, with a translated-newline simulation that fails against the old write.
- [ ] W4: repair G1, U1, U2 and S1 in the glean, purge-devtmp and sweep-fix files above (no deps) - Acceptance: `uv run pytest skills/glean skills/purge-devtmp skills/sweep-fix` passes; the U2 test feeds CRLF records through two rewrites and asserts no growth.

**Exit Criteria**: The four focused commands pass. No assertion was weakened, and no Windows skip, xfail or deselection was added.

### Phase 1: Core
**Goal**: Repair the Qwen harness fixture causes.

**Tasks**:
- [ ] W5: repair Q1, Q2, Q3 and Q7 in the use-qwen fixture and test files above (depends on: Phase 0) - Acceptance: `uv run pytest skills/use-qwen/scripts/test_eval_events.py skills/use-qwen/scripts/test_eval_evidence.py skills/use-qwen/scripts/test_eval_gates.py skills/use-qwen/scripts/test_report.py skills/use-qwen/scripts/test_run_eval_cli.py skills/use-qwen/scripts/test_run_eval_harness.py skills/use-qwen/scripts/test_run_eval_harness_outcomes.py skills/use-qwen/scripts/test_run_eval_vet.py` passes. The explicit CRLF controls fail if the fixture translates newlines.
- [ ] W7: add the Q8 deterministic cumulative-deadline regression in `skills/use-qwen/scripts/test_run_eval_vet.py`, changing `skills/use-qwen/scripts/eval_harness/vetting.py` only if that regression reproduces a defect (depends on: Phase 0) - Acceptance: `uv run pytest skills/use-qwen/scripts/test_run_eval_vet.py -k warmup` passes. The real bounded-process timeout test is retained.

**Exit Criteria**: `uv run pytest skills/use-qwen` passes. Q4-Q6 files are untouched.

### Phase 2: Integration
**Goal**: Prove full-suite closure on native Windows and document only that evidence.

**Tasks**:
- [ ] Prepare native Windows validation for the final changed commit (depends on: Phase 1).
  The closeout coordinator owns the actual run: one approved `workflow_dispatch` of
  `.github/workflows/ci.yml` on the combined candidate. This task makes no push and no dispatch.
  Acceptance: `uv run pytest` exits 0 locally. A note in the PRD's review evidence names each
  cause row (B1-B2, P1-P2, D1-D3, G1, U1-U2, S1, Q1-Q3, Q7, Q8), the commit that repairs it,
  its local regression, and whether the native run must still confirm it.
  Native acceptance, recorded later by the coordinator: `uv run --python 3.13 pytest` exits 0 on
  Windows; the Ubuntu matrix is green; the run URL, tested commit, collection and every skip/xfail
  reason are recorded. Do not weaken the command or mark native validation complete without that run.
- [ ] Correct the Windows command and coverage paragraph (depends on: the passing full-suite run).
  Premise: a passing native Windows run is recorded for this PRD's commit. If it is not, skip and
  report this task; never claim coverage in advance.
  Premise: re-read the README and named junction stub test; retain any already-correct wording.
  Acceptance: a file assertion finds the single-backslash command and no doubled spelling;
  README names full Python coverage on windows-latest, distinguishes Git Bash test requirements
  from the Braid CLI, and makes no real-junction claim without a corresponding executed test.

**Exit Criteria**: Passing native Windows and Ubuntu evidence exists for the changed commit; README agrees.

## Test Strategy

### Critical Scenarios
- **Happy path**: both hosts collect the full maintained Python suite and pass it.
- **Edge case**: spaces, native separators, unreadable files and real links preserve the same protections.
- **Error case**: missing tool/symlink capability fails setup explicitly instead of skipping a module.
- **Error case**: concurrent publication or an injected write failure preserves exclusive ownership and cleanup.
- **Regression**: Linux behavior, the Node job, all existing Python collection roots and strict defect xfails survive.

## Risks
- **Scope is larger than a CI edit**: the user chose the entire suite. Design the publication change
  and split implementation tasks by independent module, each under the planner's budget; no unrelated cleanup.
- **Remote evidence is necessary**: local stubs cannot prove native Windows support. Existing workflow_dispatch
  and gh provide a headless route; auth was verified during backlog review, but re-check it before execution.
- **New tests can land earlier in the batch**: compare actual collections, never a fixed test count.
- **Later harness PRDs add Python tests**: they must keep this full Windows gate green using portable
  copy/process fixtures; this PRD does not excuse their regressions.
- **Junction fallback coverage**: hosted symlink privileges may leave it stub-tested; say so precisely.
