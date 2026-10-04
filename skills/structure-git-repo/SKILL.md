---
name: structure-git-repo
description: Use when scaffolding an empty Git repository or restructuring an existing one (provide repository path). Triggers on "structure git repo", "scaffold repo", "restructure repo", "apply repo structure".
---

# Structure Git Repo

Apply the common repository structure where it fits, tailored to the repository's
purpose. It is a standard and advice for those in doubt, not a mandate. Never force
it where it does not make sense: flag the misfit loudly instead (see Fit).
Work on the selected repository; the user chooses when to run this skill elsewhere.

## Dependencies

- Filesystem editing, Git, and Python 3.10+: required. Use mise-managed runtimes.
  The bundled helper uses only the standard library. Missing helper/resources mean
  an incomplete skill installation; report the missing path before mutation.
- Mise: required when adding toolchain/tasks; absent installation blocks that part.
- Braid, Specflow and Autopilot: conditional integrations, not prerequisites for a
  basic repository. Read `references/integrations.md` when applicable. Missing
  capabilities block their dependent changes, not independent improvements.

## Select the target

Use an explicit repository path from the request or an unambiguous repository
already established in the conversation. Otherwise ask for one path and wait.
Resolve it and state the target. A nonexistent path is valid for scaffolding.
An empty directory or Git-only checkout uses scaffold mode; other content uses
restructure mode. A request to inspect, plan or dry-run permits no target writes.
For scaffolding, infer purpose/toolchain from the request; ask only for missing
information that changes what should be created.

## Fit

Judge fit before any write, for a planned repository and an existing one alike.
State the project kind (such as library, service, dotfiles, documentation or
monorepo) and whether the structure suits it.

When a part is too rigid, costs more than it gives, or fights the repository's
ecosystem, conventions or consumers, flag it loudly: open the response with a
`MISFIT` block naming the part, the evidence and the alternative you recommend.
Never bend the repository to match the layout, and never drop a part silently.
Both hide the signal used to tune this standard per project kind.

- Some parts misfit: keep the repository's own convention there, apply the rest,
  and list each deviation in the final report.
- The structure misfits as a whole, or following it would move working material
  for no gain: stop before mutation, report `PLANNED` with the misfit, and let the
  user decide.

A deliberate deviation is a result, not a defect. It does not block `COMPLETE`,
and a helper `FAIL` on a part left out on purpose is reported as a deviation.
Fit governs layout choices only. The safety rules in the references (preserve
work, fabricate no approvals, publish nothing unasked) hold regardless.

## Execute

1. Read applicable repository instructions and `references/layout.md`. Read the
   existing README, manifests and workflow configuration before choosing changes.
2. Run the helper's `inspect` command. Extend its shallow inventory with tracked
   files, configuration and path-consumer searches; it is not an exhaustive audit.
   Build an applicability table: area, observed source, fit, intended change,
   prerequisite.
3. Read and execute `references/scaffold.md` or `references/restructure.md`.
   Read `references/tasks.md` when configuring commands/releases and
   `references/integrations.md` when configuring hosts or workflow tools.
4. Implement the requested reversible changes. A restructuring request authorizes
   ordinary edits/moves; do not turn it into another approval interview. Present the
   concrete delta first, misfits on top. Ask only about material ambiguity, a
   whole-structure misfit, conflicting ownership, destructive replacement or work
   outside the selected repository.
5. Run the bundled `check` command and the applicable validation described in the
   mode reference. Paste the helper's actual JSON result, then name operational
   checks performed, unavailable capabilities and remaining migrations. Structural
   PASS alone does not establish working hooks, releases, hosts or workflow recovery.

Use the installed helper through the shared discovery path:

```bash
python3 ~/.agents/skills/structure-git-repo/scripts/structure_repo.py inspect /path/to/repo
python3 ~/.agents/skills/structure-git-repo/scripts/structure_repo.py check /path/to/repo
```

When validating the skill installation itself, run the helper with `--selftest`;
it exercises disposable fixtures, not the selected repository.

## Finish or resume

Report `COMPLETE`, `INCOMPLETE`, or `PLANNED`, with the target, changed paths,
verification evidence and next concrete step. COMPLETE requires every applicable
planned change and check to finish; explain inapplicable areas and list each
deviation from the structure with its reason. An honest INCOMPLETE
with working independent changes is useful. Never describe missing integrations as
implemented. Preserve unrelated work; commit/push/publish only when requested.
For restructuring, keep the migration report current after each completed group
so another invocation can resume from disk.
