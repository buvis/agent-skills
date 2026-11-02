---
eligibility: test -x "$HOME/.local/share/mise/installs/pipx-buvis-gems/latest/bin/braid"
design: skip
default_model: sonnet
model_tier_rationale: deletion plus exact replacement text; the one judgment point (premise re-check) is spelled out in the task text
---

# Retire the bundled braid package

Source: `~/.claude/docs/dev/project-management/discovery/00182-layer-agent-rules-across-hosts.md` (phase 1, retirement step). Runs after buvis/gems PRD 00115 is released and installed; the `eligibility` check holds the PRD until the gems `braid` binary exists.

## Overview

### Problem Statement

braid now ships in `buvis-gems` (gems PRD 00115). This repository still carries
the old `agent-skills-braid` package, its launcher and its tests, so two braids
exist and the README documents the old one (`~/.config/agent-skills`,
`AGENTS_ROOT`, `python bin/braid.py`). Discovery 00182: content repos stop
carrying a Python package.

### Target Users

Anyone reading or cloning this repository.

### Success Metrics

- `rg -n "agent_skills_braid|agent-skills-braid|bin/braid" --glob '!CHANGELOG.md' --glob '!docs/dev/**'` finds nothing.
- `uv run pytest tests/test_skill_placement.py tests/test_ci_workflow.py tests/test_conftest_fixtures.py` passes.

## Functional Decomposition

### Capability: Remove the package

#### Feature: Delete code and tests
- **Description**: Remove braid's source, launchers and tests.
- **Inputs**: `src/agent_skills_braid/cli.py`, `src/agent_skills_braid/__init__.py`, `bin/braid`, `bin/braid.py`, `tests/test_braid.py`, `tests/test_braid_check.py`.
- **Outputs**: Those files gone.
- **Behavior**: Premise: the gems `braid` binary at `$HOME/.local/share/mise/installs/pipx-buvis-gems/latest/bin/braid` exists and `"$HOME/.local/share/mise/installs/pipx-buvis-gems/latest/bin/braid" --help` exits 0. Re-check at execution; if it fails, skip the whole PRD and report.

#### Feature: Make the project a non-package
- **Description**: `pyproject.toml` keeps dev tooling only.
- **Inputs**: `pyproject.toml`.
- **Outputs**: No build system, no script, no wheel target.
- **Behavior**: Delete the `[build-system]` table, the `[project.scripts]` table and the `[tool.hatch.build.targets.wheel]` table. Set `name = "agent-skills"`, `description = "Portable agent skills for AI coding assistants"`, keep `version`, and add `[tool.uv]` with `package = false`. Keep `[dependency-groups]`, `[tool.pytest.ini_options]`, `[tool.ruff]` and `[tool.ruff.lint]` unchanged. Run `uv lock` so `uv.lock` matches.

### Capability: Point readers at gems

#### Feature: CI step name
- **Description**: The lint step no longer lints braid.
- **Inputs**: `.github/workflows/ci.yml`.
- **Outputs**: Step `- name: Lint braid` renamed to `- name: Lint`.
- **Behavior**: Command unchanged.

#### Feature: README and AGENTS.md
- **Description**: Documentation names gems braid and `~/.config/braid`.
- **Inputs**: `README.md`, `AGENTS.md`, `CHANGELOG.md`.
- **Outputs**: Edited text.
- **Behavior**: In `README.md`: (1) replace the first paragraph (lines starting `Portable personal skills` through `host-specific discovery paths.`) with `Portable personal skills for AI coding assistants. They reach each assistant through braid, the composer in [buvis-gems](https://github.com/buvis/gems).`; (2) replace the body of `## Install` with a code block `git clone https://github.com/buvis/agent-skills ~/git/src/github.com/buvis/agent-skills`, `uv tool install buvis-gems`, `mkdir -p ~/.config/braid/sources.d`, `echo ~/git/src/github.com/buvis/agent-skills > ~/.config/braid/sources.d/personal`, `braid --dry-run`, `braid`, `braid --check`, followed by the sentence `braid usage, flags, Kiro enrollment and Windows behavior are documented in buvis-gems (docs/source/tools/braid.rst).`; (3) replace `~/.config/agent-skills/sources.d/` with `~/.config/braid/sources.d/` everywhere; (4) delete everything from the `## braid` heading through the paragraph ending `no Bash runtime\nis required.`, keeping the two `.braidignore` paragraphs that follow under a new heading `## .braidignore`, and change `Braid loads it from\nthe tool repository, ~/.agents,` to `braid loads it from\n~/.agents,`. In `AGENTS.md`, replace `` `skills/` is the only directory braid scans (`_skills_directory`) `` with `` `skills/` is the only directory braid (buvis-gems) scans for skills ``. In `CHANGELOG.md` `[Unreleased]`, add `### Removed` entry `- **braid**: the bundled agent-skills-braid package; install braid from buvis-gems and move sources.d to ~/.config/braid`.

## Structural Decomposition

### Repository Structure

```text
src/agent_skills_braid/cli.py        # deleted
src/agent_skills_braid/__init__.py   # deleted
bin/braid                            # deleted
bin/braid.py                         # deleted
tests/test_braid.py                  # deleted
tests/test_braid_check.py            # deleted
pyproject.toml                       # non-package project
uv.lock                              # relocked
.github/workflows/ci.yml             # step rename
README.md                            # gems pointer
AGENTS.md                            # scan wording
CHANGELOG.md                         # Removed entry
```

### Module: repository metadata
- **Maps to capability**: Remove the package, Point readers at gems
- **Responsibility**: Leave a content-only repository.
- **Location**: `pyproject.toml`, `uv.lock`, `.github/workflows/ci.yml`, `README.md`, `AGENTS.md`, `CHANGELOG.md`
- **Exports**: none

## Dependency Graph

### Foundation Layer (Phase 0)
No dependencies - built first.

- **repository metadata**: deletions and edits in one phase.

### Core Layer (Phase 1)
- none

### Integration Layer (Phase 2)
- none

## Implementation Phases

### Phase 0: Foundation
**Goal**: The repository holds content only.

**Tasks**:
- [ ] Re-check the premise, then delete `src/agent_skills_braid/cli.py`, `src/agent_skills_braid/__init__.py`, `bin/braid`, `bin/braid.py`, `tests/test_braid.py`, `tests/test_braid_check.py`, and edit `pyproject.toml` and `uv.lock` as specified (no deps) - Acceptance: `test ! -e src/agent_skills_braid && test ! -e bin/braid.py`; `uv lock --check` exits 0; `uv run pytest tests/test_skill_placement.py tests/test_ci_workflow.py tests/test_conftest_fixtures.py` passes.
- [ ] Apply the CI, README, AGENTS.md and CHANGELOG.md edits as specified (depends on: first task) - Acceptance: `rg -n "agent_skills_braid|agent-skills-braid|bin/braid|AGENT_SKILLS_CONFIG|config/agent-skills" --glob '!CHANGELOG.md' --glob '!docs/dev/**'` finds nothing; `rg -n "name: Lint$" .github/workflows/ci.yml` hits once.

**Exit Criteria**: Full gate green: `uv run pytest`, `uv run ruff check`, `uv run ruff format --check`.

## Test Strategy

### Critical Scenarios
- **Happy path**: suite collects without braid tests and passes.
- **Error case**: gems braid missing → PRD skipped, nothing deleted.

## Risks

- **This machine runs the old braid through `~/.agents/bin/braid`**: that link dangles after this PRD. The buvis home PRD 00183 removes it and moves `sources.d`; it carries the same eligibility check.
