---
catchup: force
---

# Distil Memory Candidates: Extraction and Funnel

Source: `~/.claude/dev/local/discovery/00147-distil-memory-from-transcripts.md`
(comprehensive, 2026-08-26). Slice 1 of 3, per that doc's own PRD slicing note:
extraction, funnel, yield report and dry-run. Slice 2 is the distiller
(`00008`), slice 3 the queue and walkthrough (`00009`). The doc says explicitly
that the slices must not be merged into one PRD.

## Overview

### Problem Statement

Facts worth carrying between sessions get established and then lost, unless
someone deliberately writes a memory file. The instinct pipeline was built to
close this gap, never delivered a single fact, and was deleted: it wrote to a
path its own encoder computed wrong, and what it produced were tautologies with
trigger and action set to the same string. The want survives the implementation,
and the corpus that could answer it exists - cellar archives 2,371 transcripts
across 25 projects, 1.4 GB. Nothing may read that wholesale, so before any model
sees anything there has to be a funnel that bounds it.

### Target Users

The solo maintainer, running an on-demand sweep - first as a single-project
pilot, later over full history.

### Success Metrics

- A run over a 30-day window completes and reports counts at every funnel stage,
  including zero.
- A dry run reports per-stage counts without calling any strong model.
- A contract check fails loudly, naming the version it resolved, when the
  installed claude-checkup is older than `0.2.2`.
- The assistant-side extraction has tests that fail on each injected shape it can
  encounter.

## Functional Decomposition

### Capability: Corpus access

#### Feature: Resolve the transcript parser from the plugin cache

- **Description**: Import claude-checkup's transcript parser without pinning a
  version.
- **Inputs**: `~/.claude/plugins/cache/buvis-plugins/claude-checkup/*/skills/audit-sessions/scripts/parser.py`.
- **Outputs**: The imported parser module and the version it came from.
- **Behavior**: Globs the cache, parses each directory name into a version tuple
  and takes the max - the house pattern from
  `hooks/strunk-ruling-inject.py:resolve_strunk_skills_dir()`. The cache root is
  a single named constant, so claude-checkup's coming migration to the
  agent-plugins standard is one edit.

#### Feature: Fail loudly on a stale parser

- **Description**: Refuse to parse with the old provenance rules.
- **Inputs**: The resolved version.
- **Outputs**: Either a green contract check, or a loud failure naming the
  resolved version and the minimum required.
- **Behavior**: The user-side provenance fix is commit `d10ecb1`, which drops
  `promptSource == "sdk"` rows (416 → 246 on the real corpus), released as
  claude-checkup `0.2.2`. Version 0.2.1 still over-counts by 41%, so `0.2.2` is
  the minimum this skill accepts. The check also asserts the
  imported parser exposes what this skill calls, so a rename in the other repo
  surfaces as a named failure rather than a wrong result.

#### Feature: Select the transcript set

- **Description**: Decide which transcripts a run reads.
- **Inputs**: `--days` (default 30), `--all`, `--project <name>`.
- **Outputs**: The list of transcript files for this run.
- **Behavior**: The lookback window is the first bound on corpus size.
  `--project` restricts a run to one project's store, which is how the first
  pilot runs before any full sweep - the Risks section depends on it existing.

### Capability: The funnel

#### Feature: Slice on verification markers

- **Description**: Cut 1.4 GB down to candidate slices for free.
- **Inputs**: The selected transcripts, assistant-role text only.
- **Outputs**: Text slices carrying a verification marker, with their source
  transcript and offset.
- **Behavior**: Regex only, no model. Measured on 406 transcripts: 224 sessions
  carry a marker, 528 hits, median 2 per session, max 16. The marker is a cheap
  recall filter, not a precision one - most hits are transient process
  verifications ("all 264 tests pass") - and separating those from durable facts
  is the next stage's job, not this one's.

#### Feature: Extract assistant-side content safely

- **Description**: Keep injected content out of the slices.
- **Inputs**: Parsed transcript entries.
- **Outputs**: Assistant-authored text only.
- **Behavior**: The user-side filter is solved upstream; the assistant side has
  no equivalent and needs its own check. Each injected shape it can encounter is
  enumerated during design and gets a test that fails when the shape leaks
  through. This is the failure that killed the last system, one layer up: a
  distiller reading injected content proposes the repo's own rules back as
  discoveries.

#### Feature: Triage cheaply before the expensive model

