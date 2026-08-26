---
name: run-agoge
description: Use when running the agoge product-QA pack at a repo - recon, armed specialist dispatch, dedup, and one findings report about the product rather than the diff. Triggers on "run agoge", "/run-agoge", "product QA", "QA this project".
compatibility: "Documentation copy of the agoge plugin skill; the seven specialist agents and the PRD-number claimer ship only in that plugin, and Claude Code uses the namespaced plugin skill."
---

# Run agoge

Agoge is the product-time lens. Every other review reads a diff; this one runs
the product. Seven named specialists: **olivia** (recon, always), then
**walter** (journeys), **heidi** (integration and db), **judy** (UX),
**wendy** (release truth), **peggy** (performance), **trudy** (runtime
security).

The one rule the whole pack exists to enforce: **a lane that did not run is
never a pass.** Every result carries `verified`, `unverified`, `mocked` or
`skipped`, and only `verified` is a real defect.

> **This copy carries the doctrine, not the pack.** The seven agent files and
> the PRD-number claimer ship in the agoge plugin; paths written as
> `<agoge-plugin-root>/...` point there. Without that plugin the playbooks below
> still read as QA doctrine, but no lane can be dispatched.

## Dependencies

- Agent registry: `olivia`, `walter`, `heidi`, `judy`, `wendy`, `peggy`,
  `trudy` — each dispatched as `subagent_type: agoge:<name>`. They ship in the
  agoge plugin and exist on Claude Code only. Missing = this skill cannot run. The frontmatter `name` is the file stem; the dispatch name
  is that stem namespaced, because a plugin's agents register under its
  namespace only. Naming a persona bare fails outright with
  `Agent type 'olivia' not found`.
- Path: `references/finding-contract.md` in this skill's directory — the
  finding, report and profile contracts. Read it before step 2.
- Path: `references/{browser,data,perf,security}-playbook.md` in this skill's
  directory — per-lane execution doctrine, pasted into the dispatch that needs
  it. `references/authoring-playbook.md` is the master's own, never dispatched.
- Path: `references/prd-emission.md` in this skill's directory, and
  `<agoge-plugin-root>/skills/run-agoge/scripts/allocate_prd_number.py` — how an
  accepted finding becomes a backlog PRD, and the claim that keeps two writers
  off one number. Step 9 only.
- Optional: an unattended runner may fire one run per batch of completed work,
  passing `--authorized <its own name>`. Nothing here needs one; running this
  skill by hand is the ordinary case.
- CLI: `git`, `python3`.

The walkthrough packet shape lives in `references/finding-contract.md`, and the
roster conventions in each agent file's own frontmatter. This skill depends on
no file outside its own directory and the seven agent files.

## Arguments

- *(none)* — the current repo.
- `<repo-path>` — an absolute path to the repo to run against.
- `--refresh-profile` — re-run recon even when the profile is fresh.
- `--authorized <source>` — assert, at invocation, that the target is the
  operator's own or explicitly authorized, where `<source>` names the human act
  it came from (an unattended loop passes its own name). Arms **trudy** only.
  A `--authorized` flag with no value is an error: stop and report. A
  `--authorized` flag not passed at all is not an error — the run continues
  without an invocation-level assertion. Never assert anonymously, and never
  supply a source of your own. A source that is itself another flag
  (`--authorized --refresh-profile`) is the same error, not a source named
  `--refresh-profile`. `<source>` is bounded to a shell-word shape: a single
  token of letters, digits, dash and underscore, and nothing else. A source
  outside that shape is the same error: stop and report it, never sanitize it
  into shape. `autoclaude-drain` fits.
- `--resume <report>` — walk an existing report's packets and record decisions.
  Dispatches nobody. Jump straight to step 9.
- `--decisions <file>` — with `--resume`, take the decisions from a JSON file
  instead of asking. For headless verification, never for a real walkthrough.

## Workflow

### 1. Resolve the target

Take the absolute repo path from the argument, else the cwd's repo root. Record
its HEAD:

```bash
git -C /absolute/target/repo rev-parse HEAD
```

Everything downstream uses absolute paths. Never `cd`.

Read `references/finding-contract.md` from this skill's directory now. You will
paste its `## Finding contract` section into every dispatch prompt, so the
specialists get the contract without reading any path of yours.

