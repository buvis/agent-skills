---
name: create-prd
description: Use when converting a plan, design doc, brainstorming output, or discovery doc into a structured PRD saved to the backlog. Triggers on "create PRD", "create PRD from plan", "make PRD", "convert to PRD", "save plan as PRD".
---

# Create PRD

Transform a plan or design document into an RPG-compliant PRD and save to the backlog.

**RPG means Repository Planning Graph**: Microsoft Research's method for dependency-aware repository planning (see <https://docs.task-master.dev/capabilities/rpg-method> and `assets/example_prd_rpg.md`). It separates WHAT (functional decomposition) from WHERE (structural decomposition) and connects them with an explicit dependency graph. It does NOT mean role-playing game: a PRD is a plain engineering document. Never add narrative framing, quest logs, or fantasy flavor; downstream tooling (`/autopilot:plan-tasks`, the review coverage gate) parses the literal section headings, including `#### Feature:`.

## Dependencies

- Plugin skills (`autopilot` plugin), consumers of what this skill writes:
  `autopilot:plan-tasks` parses the literal section headings and owns
  `default_model`; `autopilot:run-autopilot` reads the PRD frontmatter at
  Phase 0; `autopilot:design-solution` runs the `design:` sub-step. Without
  the plugin the PRD is still valid - only the automated pipeline is missing,
  so plan and implement it by hand.
- Personal skill (optional): `spike`, offered by the guess-density gate when
  the draft is too fuzzy to freeze.

## Workflow

### 0. Check for discovery doc

Before proceeding, check whether requirements were elicited:

1. If the user passed a file from `dev/local/discovery/`, or a converged spike spec from `dev/local/spikes/<slug>/SPEC.md`, requirements were elicited (the spike loop is elicitation by building). Proceed to step 1.
2. Otherwise (different file, conversation context, or no argument), warn:

> No discovery doc provided. Run `/elicit-requirements` first to validate requirements, or say "skip" to proceed without one.

Wait for the user to respond. If they say "skip" (or equivalent), proceed. Otherwise, stop and let them run `/elicit-requirements`.

This gate is advisory, not blocking. The user can always skip it for simple, well-understood features.

### 1. Identify source material

Look for plan/design content in this order:

1. **Discovery doc** - file from `dev/local/discovery/` (produced by `/elicit-requirements`)
2. **Explicit file reference** - user points to a specific markdown file (e.g. a plan file in the repo)
3. **Current conversation context** - a plan just produced by brainstorming or plan mode

Read the source file if one was referenced. Extract:

- Problem statement / objective
- Core requirements and features
- Technical constraints
- Dependencies between components
- Acceptance criteria

### 2. Choose template and load it

Pick one based on complexity:

| Plan complexity | Template | Use when |
|-----------------|----------|----------|
| Simple feature | `assets/minimal.md` | Single capability, few features |
| Standard feature | `assets/standard.md` | Multiple capabilities, clear dependencies |
| Complex system | `assets/example_prd_rpg.md` | Full RPG method needed |

**Read the chosen template file before drafting.** The PRD MUST contain every section the template defines, in the same order, with the same headings.

**Do NOT model the structure on existing PRDs in the repo**, even if they look authoritative. Repo PRDs predate or postdate the template and may drift. The template is the single source of truth for structure. Use the repo's prevailing tone and naming conventions, never its section layout.

### 3. Format as PRD

Apply the full RPG structure. All four sections are mandatory; none may be omitted, renamed, or merged into another section:

1. **Functional decomposition**: Capabilities > Features (WHAT it does). Each Feature is its own sub-block under its Capability, populated with the fields the template specifies (typically Description / Inputs / Outputs / Behavior).
2. **Structural decomposition**: Modules > Files (WHERE it lives). MUST include BOTH:
   - The Repository Structure code-block tree showing module → file mapping
   - One **Module: {Name}** block per module with Maps-to-capability / Responsibility / Exports
   A file tree alone is not sufficient.
3. **Dependency graph**: Foundation Layer / Core Layer / Integration Layer with explicit per-module dependency lists. Even single-phase PRDs MUST include this section — a one-line "no dependencies; built first" entry is fine, but the heading must be present.
4. **Implementation phases**: Topological order of tasks. Each task includes its dependency reference and an Acceptance criterion.

While drafting, mark every contract detail you invented rather than sourced from the input (an input/output shape, an interface, a behavior under an edge case) with `(guess)`. Never resolve ambiguity silently - the step 5.5 gate counts these markers.