- **Description**: Discard transient verifications on a cheap tier.
- **Inputs**: The marker slices.
- **Outputs**: The survivors, plus a discard count.
- **Behavior**: A Haiku-tier pass whose only job is "transient verification" or
  "possibly durable". It exists to keep the strong model reading only
  twice-filtered slices, which is what holds the sweep inside the 30% meta
  budget. Every model call in this feature goes through one seam,
  `judge(prompt, tier)`, defined here and imported by the distiller in PRD
  00008 rather than reinvented there. Its default shells out to the headless
  `claude` CLI the way the `use-sonnet` skill documents; tests inject a stub, so
  no test ever spends. One seam means the model tier is one edit, not two.

### Capability: Reporting

#### Feature: Report the yield out loud, including zero

- **Description**: Never let a run be silently empty.
- **Inputs**: The counts at every stage.
- **Outputs**: A per-stage count table, printed and written to
  `dev/local/audit-results/`.
- **Behavior**: Every run states transcripts read, slices matched, slices kept
  after the assistant-side filter, survivors after cheap triage. A run that finds
  nothing says so - the retired pipeline's silence is the thing being excluded.
  The report ends with the verbatim how-to-proceed block.

#### Feature: Dry-run the funnel

- **Description**: Price a sweep before paying for it.
- **Inputs**: `--dry-run` plus the usual selection flags.
- **Outputs**: The same per-stage counts, with no strong-model call at all.
- **Behavior**: Promoted from nice-to-have to must-have, because the Risks
  section names it as the mitigation for a first `--all` sweep costing more than
  expected.

## Structural Decomposition

### Repository Structure

```
skills/
└── distil-memory/
    ├── SKILL.md                  # Maps to: Reporting (the invocation contract)
    └── scripts/
        ├── corpus.py             # Maps to: Corpus access
        ├── funnel.py             # Maps to: The funnel
        ├── test_corpus.py        # Tests for parser resolution and selection
        └── test_funnel.py        # Tests for markers, extraction, triage
```

### Module: corpus.py

- **Maps to capability**: Corpus access
- **Responsibility**: Resolve the parser, assert the contract, select
  transcripts.
- **Exports**:
  - `resolve_parser()` - `(module, version)` from the plugin cache
  - `assert_contract(version)` - loud failure below the minimum
  - `select_transcripts(days=30, all=False, project=None)` - file list

### Module: funnel.py

- **Maps to capability**: The funnel, Reporting
- **Responsibility**: Marker slicing, assistant-side extraction, cheap triage,
  and the per-stage counts.
- **Exports**:
  - `slice_on_markers(transcripts)` - slices with provenance
  - `assistant_only(entries)` - assistant-authored text
  - `judge(prompt, tier)` - the one model seam, injectable in tests
  - `triage(slices, judge=judge)` - survivors plus discard count
  - `render_yield(counts)` - the report

## Dependency Graph

### Foundation Layer (Phase 0)

No dependencies - built first.

- **corpus.py**: nothing may read the corpus before the parser is resolved and
  its version asserted.

### Core Layer (Phase 1)

- **funnel.py**: Depends on [corpus.py]

### Integration Layer (Phase 2)

- **distil-memory SKILL.md**: Depends on [funnel.py, corpus.py]

## Implementation Phases

### Phase 0: Foundation

**Goal**: The corpus can be reached, and only through a parser new enough to
trust.

**Tasks**:

- [ ] Implement `resolve_parser()` in `scripts/corpus.py` using the
  version-glob idiom, with the cache root as one named constant (no deps)
  - Acceptance: given a fixture cache holding `0.2.1` and `0.2.2`, it resolves
    `0.2.2`; the root constant appears exactly once in the file.
- [ ] Implement `assert_contract()` with a minimum version of `0.2.2` (no deps)
  - Acceptance: a resolved version below `0.2.2` raises, naming the resolved
    version and the minimum; the message says the installed plugin over-counts
    rather than "parse failed".
- [ ] Implement `select_transcripts()` with `--days`, `--all` and `--project`
  (no deps)
  - Acceptance: a fixture store yields only transcripts inside the window;
    `--project` restricts to one store; `--all` returns everything.

**Exit Criteria**: `uv run --with pytest pytest scripts/test_corpus.py` passes
with zero failures.

### Phase 1: Core

**Goal**: The funnel bounds the corpus and reports what it did.

**Tasks**:

- [ ] Implement `slice_on_markers()` over assistant-role text (depends on:
  Phase 0)
  - Acceptance: on a fixture transcript carrying two markers, two slices are
    returned, each with its source file and offset.