### 2. Profile

The profile is `dev/local/meta/agoge-profile.md` in the **target** repo,
falling back to `dev/local/agoge-profile.md` when `meta/` has none. It decides
who runs, so a wrong profile is a wasted run. Whichever one you read is *the
resolved path*: every later step that names the profile names that path, not
the other one.

- **Missing**, or its freshness sha is not the target's HEAD, or
  `--refresh-profile`: dispatch **olivia** as `subagent_type: agoge:olivia`
  (see the recon prompt below).
- **Fresh**: read it and go to step 3.

After a refresh, before anything else, prove the human-owned section survived.
**Do not reach for `git diff`** — `dev/local/` is ignored almost everywhere, so
that diff comes back empty whatever recon did, and a check that cannot fail is
worse than none. Copy `## Pins and vetoes` to a scratch file *before* the
dispatch, extract it again afterwards, and compare the bytes (`cksum` on both).

**If the section changed, stop the run and report it.** Recon rewriting a
human's veto is a defect in the pack, not a detail.

### 3. Dispatch the armed specialists

From the profile's per-specialist strategy, dispatch **only** specialists marked
`armed`, not vetoed, and carrying populated tactics. Unarmed and vetoed lanes
are reported, never run — that is the cost gate. An `armed` row with empty
tactics is reported `skipped` too, reason "stale profile, rerun recon with
`--refresh-profile` to give it real tactics before dispatch."

**One exception, and only one, and it turns on the reason.** `unarmed` is a
verdict about *surface*: recon found nothing here for that lane to run. Recon is
told (step 6 of the recon prompt) to decide trudy on surface alone, but an older
or hand-edited profile may still carry an `unarmed` row whose stated reason is
the `Authorization:` default rather than a surface fact. **That row alone** does
not survive an authorization arriving by the other route — for it, part 5 below
decides. A surface `unarmed` still stands, for trudy as for everyone: a repo with
nothing to run does not become probeable because a flag was passed.

If the row gives no reason, treat it as a surface verdict and leave her unarmed.
Reading an unexplained row as the authorization case would let the exception
swallow the cost gate.

A third way the exception fails closed: it inherits the tactics rule above,
not just the reason. `finding-contract.md` defines an `unarmed` row as carrying
the reason, not tactics, and part 2 of a dispatch prompt is built from that
specialist's row — its tactics and the exact commands recon established. Arm a
tacticsless row anyway and trudy probes blind while the report claims the lane
ran armed. If the row's tactics are empty, do not dispatch her: report the lane
`skipped` for the same reason given above.

Dispatch every armed specialist **in one message**, one Agent call each naming
`subagent_type: agoge:<persona>`, so they run concurrently. One that fails
returns its error and the others are unaffected; record that lane `unverified`
with the failure and finish the run.

Each prompt is assembled from five parts, in this order:

1. The absolute target repo path, and the one-line instruction: run the product,
   do not modify it.
2. That specialist's row from the profile — its tactics and the exact commands
   recon established — plus the mocking strategy.
3. **The lane's playbook**, pasted verbatim from this skill's `references/`:

   | Lane | Playbook |
   |---|---|
   | judy | `browser-playbook.md` |
   | heidi | `data-playbook.md` |
   | peggy | `perf-playbook.md` |
   | trudy | `security-playbook.md` |
   | walter | `browser-playbook.md`, **only** when the profile puts a journey through a page |
   | wendy, olivia | none |

   A lane never authors. If the profile assigns authoring, that is the master's
   job in step 6 — say so in the prompt so the specialist puts its test in the
   finding's `fix` field instead of on disk.