**Unattended rule (no human mid-implementation):** The saved PRD executes in an unattended loop - nobody answers questions, tests by hand, or picks between options mid-run. A PRD whose text needs the user to test, validate, or decide anything ("user confirms", "manual check", "decide during implementation", an Open Question left for the implementer) is incorrectly created. User input belongs in the attended phases BEFORE this skill (`/spike`, `/elicit-requirements`, `/review-discovery-doc`, plan discussion - the human drives those): resolve every such point with the user now and write the answer into the PRD, or send the fuzzy part back to those phases. Acceptance criteria must be checkable headlessly by a command, test, or file assertion.

**Premise rule (observed-state tasks):** Any task whose action deletes, moves, overwrites, or edits content justified by observed repo state MUST (a) state that premise in its Feature or task text (e.g. `Premise: path X is an unused scaffold, not a live skill`) and (b) include an execution-time re-check in its acceptance criteria — a failed premise means skip and report, never force. Rationale: during the 2026-07-07 skill audit a queued task nearly archived a skill the user was actively building (`brief-portfolio` went live between audit read and PRD write), and only a lucky mid-session refresh caught it. This is authoring guidance, not structure — the `assets/` templates are unaffected.

**Metric rule (no suite-wide numbers):** Success criteria and acceptance criteria name the tests that must pass (by test name, or a `pytest -k` / `node --test` filter) and, when timing matters, the budget of the test this PRD owns. Never pin a suite total ("18 passing, up from 16", "suite under 2050ms"): a neighbouring PRD adds one test and the criterion is stale before this one is drained, and no implementer can satisfy it without deleting coverage. Rationale: batch 202609040601 deferred four such criteria across PRDs 00019 and 00033, every one unmeetable on the day it was reviewed.

### Optional frontmatter fields

PRD frontmatter is a YAML block at the top of the file delimited by `---` lines. Seven fields are recognized by the autopilot pipeline (six parsed by `/autopilot:run-autopilot` Phase 0; `default_model` is owned and re-read by `/autopilot:plan-tasks`). All six Phase-0 fields are optional; `default_model` is decided for every PRD by step 5.6:

- `catchup: run | skip | force` — controls Phase 1 (Catchup) behavior. `run` (default) honors the batch cache; `skip` bypasses catchup entirely; `force` ignores the batch cache and re-runs full catchup. Use `skip` for PRDs that need no fresh project context (e.g. small docs-only changes). Use `force` after a major structural change you want catchup to pick up.
- `rework_cap: <int>` — caps how many review-rework cycles Phase 5 will run before pausing. Default `2` (lowered from 3 on 2026-08-01: 13 of 14 completed PRDs ran to cap 3 without converging, so the third cycle was buying ~0.5 real findings for ~25% of review cost). `rework_cap: 5` allows five review cycles before pause. Raise this for genuinely hard PRDs that need more cycles; the default suits most work.
- `design: run | skip` — controls the Phase 1.5 design sub-step (between catchup and planning). `run` (default) generates a reviewed design doc via `/autopilot:design-solution` before planning; `skip` bypasses design entirely. Use `skip` for trivial PRDs that need no implementation design.
- `design_gate: user` — when set, Phase 1.5 PAUSEs for your review of the design doc (summary + unresolved non-blockers) before planning. Absent by default (design runs autonomously, no pause). Set it on PRDs where you want to vet the design before tasks are planned.
- `doubt_reviewer: codex | fable` — selects the doubt-review (Phase 8) reviewer set for this PRD. `codex` (default) uses the standard codex doubt reviewer; `fable` opts into the Eve (Claude Fable 5) doubt-review leg. Absent by default. (Only adds/parses the flag today; the Phase 8 consumer lands in a follow-on PRD.)
- `consensus_engine: legacy | shadow | workflow` — selects the engine behind Alice's consensus leg in the review phase. `legacy` (default) runs today's single review subagent. `workflow` runs the `review-fanout` workflow instead: review dimensions in parallel with schema-forced findings, dedup, and adversarial verification of every CRITICAL/HIGH before it can block. `shadow` runs both — legacy Alice gates the cycle and the workflow runs beside her, non-gating, so you can compare before opting in. Absent by default.
- `default_model: haiku | sonnet | opus` — **floor** for the per-task model tier, never a cap. Owned by `/autopilot:plan-tasks` step 4.7 (the single source of truth): `final_tier = max(classifier_tier, default_model)`, re-read from this frontmatter at Phase 6 runtime, never persisted to state. Decided per PRD by step 5.6 below; omitted only for the pass-through case that step defines.
- `model_tier_rationale: <one line>` — free text recording why step 5.6 chose that floor, so a later reader can tell a considered decision from a habit. Ignored by both parsers: Phase 0 drops unknown keys, and `/autopilot:plan-tasks` reads only `default_model`.