- [ ] Implement `assistant_only()` and enumerate the injected shapes it must
  reject (depends on: Phase 0)
  - Acceptance: one test per enumerated shape, each failing if that shape's text
    reaches the slices; the enumeration is written into the module docstring so a
    later reader can check it against the schema.
- [ ] Implement `judge(prompt, tier)` as the single model seam, defaulting to the
  headless `claude` CLI, and `triage()` as a cheap-tier pass over it with a
  discard count (depends on: Phase 0)
  - Acceptance: given fixture slices - a test-pass verification and a durable
    fact - and a stub judge, the transient one is discarded and the count
    reflects it; the whole test run makes no real model call, provable by a test
    that fails if the default judge is reached.
- [ ] Implement `render_yield()` and the `--dry-run` path (depends on: Phase 0)
  - Acceptance: a dry run over a fixture corpus prints counts for every stage
    including zeros and makes no strong-model call, provable by a test that fails
    if the strong-model entry point is reached.

**Exit Criteria**: `uv run --with pytest pytest scripts/test_funnel.py` passes
with zero failures.

### Phase 2: Integration

**Goal**: The funnel is invocable and its numbers are real.

**Tasks**:

- [ ] Write `skills/distil-memory/SKILL.md` covering invocation, the flags, the
  yield report, and a `## Dependencies` section naming claude-checkup's
  `parser.py` and its minimum version (depends on: Phase 1)
  - Acceptance: the create-skill validator passes; the description is trigger-led
    and under 250 chars.
- [ ] Run the funnel over one project with `--dry-run` and record the numbers in
  `dev/local/audit-results/` (depends on: Phase 1)
  - Premise: claude-checkup `0.2.2` or newer is installed (the release that
    carries `d10ecb1`), and `~/.claude/projects/` still symlinks into the cellar
    repo with the target project's transcripts present. Re-check at execution: an
    older claude-checkup means `assert_contract()` refuses by design, so stop and
    report rather than lowering the minimum; if the project has no transcripts,
    run against one that does and name the substitution.
  - Acceptance: the report names transcripts read, slices matched, slices kept
    and survivors, and states the resolved claude-checkup version.

**Exit Criteria**: A single-project dry run produces a per-stage count table and
no model spend beyond the cheap tier.

## Test Strategy

### Critical Scenarios

- **Happy path**: a 30-day window over one project → slices found, counts
  reported at every stage.
- **Happy path**: `--dry-run` → identical counts, zero strong-model calls.
- **Edge case**: a window with no markers at all → the report says zero out loud
  rather than printing nothing.
- **Edge case**: a transcript predating `promptSource` and `origin.kind` → it is
  kept, not silently dropped, matching the upstream negative-check choice.
- **Error case**: installed claude-checkup is 0.2.1 → loud failure naming the
  version, no parsing attempted.
- **Error case**: an injected shape reaches the assistant-side slices → its test
  fails, because that is the exact failure that killed the retired pipeline.

## Risks

- **The distiller reads injected content and proposes the repo's own rules back
  as discoveries**: the user side is fixed upstream; the residual risk is the
  assistant side and a stale installed plugin. Mitigation: the enumerated-shape
  tests and the loud version check.
- **A first `--all` sweep costs more than expected**: mitigation is the funnel
  plus the dry-run, both must-haves here.
- **`parser.py` changes underneath the skill**: it lives in another repo, so a
  break surfaces at runtime. Mitigation: the contract check asserts what is
  imported and names the version it resolved.
- **The plugin cache root moves** when claude-checkup migrates to the
  agent-plugins standard. Mitigation: the root is one named constant.
- **Marker abundance is mistaken for candidate precision**: measured, most hits
  are transient. Mitigation: this slice only recalls; precision is slice 2's job
  and this PRD does not claim it.

## Post-completion notes (2026-09-05)

Deferred by batch 202608290848 (cycle 2 spec divergences), decided 2026-09-05
in `dev/local/audit-results/deferred-walk-202608290848-2026-09-05.md`.

- Phase 1's exit command `uv run --with pytest pytest scripts/test_funnel.py`
  no longer exists as written: the file was split into
  `test_funnel_extraction.py`, `test_funnel_report.py` and
  `test_funnel_triage.py` under the 800-line cap. Run the directory.
- Module Exports names `assert_contract(version)`; the shipped signature is
  `assert_contract(version, parser_module, minimum=_MIN_VERSION)`, as the
  design doc signed. This note corrects the PRD text; the code stands.
- `judge()` passing the slice text as a CLI argument, and persisting a
  transcript per call, is PRD 00072.
