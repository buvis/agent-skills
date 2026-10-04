# Restructure an existing repository

## Establish the boundary

Read the repository before proposing moves: README/AGENTS, manifests, mise/native
tasks, CI, docs/dev, .agents, native integration files and effective Git hook setup.
Use Git to distinguish tracked, ignored, untracked and modified material. A .git file
can identify a worktree; do not assume it is a directory. If Git identifies a parent
repository instead of the selected path, resolve that mismatch before editing.
Bare repositories need an explicitly selected worktree; never scaffold into bare
Git internals. Preserve unrelated dirty/staged work; do not stash/reset it automatically.

For an intentional bare-backed worktree (such as dotfiles), pass the declared Git
directory to both helper commands: `inspect /path/to/worktree --git-dir /path/to/git-dir`
and `check /path/to/worktree --git-dir /path/to/git-dir`. Use that identity for every
Git operation. Anchor pathspecs with `:(top)` and confirm a known-tracked control;
empty tracking output alone does not prove a file is untracked. Never infer a bare
Git directory or treat all files in a home-directory worktree as owned by that repo.

Build a compact table of old path, destination, reader/writer/caller, prerequisite,
and intended action. Search executable consumers and documentation separately.
Include package/release hooks, task script paths, CI, global steering, context writers,
recording pathspecs, dirty-tree exemptions, cleanup, runtime recovery and skill source
ownership. Retain existing native assets and ecosystem source/test layouts.

Show the concrete delta and apply the already requested reversible restructuring.
If asked only to audit/preview, stop with PLANNED and do not write a report into the
target. Do not turn every file move into a separate approval question.

## Migrate by coherent dependency group

Create/update a report at docs/dev/project-management/reviews/YYYYMMDD-structure-repo.md
(or an existing report for this migration). Include baseline Git state, applicability,
path map, prerequisite evidence, completed groups, verification results and resume point.
Preserve concurrent report content; use a unique suffix when another report owns the name.

For each group:

1. Verify shared tools can consume the target representation. Check installed help,
   configuration schemas or source; do not assume planned Braid/Specflow/Autopilot
   features exist. Use integrations.md. Changes outside the selected repository
   require their own authorization; report their exact prerequisite and continue
   independent ready groups.
2. Capture recoverable originals for modified untracked/ignored material using an
   explicit local backup path. Git history alone cannot recover those bytes. Stage
   nothing unrelated and preserve the user's index. Use a safe handoff boundary for
   active/paused runners; preserve resumable state rather than moving live controls.
3. Move content with its consumers: readers, writers, links, hooks, recording and
   cleanup switch together. A repository has one active work authority. Shared tools
   may temporarily support old/new layouts across different repositories.
4. Classify old metadata by purpose. Preserve IDs, provenance, historical designs,
   review evidence and approval meaning. Completed PRD status is not a Specflow
   approval; transformed artifacts cannot inherit fabricated approval hashes.
5. Check the diff and targeted consumers, then record the completed group immediately.
   Leave blocked groups on their working old representation. Do not dual-write queues
   or hide remaining old writers behind a claim that migration is complete.

## Complete with evidence

Run the helper's check command and paste its output into the report. It checks a
small structural subset only. Separately record actual evidence for each applicable
area, or an explicit not-applicable/blocked reason:

- Fresh-clone setup, repeatable onboarding/sync, and linked-worktree execution with
  existing hooks preserved. Use disposable fixtures; do not create commits, install
  global hooks or rewrite the user's shared hook manager merely to exercise a check.
- Public commands and CI use the same implementations; shims pass arguments/status
  and cannot recurse. Run applicable safe checks after inspecting task definitions.
- Spec creation/approval/runner consumption and existing required review phases;
  context readers/writers find their authoritative sources.
- Recording includes retained machine records; runtime exemptions do not hide other
  changes. Recovery preserves active/paused work; cleanup recognizes its new ownership.
  Exercise cleanup via a supported preview or isolated fixture, never a live purge.
- Declared host discovery and optional Kiro panel capability have evidence or explicit
  limitations. Release version authority, preview and recovery satisfy tasks.md;
  do not publish, push or create release tags to prove restructuring works.

If a required workflow cannot be verified, report INCOMPLETE with a resumable next
step. Optional unsupported integrations may be documented unavailable without making
them required. Pending path changes remain advisory until this repository switches;
actual broken consumers remain defects. COMPLETE requires all applicable migration
groups and their checks to finish. Retire compatibility only after its consumers
migrate; retain historical evidence according to its purpose.
