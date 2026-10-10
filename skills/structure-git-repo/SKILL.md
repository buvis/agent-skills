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
Distinguish two kinds when you run `check`:

- A part that *would* apply but you deliberately skip here (such as a native
  plugin `CLAUDE.md`): pass `--deviation CHECK=REASON`. The JSON records it as
  `DEVIATION`.
- A part that does not apply to this repository kind at all (such as the
  AGENTS.md bridge in a repository that never adopted agent instructions):
  pass `--not-applicable CHECK=REASON`. The JSON records it as `NOT-APPLICABLE`.

Both keep that check out of the gate while preserving the underlying evidence,
and neither is a `PASS`. Both are opt-in: a bare `check` never infers them, so an
unmarked repository that lost a file it should have still fails. The helper
refuses a waiver that names a passing or unknown check, or the same check marked
both ways, so a waiver can never mask a real defect. This makes a portfolio-wide
`check` a readable signal: `FAIL` means an unaddressed gap, `DEVIATION`/`NOT-APPLICABLE`
mean a recorded judgement, `PASS` means the structural subset holds. Fit governs
layout choices only. The safety rules in the references (preserve work, fabricate
no approvals, publish nothing unasked) hold regardless.

## Execute

1. Read applicable repository instructions and `references/layout.md`. Read the
   existing README, manifests and workflow configuration before choosing changes.
2. Run the helper's `inspect` command. Extend its shallow inventory with tracked
   files, configuration and path-consumer searches; it is not an exhaustive audit.
   Build an applicability table: area, observed source, fit, intended change,
   prerequisite. Declare supported hosts from the request, repository and established
   user workflow; an absent native directory does not mean its host is unsupported.
3. Read and execute `references/scaffold.md` or `references/restructure.md`.
   Read `references/tasks.md` when configuring commands/releases and
   `references/integrations.md` for instruction bridges and applicable workflow tools.
   Create/preserve the CLAUDE.md import bridge by default at the root and each
   maintained nested AGENTS.md scope. Do not wait for a flag, installed Claude or
   another user decision. Missing bridges block completion unless waived, by the
   user or as a Fit deviation; report either as a deviation. The bridge is a Fit
   part like any other: when an existing CLAUDE.md is authored native content whose
   consumer requires that exact file (such as a Claude plugin), and no AGENTS.md
   owns the shared prose, forcing an `@AGENTS.md` import fights the ecosystem.
   Record that as a `MISFIT`/deviation under the Fit rules rather than overwriting
   the native file or demanding a user interview.
4. Implement the requested reversible changes. A restructuring request authorizes
   ordinary edits/moves; do not turn it into another approval interview. Present the
   concrete delta first, misfits on top. Ask only about material ambiguity, a
   whole-structure misfit, conflicting ownership, destructive replacement or work
   outside the selected repository.
5. Run the bundled `check` command and the applicable validation described in the
   mode reference. Paste the helper's actual JSON result, then name operational
   checks performed, unavailable capabilities and remaining migrations. A `PASS`
   gate certifies only the structural subset; it is not evidence that hooks,
   releases, host instruction loading or workflow recovery actually work. Record a
   deliberate skip as `--deviation`/`--not-applicable` so the pasted JSON carries
   the judgement instead of a bare `FAIL`.

Use the installed helper through the shared discovery path. Scaffolding and checking
include the root Claude bridge automatically:

```bash
python3 ~/.agents/skills/structure-git-repo/scripts/structure_repo.py inspect /path/to/repo
python3 ~/.agents/skills/structure-git-repo/scripts/structure_repo.py check /path/to/repo
python3 ~/.agents/skills/structure-git-repo/scripts/structure_repo.py check /path/to/repo --deviation claude-imports-AGENTS.md="native plugin CLAUDE.md, no AGENTS.md owner"
python3 ~/.agents/skills/structure-git-repo/scripts/structure_repo.py check /path/to/repo --not-applicable nonempty-AGENTS.md="no agent-instructions convention" --not-applicable claude-imports-AGENTS.md="no AGENTS.md to import"
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
