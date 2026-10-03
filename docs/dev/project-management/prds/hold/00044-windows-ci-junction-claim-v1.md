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

### Repository Structure
```text
.github/workflows/ci.yml               # Windows runner and full-suite command
.gitattributes                        # New: LF for Bash files
pyproject.toml                        # Complete Python collection
README.md                             # Command and measured coverage
tests/test_braid.py                    # Validation; edit only for a verified portability issue
skills/
├── sweep-fix/scripts/
│   ├── conftest.py
│   ├── test_sweep_resolvers.py
│   └── test_sweep_scan.py
├── explain-interactively/scripts/test_build.py
├── review-prd-backlog/scripts/test_check_links.py
├── survey/scripts/test_survey.py
├── purge-devlocal/scripts/test_purge_devlocal.py  # Validation surface
├── brush/scripts/{trash_untracked.py,test_brush_scripts.py}
└── distil-memory/scripts/
    ├── proposal.py
    ├── test_proposal_publication.py
    ├── test_funnel_distil_publication.py
    ├── test_dedup.py
    ├── test_dedup_classify.py
    └── test_funnel_main.py
```
Additional collected files are changed only for a reproduced Windows failure or its regression;
record the failure and file in the implementation plan rather than perform a general refactor.

### Module: Runner
- **Maps to capability**: Complete Windows verification
- **Responsibility**: Own workflow, .gitattributes and pyproject collection; prove prerequisites.
- **Exports**: jobs.windows and the full pytest command on both hosts.

### Module: Fixture portability
- **Maps to capability**: Complete Windows verification
- **Responsibility**: Own the listed sweep, assembly, link-checker, survey, purge, Braid and distil read/path fixtures.
- **Exports**: Existing test behavior under controlled, portable environments.

### Module: Brush protection
- **Maps to capability**: Portable data safety
- **Responsibility**: Own trash_untracked.py and test_brush_scripts.py path/protection fixes.
- **Exports**: Existing CLI and report/manifest schema, with host-correct path identity.

### Module: Proposal publication
- **Maps to capability**: Portable data safety
- **Responsibility**: Own proposal.py and its two publication test files; retain ownership and failure guarantees.
- **Exports**: Existing publish interface and artifact schema.

### Module: Windows documentation
- **Maps to capability**: Accurate Windows documentation
- **Responsibility**: Own README's install/Windows wording and validation evidence references.
- **Exports**: Copyable command and claims limited to observed coverage.

## Dependency Graph

### Foundation Layer (Phase 0)
- **Runner**: Uses existing workflow and lower-numbered 00020/00022 outputs.
- **Fixture portability**: Reproduces known failures; no new product behavior.

### Core Layer (Phase 1)
- **Brush protection**: Depends on [Fixture portability].
- **Proposal publication**: Depends on [Fixture portability].

### Integration Layer (Phase 2)
- **Windows documentation**: Depends on [Runner, Fixture portability, Brush protection, Proposal publication].

## Implementation Phases

### Phase 0: Foundation
**Goal**: Establish the complete collection, executable runner and reproducible portability cases.

**Tasks**:
- [ ] Re-check the workflow/collection and provision the Windows job, toolchain, UTF-8, LF and symlink
  capability checks (no deps) - Acceptance: `uv run python3 -c "import yaml; d=yaml.safe_load(open('.github/workflows/ci.yml')); assert d['jobs']['windows']['runs-on'] == 'windows-latest'; assert {'test','shell','lint','node'} <= d['jobs'].keys()"`
  exits 0; `uv run pytest --collect-only -q` includes tests, skills and earlier repo-level scripts tests;
  the Windows job runs the same unfiltered command, with no failure suppression.
- [ ] Port the named fixtures after reproducing their assumptions (no deps) - Acceptance: each
  affected test retains its observed behavior; the real resolver/search and Bash subprocess cases
  pass, denied-read cases distinguish unreadable from missing, and actual symlink tests run.
  `uv run pytest --collect-only -q` records the collection for comparison with the Windows run;
  no existing regression is removed and no new Windows skip/xfail/deselection is introduced.

**Exit Criteria**: A complete Windows job exists and the fixture changes preserve coverage.

### Phase 1: Core
**Goal**: Correct filesystem behavior without weakening data protection.

**Tasks**:
- [ ] Fix brush relative-path identity (depends on: Phase 0) - Acceptance: `uv run pytest
  skills/brush/scripts/test_brush_scripts.py -q` passes regressions for tracked files, protected
  prefixes, dotdot aliases, spaces and Windows separators, with a permitted-path positive control;
  refusal and manifest paths identify the same file before and after normalization.
- [ ] Make proposal publication portable (depends on: Phase 0) - Acceptance: `uv run pytest
  skills/distil-memory/scripts/test_proposal_publication.py
  skills/distil-memory/scripts/test_funnel_distil_publication.py -q` passes on both hosts;
  competing writers have one winner, pre-existing destinations survive, failures expose no
  partially published proposal set, and cleanup/retry preserve the documented output schema.

**Exit Criteria**: Both product regressions pass without changes to their intended safety guarantees.

### Phase 2: Integration
**Goal**: Prove full-suite closure on native Windows and document only that evidence.

**Tasks**:
- [ ] Run the complete Python suite on POSIX and windows-latest for the final changed commit
  (depends on: Phase 1). Use the existing GitHub Actions workflow and authenticated headless gh CLI
  to inspect the branch/PR run; no manual browser check or interactive login is part of this task.
  Acceptance: `uv run --python 3.13 pytest` exits 0 on Windows; the existing Ubuntu matrix is green;
  record the run URL, tested commit, collected tests and every skip/xfail reason in the review evidence.
  Fix additional Windows failures of collected tests in this PRD, preserving behavior and full collection.
  If authentication/runner access is unavailable, stop and record the execution blocker; do not
  weaken the command or mark this validation complete.
- [ ] Correct the Windows command and coverage paragraph (depends on: the passing full-suite run).
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