4. The `## Finding contract` section, pasted verbatim.
5. For **trudy** only: the authorization, and the human act it came from. A
   vetoed trudy never reaches this resolution at all: step 3 already refused
   her before part 5 runs, so every row below resolves only for a lane that
   got this far. Resolve it in this order and stop at the first hit:

   | Source | When | What her prompt carries |
   |---|---|---|
   | `profile` | the profile's `Authorization:` line is asserted (not `not asserted`) | that line verbatim, plus `Asserted by: profile (<path>)` — `<path>` is the profile path that resolved in step 2, `dev/local/meta/agoge-profile.md` or the root fallback |
   | `invocation` | `--authorized <source>` was passed | the contract's assertion line, plus `Asserted by: invocation (<source>)` |
   | none | neither of the above | nothing — **do not dispatch her**; report the lane `skipped`, reason "authorization not asserted" |

   An `Authorization:` line with an empty value is treated the same as an
   absent line: neither satisfies the profile row's condition, so both fail
   closed.

   The profile wins over the invocation when both assert: the file in the repo
   is the more specific act. Both routes are a human's — a machine never
   asserts for itself, and recon still may not write that line. Pass the
   source through verbatim; do not invent, shorten or supply one.

   An `--authorized` with an empty source is an error. Stop the run and report
   it, the same rule the decisions file follows in step 9: a path whose whole
   point is that a human authorized it must not guess who. The flag-shaped and
   out-of-shape source errors stated in Arguments take that same path.

Keep each prompt under 50 000 bytes — measure it, do not estimate. Recon output
and one playbook are small; this only binds if you paste files in, so do not.

### 4. Audit the statuses

Before anything is merged or written, check every finding that arrived
`verified` against its own evidence, per the finding contract's downgrade rule.
Evidence that quotes a command and its output backs the claim; evidence that
reads the code or names a mock does not, and the finding is downgraded with a
note.

A lane cannot audit its own claim. This step exists because the master is the
only reader who did not make it.

### 5. Dedup

Collapse findings that are the same defect seen from two lanes (a dead
integration also breaks a journey). Key on normalized path plus symptom, not on
wording. On merge: keep the **strictest** severity, union the evidence, and keep
every contributing lane's name.

Do not merge two findings that share a file but not a symptom.

### 6. Author, if the profile assigns it

Only the master authors — every specialist is pinned read-and-run so the armed
tree stays byte-identical while the lanes work. Read
`references/authoring-playbook.md` and follow it: branch, write, run, commit
tests only, return to the branch you started on.

Skip the step, and say so in the report, when the profile assigns no authoring,
no finding survived step 4 as `verified`, or the target's tree is dirty.

### 7. Report

Write both files into the target repo's `dev/local/audit-results/`:

- `agoge-<YYYY-MM-DD>.md` — the human report, in the report contract's shape:
  summary header with per-lane verified / unverified / mocked / skipped counts
  and who was armed, unarmed or vetoed; then one walkthrough packet per finding;
  then the how-to-proceed block.
- `agoge-<YYYY-MM-DD>.json` — the sidecar, in the contract's shape. `fixture` is
  the target directory's basename. Every finding needs a non-empty `paths`; a
  finding you cannot anchor to a file belongs in the markdown only.

**Never overwrite a report.** If that date is taken, suffix yours (`-2`, `-3`).
Two drained batches land on one day often enough, and the report you would
clobber may still be carrying somebody's unwalked packets.

The summary header is the honesty ledger. A lane with zero findings still states
which of the four statuses applies to it, and why. Counts are post-downgrade.
Name the authored branch and its runner command, or say nothing was authored.

It also records **how the security lane was authorized**, one of four routes, in
the header and in the sidecar's `authorization` object: `profile` (the profile's
`Authorization:` line asserted it; no separate source, since the profile path is
already its identity), `invocation` (`--authorized <source>` asserted it; record
that token as source), `vetoed` (a veto overrode an assertion that was actually
made, by either route; source carries the overruled invocation token when that
assertion came from `--authorized`, and is absent when it came from the profile
line; when the profile line and `--authorized <source>` both assert, the
profile wins and source stays absent, the same precedence part 5 states for
the non-vetoed case, restated here since a vetoed trudy never reaches part 5),
or `none` (no assertion was made at all, so there is no source; a veto
with nothing to overrule is `none`, not `vetoed`). A reader must be able to tell
later which human act decided, and `vetoed` is the one case where the operator
said no, the one route that had no audit trail before this: write it down at the
time.

### 8. Close

**Interactive**: go to step 9 and walk the findings now.

**Unattended** (an autopilot loop, a headless run, or no human to answer): write
the packets and stop. Never auto-emit PRDs, never guess an approval. End the
report with this line, exactly:

```
> **AGOGE-WALKTHROUGH-PENDING** — run `/run-agoge --resume <path to this file>` to walk these packets and record decisions.
```