Example combining several:

```yaml
---
catchup: force
rework_cap: 5
design: run
design_gate: user
doubt_reviewer: fable
consensus_engine: shadow
default_model: sonnet
model_tier_rationale: transcription only - exact expressions given, additive tests
---
```

The six Phase-0 fields are optional; invalid values fall back to defaults (a one-line warning is logged).

### 4. Split if needed

If PRD exceeds ~200 lines or has loosely coupled parts:

- Split into separate PRD files
- Each PRD should be self-contained
- Name related PRDs with shared prefix: `00001-auth-login-v1.md`, `00002-auth-session-v1.md`

### 5. Verify structure before saving

Walk the chosen template top-to-bottom and confirm every `##`/`###` heading the template defines is present in your draft, in the same order, with the same wording. If any are missing, renamed, or out of order, revise before saving. This is the gate that prevents drift toward whatever PRD style happened to dominate the repo's existing files.

### 5.5. Guess-density gate

Count unresolved contract markers in the draft: `(guess)`, `TBD`, `TODO`, plus Open Questions that bear on any Feature's Inputs/Outputs/Behavior. **3 or more:** do not save yet - offer via AskUserQuestion: **Spike the fuzzy part** (run the spike skill with the draft as its rough spec; on convergence rewrite the guessed fields from observed behavior, then re-run this gate), **Resolve now** (answer them in conversation), or **Save anyway** (explicit override - the markers stay in the PRD and plan-tasks will freeze them as written). **2 or fewer:** proceed to step 5.6.

### 5.6. Model-tier gate

Decide the `default_model` floor for this PRD and write it into the frontmatter. Run this on every PRD, never by habit: a blanket `opus` costs several times what a cheaper tier spends doing the same work correctly, and a blanket `sonnet` hands judgment work to a model that will transcribe its way past it.

Run the gate AFTER step 5.5, not before. Resolving guesses is what turns a vague Behavior field into an exact expression, and that is precisely what the rubric measures.

**`default_model` is a floor, not a cap** (`/autopilot:plan-tasks` step 4.7: `final_tier = max(classifier_tier, default_model)`). `sonnet` does not stop the per-task classifier raising an individual task to `opus` on a contract edit or algorithmic risk; it only stops the PRD dropping to `haiku`. That safety net is why a well-specified PRD should not be pinned to `opus` out of caution.

**Set `opus` if ANY row holds.** One hit is enough - stop at the first.

| Escalator | It looks like |
|-----------|---------------|
| Invented algorithm or predicate | The PRD names a behavior but not the expression implementing it: an ownership test, a classification rule, a heuristic |
| Concurrency or timing | Thread pools, deadlines, cancellation, async ordering - anything where interleaving decides correctness |
| Equivalence obligation | New code must produce byte-identical or behavior-identical output to what it replaces |
| Invented contract | A return shape, class name, message format, or wording with no source value, especially when another PRD consumes it |
| Destructive blast radius | Flips a default that deletes or moves data, widens a guard on a destructive path, or writes outside the repo |
| Generative prose at volume | More than a couple of authored descriptions or entries where the writing quality IS the deliverable |
| Cross-cutting shape change | One signature or return shape changed across two or more independent modules or apps |

**Otherwise `sonnet`**, and only when all three hold:

- Every non-test edit carries its exact final text, expression, or attribute value in the task line. The implementer transcribes; it never designs.
- Each acceptance criterion is a runnable command that fails loudly. No criterion can pass vacuously.
- A wrong implementation breaks a named test rather than degrading silently.

**Omit `default_model` entirely** when the PRD is mechanical enough that `haiku` is acceptable - the classifier's `mechanical` row then reaches it. Writing `sonnet` is the explicit statement that this PRD is too consequential for `haiku`. Write `model_tier_rationale` in this case too, so the omission reads as a decision rather than a lapse.

Two failure modes to watch when the verdict is `sonnet`, both worth naming in the rationale rather than escalating the whole PRD:

- **Premise-skip discipline.** Tasks carrying the step-3 premise rule ("re-check at execution; a failed premise means skip and report") depend on the implementer stopping rather than forcing. That instruction has to be in the task text, not implied.
- **Edits to existing tests.** A task that repoints or rewrites tests already in the tree is the one place a wrong turn weakens coverage silently instead of going red. Pin the expected count with an `rg -c` premise.

Record the verdict:

```yaml
default_model: sonnet
model_tier_rationale: transcription only - exact expressions given, additive tests
```

Put NO comment on the `default_model:` line. The Phase-0 parser (`run-autopilot/cli/frontmatter.py`) is not PyYAML: it splits on the first colon and takes the rest verbatim, so `sonnet  # mechanical` becomes an invalid value and the floor is dropped without an error.

This is authoring guidance, not structure - the `assets/` templates carry no frontmatter block and are unaffected.

### 6. Save to backlog

```bash
# Create directory if needed
mkdir -p dev/local/prds/backlog

# Determine next sequence number
# Scan ALL prds in dev/local/prds (backlog, wip, done, hold) AND dev/local/discovery for highest existing sequence
# Extract 5-digit prefix from filenames matching pattern NNNNN-*.md
# Increment by 1, pad to 5 digits

# Save PRD with sequence prefix
```

**Concurrent-creation collision rule.** The scan-then-write is not atomic — a second `/create-prd` (or a machine PRD writer) running in parallel can claim the same `NNNNN` between your scan above and your save. So **after writing, re-run the sequence scan**: if your `NNNNN` now appears on a file you did NOT just write (a collision), renumber yours to the next free number, save under the new name, delete your original, and re-scan once more to confirm uniqueness. Best-effort, not a lock — two writers who re-scan at the exact same instant can still both pick the next number; `/review-prd-backlog` catches that residual case (it flags colliding prefixes).

## File Naming Convention

```text
{sequence}-{feature-slug}-v{version}.md

Where:
- sequence: 5-digit zero-padded number (00001, 00002, ...)
- Sequence determined across ALL subdirs in dev/local/prds/

Examples:
- 00001-user-auth-v1.md
- 00002-api-rate-limiting-v1.md
- 00003-dashboard-widgets-v2.md
```

## Sequence Number Logic

1. List all `.md` files in `dev/local/prds/**` and `dev/local/discovery/`
2. Extract leading 5-digit prefixes matching `^[0-9]{5}-`
3. Find max sequence number (default 0 if none exist)
4. New sequence = max + 1, zero-padded to 5 digits

## Versioning (bump `-vN` vs allocate a new number)

The `NNNNN` sequence identifies a **unit of work**; the `-vN` suffix identifies a **spec revision** of that same unit. Decide with:

- **Editing a backlog PRD** (not yet worked) → **no version bump**. It is a working document; revise it in place. Bump to `-v2` (same `NNNNN`) only when you deliberately want to PRESERVE the superseded spec beside the new one — rename the old to keep it, then write the `-v2`.
- **A done PRD that needs re-work** (the shipped design was wrong, or a follow-up materially re-specs the *same* feature) → write a new `-v2` under the **SAME `NNNNN`**, and reference the v1 it supersedes in the PRD body. Same feature identity → same number, new version.
- **A genuinely separate capability** — even one closely related → allocate a **NEW sequence number** with a shared slug prefix (`00001-auth-login-v1`, `00002-auth-session-v1`), NOT a version bump. Different work → different number.

The version suffix never changes the sequence scan (it keys on `NNNNN`), so a `-v2` alongside a `-v1` under one number is fine — both are found, neither collides.

## Directory Structure

```text
dev/local/prds/
├── backlog/    # Planned but not started
├── wip/        # Currently being implemented
├── hold/       # Parked (human HOLD verdicts + machine stalls); autopilot never reads it
└── done/       # Completed PRDs (for reference)
```

## PRD Lifecycle

1. **Create**: Save to `backlog/`
2. **Start work**: Move to `wip/`
3. **Park** (optional): Move to `hold/`; a human moves it back to `backlog/` or `wip/` to resume
4. **Complete**: Move to `done/`

A parked PRD keeps its number — that is why the sequence scan MUST include `hold/`, or a new PRD can duplicate a parked one's number.

## Assets

- `assets/minimal.md` - Quick PRD for simple features (~50 lines)
- `assets/standard.md` - Standard PRD structure (~100 lines)
- `assets/example_prd_rpg.md` - Full RPG method reference
