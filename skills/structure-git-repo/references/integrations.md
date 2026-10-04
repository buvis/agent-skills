# Integrate supported capabilities

Check installed versions/help/schema/source and official host documentation when
needed. Record documentation date separately from a successful local probe. Never
turn a roadmap or a config-file presence into a working-capability claim.

## Instructions

Author shared prose in root/nested AGENTS.md. Root guidance directs reading applicable
nested files before working on governed files if the host has not already loaded them.
Nested guidance states scope explicitly, including for hosts that load it eagerly.
A prose pointer is an agent-followed fallback, not proof of automatic loading.

Use the smallest supported native pointer/config adapter; retain the one-line
CLAUDE.md @AGENTS.md bridge where Claude is supported. A root import alone does not
prove nested discovery. Keep host-specific execution policies and hooks independent
of prose. Do not build a steering MCP service or universal glob-rule generator.

Record actual enabled surfaces (CLI/app/IDE/cloud/custom agent), their entry points,
nested behavior, adapter owner and evidence/limitations. Initial documentation from
2026-10-03 distinguished Codex startup discovery, Claude version/settings, Copilot
surface differences and Kiro eager/custom-agent behavior; recheck installed support
instead of treating that snapshot as permanent truth. No need to configure absent hosts.

## Skills: Braid owns projection

Use repository-declared sources/targets only; preserve authored .agents/skills in place.
Do not import global personal skills/policy or Braid's installation checkout. State and
backups must be ignored and worktree-local. Declare the Braid dependency in repository
tooling; no sibling source checkout requirement.

Capability gate: verify the installed Braid can isolate repository inputs, preserve
owned/unowned paths, report drift and use the needed adapter. The known older CLI's
destination overrides and additive --source still included personal/default sources;
those flags alone are not an isolation solution. Do not invent a --repo flag or ship
an onboard task that calls nonexistent functionality. If missing, report the exact
Braid enhancement as blocked and leave existing working views intact. Do not fork
projection logic into the scaffold helper. Native discovery needs no projection.

Prefer Braid's symlinks and supported Windows junction fallback. A copy adapter needs
demonstrated host necessity plus refresh/drift semantics. Hooks do not refresh copies
after every ordinary source edit. Keep generated views ignored at exact paths (no
trailing slash on patterns that must also match symlinks). Check ownership/conflicts
before adding ignores. Never silently install repository skills into a user-global store.

## Specs: canonical paths and the optional Kiro link

Check the installed Specflow schema before creating .agents/specflow.json for the
docs/dev/project-management root and its specs directory. Specflow owns artifacts
and per-spec approval state; native sidecars may coexist. Autopilot must actually
consume that representation before its active PRD queues are retired. A missing
consumer blocks that workflow migration, not adding unrelated procedures or commands.

Onboard owns an optional ignored .kiro/specs link to configured specsDir when Kiro
integration is enabled. Specflow reads the canonical path directly and does not
create/repair the link. Use a relative symlink or supported Windows junction, never
a copied specs tree: editor writes must reach canonical artifacts.

Keep correct links; maintain owned links only. Preserve real directories and unowned
conflicts and report a remedy, without merging/deleting/hiding them automatically.
Verify panel discovery on the actual Kiro surface; if unsupported, report the panel
unavailable and retain the canonical folder. Skill discovery is a separate capability.
The existence of a home .kiro directory does not establish an installed Kiro IDE.

## Onboard and Git hooks

Full onboard ensures dependencies, supported adapters, ignore coverage and hook setup.
--sync uses installed tooling for local projections/links only: no installs/network
setup, hook reinstallation or tracked configuration rewrites. Missing prerequisites
produce an actionable failure. Repeat runs preserve already-correct state.

Enforce the sync boundary before the task implementation runs. Mise can install
missing tools while starting a task. Where supported, use repository configuration
to cover both shims and direct mise calls:

```toml
[settings]
task.run_auto_install = false
```

Full onboard then performs its declared installs explicitly. A launch-time
`MISE_TASK_RUN_AUTO_INSTALL=false` also covers that invocation, but alone does not
protect direct calls. Inspect task dependencies and environment hooks for implicit
setup too. Verify sync with missing-tool fixtures; a guard inside the implementation
is too late. See [mise's setting](https://mise.jdx.dev/configuration/settings.html#task-run-auto-install).

Resolve Git paths through Git and respect effective core.hooksPath, including existing
managers, worktrees and shared/global hook locations. Compose through supported
manager mechanisms; otherwise install owned entries only at unused effective paths.
Do not replace/wrap arbitrary unowned hooks or redirect an existing manager. Report
the concrete integration step if composition is unsupported; no new universal manager.

Applicable post-checkout/post-merge/post-rewrite hooks invoke the current worktree's
explicit onboard --sync entry point. Never embed another checkout's absolute path in
shared hooks. Preserve arguments/stdin and existing status handling. Skip absent
optional hosts; report enabled-but-unavailable integrations. Keep explicit sync/drift
operations for ordinary edits and recovery. Do not present setup that failed as armed.