That token is how a returning human and the resume path both find an unwalked
report. A run that reaches step 9 removes the line.

An unattended run writes **only** into `dev/local/audit-results/`. It never
touches `dev/local/prds/`: a machine that files its own findings as work has
approved them on the human's behalf.

### 9. Walk the findings

Reachable two ways: an interactive run arriving from step 8, or `--resume
<report>` on a report someone left pending. On the resume path, dispatch nobody
and re-run nothing — the findings are already established, and re-running them
would produce a second set of numbers to reconcile.

Walk them one at a time in the finding contract's `## The walkthrough packet`
shape: one packet per message, at least three real options each, recommendation
first. Record accepted / deferred / rejected in the report as you go, then close
with the minutes and delete the pending line.

**With `--decisions <file>`**, read the decisions instead of asking. The file
maps a finding's number in the report to `accept`, `defer` or `reject`, and an
optional option label:

```json
{
  "1": {"decision": "accept", "option": "Invalidate on write"},
  "2": {"decision": "reject"}
}
```

A finding the file does not mention is `deferred` — silence is never consent.
An `option` that matches no option in that packet is an **error**: stop and
report it. Do not map it to the nearest one. The point of this path is that its
output is determined by its input, and a guess breaks exactly that.

Record the minutes exactly as an interactive walk would, and note in the report
that the decisions were scripted, so nobody later reads them as a human's.
This path exists so a headless build can prove the walk works; it is not a way
to run a real walkthrough without a human.

**Accepted findings become PRDs**, one per finding or per cluster the human
approved, in the target repo's `dev/local/prds/backlog/`. Read
`references/prd-emission.md` and follow it. Emission happens on explicit
acceptance and on nothing else: deferred and rejected findings stay in the
report.

## The recon prompt

Dispatch `subagent_type: agoge:olivia` with:

1. The absolute target repo path.
2. The profile path, relative to that repo: the one that resolved in step 2 —
   `dev/local/meta/agoge-profile.md`, or the root `dev/local/agoge-profile.md`
   when that is the existing profile being refreshed. A fresh profile is
   always written to `dev/local/meta/`.
3. The `## Strategy profile contract` section from
   `references/finding-contract.md`, pasted verbatim — it names the six sections
   and their order.
4. When refreshing an existing profile: the current `## Pins and vetoes` section,
   pasted verbatim, with the instruction to copy it through unchanged.
5. When creating a fresh profile: the instruction to write
   `Authorization: not asserted` in that section and to say so in her summary.
6. The instruction that **trudy is armed or unarmed on surface alone**. The
   `Authorization:` line never decides her row, because it is resolved at
   dispatch and can arrive by a route recon cannot see. If the surface is there,
   arm her and stage her tactics like any other lane; if it is not, mark her
   `unarmed` with the surface reason. Recon deciding her on authorization writes
   a row with no tactics in it, which is how an armed lane gets dispatched blind.

She writes the profile and returns a summary. She writes nothing else.

## Notes

- Only `verified` findings are defects. `mocked` is a belief about a dependency,
  not the dependency. `unverified` means the lane could not run — report the
  attempt and how far it got.
- Judy on a repo with no browser surface must **skip loudly**. A skipped lane
  that invents findings to look useful is worse than no lane.
- The interactive browser fallback is the **master's**, not a lane's. Every
  specialist is pinned to `Read, Bash` and holds no browser tool, so a lane
  cannot reach it however the prompt is worded. Use it only in an interactive
  session, label those findings interactive-run, and never in an unattended run.
- The pack scores itself against `buvis/agoge-gym`: arm a fixture, run this
  skill at `armed/<fixture>`, then `bin/score` the JSON sidecar against the
  manifest. The gym's manifests are the answer key and are never inside an armed
  repo.
- **Scoring vocabulary never enters the target.** Seed ids belong to the gym.
  Keep the scorecard in the gym's own `dev/local/audit-results/`; the report in
  the target says only that scoring happened elsewhere. `bin/verify-seeds`
  enforces this and will refuse a tree that names a seed.
- **Re-arm between scored runs.** The report you just wrote sits in the target's
  `dev/local/` and describes every defect found. `bin/arm` removes the whole
  armed tree, so a fresh arm clears it — but a second run against the same arm
  lets its specialists read the first run's answers.
