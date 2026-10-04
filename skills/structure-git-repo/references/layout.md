# Target structure

This is the reusable standard distilled from the repository-structure decisions
approved on 2026-10-04. It is advice, not a mandate: apply it by purpose, and flag
any part that does not fit the repository (SKILL.md, Fit) instead of forcing it.
The tree is not mandatory scaffolding.

## Common core and ownership

Provide README.md for humans and AGENTS.md for agents. Document actual purpose,
available commands, invariants and links. Keep native language/framework/package
layouts: no forced root src/ or mirrored tests/. Add mise and tools/ where tooling
is needed. Add documentation categories, skills and workflow state only when used.
Public visibility alone does not require CONTRIBUTING, SECURITY and CODE_OF_CONDUCT;
use the audience and operating model. Preserve licensing/distribution requirements.
Release-only files apply only to repositories that release versions.

Keep one authored source per concern. Root/nested AGENTS.md hold shared instructions;
necessary native configuration, execution policy and packaged integrations may stay
in .claude/, .codex/, .kiro/, .cursor/ or .github/. Never ignore a whole native tree
merely because it is host-specific. Preserve native permission rules and hooks.

.agents/ is extensible shared agent/workflow material. Project working skills use
.agents/skills/. Shipped skills/plugins retain consumer-required package layouts;
compose views from their source without duplicating authorship. Generated views and
machine-local state are ignored precisely; authored assets remain tracked.

Commands, skills, functions, executable helpers and action-oriented procedure names
start with verbs. Keep externally prescribed filenames where their consumer needs
them, such as Git's post-checkout hook; give its implementation a verb-first name.

## Development documentation

```text
docs/dev/
  architecture/
    README.md                 # maintained current system overview
    decisions/                # significant ADRs, including superseded records
  context/
    project-capsule.md         # dated orientation linking authoritative sources
    troubleshooting.md        # reusable knowledge, when useful
  procedures/
    add-a-server.md            # example repeatable workflow
    release.md                # when releasing versions
  project-management/
    intake/
      new/[optional-group/]NNNNN-title/
        idea.md
        qa-log.md
      processed/[optional-group/]NNNNN-title/
    specs/NNNNN-title/
      requirements.md          # OR bugfix.md
      design.md
      tasks.md
      .specflow.json           # artifact-hash approvals and hold state
      reviews/                 # reports about this spec, when produced
    research/                  # reusable investigations spanning changes
    reviews/                   # reports spanning specs or the repository
  tmp/                         # ignored disposable scratch
```

Create meaningful intake drafts tracked from the start. Retain original inputs,
source material and Q&A. When requirements/bugfix requirements are first written,
move the intake item to processed/, preserve ID/group and update the spec's Sources
link. Processed means a spec exists, not approved or completed. Later Q&A stays with
that intake item. Research for one idea stays there; shared research is linked.

Specs retain their path through backlog, implementation, hold and completion.
Requirements define behavior, design records decisions, tasks track execution;
avoid repeating content. The three artifacts develop through the workflow rather
than appearing as empty files up front. Specflow owns their state, Autopilot consumes
approved bundles. Routine changes needing no spec/staged approval use normal change
workflow with existing checks/reviews. Never weaken the target's review roster.

Reports follow scope: one spec -> its reviews/; broader -> project-management/reviews/.
Q&A minutes link detailed reports; do not duplicate them or require extra reports.
Procedures describe recurring work, not a single change's tasks. Architecture describes
the current system; ADRs preserve significant rationale and link replacements when
superseded. Historical feature designs stay with their specs. Context summarizes and
links these authorities rather than maintaining a second work queue.

## Workflow storage

Use .agents/specflow.json for repository paths (project-management root and specsDir),
following the installed Specflow schema; per-spec .specflow.json is distinct state.
Allow native sidecars such as .config.kiro. Do not invent configuration fields or
approval hashes. See integrations.md for capability gates and the optional Kiro link.

Autopilot live state/locks/controls -> ignored .agents/autopilot/runtime/.
Durable ledgers, deferred requests and final snapshots -> tracked
.agents/autopilot/records/. Preserve recovery information for active/paused and
unresolved work. Human reports use the existing reviews locations by scope, linked
to records by stable run/spec identifiers. Add no project-management/runs/ category.

Keep docs/dev/tmp/ for disposable outputs. Preserve its recoverable trash-first
collector and active-work protection. Before retiring PRD status buckets, update
cleanup to recognize intake/spec/run ownership. Scratch cleanup must not follow links
or touch Autopilot runtime/records. Do not create ignored dev/work/ or rename scratch
to dev/tmp/. Retire dev/bin in favor of tools/ with its callers; classify durable
dev/local content into tracked intake/specs instead of discarding it.

Historical evidence is retained in its original meaning; migration need not fabricate
modern spec artifacts for completed history. It must not leave two active queues.
