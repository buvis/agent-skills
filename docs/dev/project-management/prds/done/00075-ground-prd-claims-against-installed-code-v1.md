---
default_model: opus
model_tier_rationale: invented predicates (identifier filter, citation-to-symbol binding) whose output a second skill's gate lens consumes as Blocking
catchup: force
design: run
---

# Ground PRD claims against installed code

## Overview

### Problem Statement

`create-prd` freezes a PRD for an unattended loop, and its last checks before the save are the guess-density count (`### 5.5. Guess-density gate` in `skills/create-prd/SKILL.md`) and the model-tier gate (`### 5.6. Model-tier gate`). Both read only what the author wrote; neither asks whether a name the author believes exists actually exists, whether a `file:line` still says what the PRD claims, or whether a library behaves as the PRD prescribes. The cost landed in another of the author's repositories (link-ok: evidence lives in that repo's local audit results, not cited by path here). Its 2026-09-05 backlog gate raised 24 Blocking findings on a backlog four earlier gates had passed; 12 were "the PRD prescribed an implementation that cannot work", 5 of them against third-party libraries and 7 against repo code (that repo's 2026-09-06 refactor assessment, finding F4). The library five were all checkable from installed crate source: git2 0.21.0's push progress callback returns unit (B04); async-graphql 7.2.1 rejects a String variable in a JSON position (B08); the project's `Value` has no Null and UniFFI 0.29.5 lifts HashMap, not BTreeMap (B09); axum-core 0.5.6 documents that DefaultBodyLimit excludes direct body consumption (B11); subtle 2.6.1's slice compare short-circuits on length (B12). The repo seven were plain `rg` misses: fetch/push report producers that do not exist (B18), an `existing_id` the unique-violation error never carries (B15), an SQL shape with no carrier for `Ok(String)` (B24), and four more (B01, B02, B19, B23). A later pass counted 16 identifiers referenced by 19 PRDs that exist nowhere in code, with 5 producer PRDs deferring the name to their design phase. The same class ran inside that repo's July batch: four consecutive PRDs asserted a transport or verb surface that did not exist ("FOURTH-CONSECUTIVE-PRD PATTERN" in the batch's deferred ledger), and paid for in review: cycle 1 of the first returned 18 findings with 4 CRITICAL, cycle 2 returned 27, and its three largest review sessions cost $25.45, $87.09 and $49.19 (that repo's loop metrics).

What neighbours already cover, so this PRD adds only the delta:

- `check_links.py` (`skills/review-prd-backlog/scripts/check_links.py:25-30`, `:66-71`) resolves path existence for `docs/dev/project-management/`, `~/.claude/` and `/Users/` prefixes, PRD numbers and memory links, with a `link-ok:` waiver (`:28`). It never reads a line number, an identifier or a package. Done PRD 00047 (`docs/dev/project-management/prds/done/00047-check-links-repeated-stats-v1.md`) only cached its `resolve_path`; nothing here touches that function.
- `review-prd-backlog` lens D (`skills/review-prd-backlog/SKILL.md:95-103`) tells the reviewer to check grounding with `rg` by hand and step 1 runs `check_links.py` mechanically (`:46`). The gate is the last attended stop; the author never ran the check, so every miss costs a gate cycle.
- This repo has no discovery directory; no discovery doc covers this.

Delta: one stdlib-only script that extracts backticked identifiers, `file:line` citations and crate-qualified API names from a PRD and checks each against the repo and the installed package source; a create-prd step between 5.5 and 5.6 that blocks the save on a missing citation or an undeclared unresolved symbol; the same script as a mechanical lens in the backlog gate so author and gate agree.

### Target Users

PRD authors (attended sessions and machine writers such as `assess-evolution` roadmaps), the `review-prd-backlog` reviewer, and the unattended loop that otherwise inherits invented producers as wrong-TDD lock-in.

### Success Metrics

- `uv run pytest skills/create-prd/scripts/test_ground_prd.py -q` reports 0 failed and 0 errors; every scenario in Test Strategy is a named test in that file.
- A fixture PRD shaped like B18 (symbol absent from the fixture repo, not declared new) exits 1; a fixture shaped like B04 (API absent from the fixture registry) exits 0 with one `unverified` row; a fixture citing a line past end of file exits 1.
- `rg -c "^### 5.55. Grounding gate" skills/create-prd/SKILL.md` prints 1; `rg -c "ground_prd.py" skills/review-prd-backlog/SKILL.md` prints at least 2 (Dependencies plus step 1).
- `uv run python3 skills/create-skill/scripts/validate_skill.py skills/create-prd` and the same for `skills/review-prd-backlog` exit 0.

## Functional Decomposition

### Capability: Grounding checker

A Python 3.10+, stdlib-only script (`subprocess` for `rg`, regex for `Cargo.lock`; no `tomllib`, which is 3.11+) that turns a PRD draft into a table of grounded and ungrounded claims.

#### Feature: Extract claims from a draft

- **Description**: Collect the three claim kinds from a Markdown PRD, skipping the YAML frontmatter block and fenced code blocks.
- **Inputs**: PRD path(s); a directory argument expands to its `*.md` files.
- **Outputs**: Per claim: kind (`citation`, `symbol`, `library`), token, `prd:line`.
- **Behavior**: A citation is `path:N` or `path:N-M`, optionally followed by `,N-M` ranges, where `path` has a file extension; `~` expands to home, absolute paths stay, anything else resolves under `--root`. A symbol is an inline backticked token of length 3 or more matching identifier segments joined by `::` or `.`, excluding tokens whose last segment is a file extension (`py`, `rs`, `md`, `toml`, `json`, `jsonl`, `yml`, `yaml`, `sh`, `js`, `ts`, `txt`, `lock`, `html`, `css`), tokens containing `/`, whitespace or a leading `-`, and tokens matching check_links' placeholder shapes (`*?<>{}$`, `...`, `NNNNN`). A symbol whose first segment names a known package (next Feature: any crate named in `Cargo.lock`, any `node_modules/` entry, any site-packages entry, installed or not) is a library claim instead. A line containing `link-ok:` contributes no claims, matching `check_links.py:28`.

#### Feature: Verify citations and repo symbols

- **Description**: Every citation must exist and, when the same Markdown line names a symbol, the cited lines must contain it; every symbol must resolve in the repo or be declared new.
- **Inputs**: Claims; `--root`; `rg` on PATH.
- **Outputs**: Status per claim: `ok`, `missing`, `unresolved`, `declared-new`.
- **Behavior**: `missing` when the file is absent, `N` or `M` exceeds its line count, or the cited range contains none of the symbols backticked on the citing Markdown line; the range passes when at least one of those symbols occurs in it; a citing line with no backticked symbol is checked for file and range existence only. A symbol resolves when every segment of length 3 or more hits `rg -F -w -q --no-messages --glob '!docs/dev/**' -- <segment> <root>`; the glob is explicit (it covers both `docs/dev/project-management/`, where PRDs live, and `docs/dev/tmp/`) so a name that lives only in other PRDs stays `unresolved`, which is the 16-phantom-identifier class. A symbol is `declared-new` when it is backticked on any line whose text, after an optional list marker, starts with `New symbols:`. Results are cached per segment for the process.

#### Feature: Verify library claims against installed source

- **Description**: A crate- or package-qualified API is searched in the installed source; absence warns, never blocks.
- **Inputs**: Claims; `--root`; `--cargo-registry` (default `~/.cargo/registry/src`).
- **Outputs**: Status `ok`, `unverified`, or `waived`.
- **Behavior**: Known packages are: every `name = "<crate>"` in `<root>/Cargo.lock`; every directory under `<root>/node_modules/`; every directory or `.py` file under `<root>/.venv/lib/python*/site-packages/`. Package identity comes from those lists alone, so a claim is classified the same way on every host. Source presence is resolved separately: a crate's source is `<registry>/*/<crate>-<version>` where `<version>` is the crate's `version` line (git2 0.21.0 resolves this way on the author's host); a node or Python package's source is its listed directory. When the source exists, each remaining segment must hit `rg -F -w -q` inside it for `ok`; when the source is absent, or a segment misses, the status is `unverified`. A citing line containing the literal `(unverified library claim)` reports `waived`.

#### Feature: Report and exit

- **Description**: Print a table or JSON and exit with a code the author and the gate can branch on.
- **Inputs**: Statuses; `--json`.
- **Outputs**: Table columns `status | kind | token | prd:line | detail`, sorted `missing`, `unresolved`, `unverified`, then the rest, followed by `<n> blocking, <m> unverified, <k> declared new`; JSON `{"rows": [...], "blocking": n, "unverified": m}` with the same fields per row.
- **Behavior**: Exit 0 when no row is `missing` or `unresolved`; exit 1 otherwise; exit 2 when `rg` is not on PATH or an input is unreadable, with the reason on stderr. `unverified` never changes the exit code.

### Capability: Authoring gate

#### Feature: Step 5.55 in create-prd

- **Description**: A step between 5.5 and 5.6 that runs the checker on the draft and blocks the save on exit 1.
- **Inputs**: The draft (written to `docs/dev/tmp/` first when it exists only in conversation).
- **Outputs**: A grounded draft with `New symbols:` lines and `(unverified library claim)` markers.
- **Behavior**: The step text tells the author to fix each `missing` row by re-reading the file and correcting the citation, each `unresolved` row by correcting the name or adding it to a `New symbols:` line in the Module block that creates it, and each `unverified` row by appending `(unverified library claim)` to that line; exit 2 is reported and stops the save. Step 3 gains the `New symbols:` authoring rule beside the guess-marking rule at `skills/create-prd/SKILL.md:80`.

### Capability: Gate lens

#### Feature: Grounding resolution in review-prd-backlog step 1

- **Description**: The gate runs the same script over `backlog/` and `wip/` as a mechanical floor under lens D.
- **Inputs**: `python3 ~/.agents/skills/create-prd/scripts/ground_prd.py --root . --json docs/dev/project-management/prds/backlog docs/dev/project-management/prds/wip`.
- **Outputs**: `missing` and `unresolved` rows become Blocking findings (fails as: wrong-TDD lock-in, or stall on a dangling citation); `unverified` rows become Non-blocking findings whose fix is the marker.
- **Behavior**: Lens D keeps its manual `rg` pass unchanged; the bullet adds, never replaces. If the script is absent the gate names the missing dependency in the recap instead of silently skipping.

## Structural Decomposition

### Repository Structure

```
skills/
├── create-prd/
│   ├── SKILL.md                    # Maps to: Authoring gate
│   └── scripts/
│       ├── ground_prd.py           # Maps to: Grounding checker
│       └── test_ground_prd.py      # Maps to: Grounding checker (contract tests, fixtures per failure class)
└── review-prd-backlog/
    └── SKILL.md                    # Maps to: Gate lens
CHANGELOG.md                        # one Added entry per skill scope
```

### Module: ground_prd.py

- **Maps to capability**: Grounding checker
- **Responsibility**: Extract claims from a PRD, verify them against the repo and installed package source, report and exit.
- **Exports**:
  - `extract_claims(text)` - claims with kind, token and line
  - `check_citations(claims, root)` - citation statuses
  - `resolve_symbols(claims, root, declared)` - symbol statuses via `rg`
  - `check_library_claims(claims, root, registry)` - library statuses
  - `run(paths, root, registry)` - rows plus blocking and unverified counts
  - `main()` - CLI (`--root`, `--cargo-registry`, `--json`, paths)
- New symbols: `ground_prd`, `extract_claims`, `check_citations`, `resolve_symbols`, `check_library_claims`, `test_ground_prd`

### Module: test_ground_prd.py

- **Maps to capability**: Grounding checker
- **Responsibility**: One fixture per failure class built under `tmp_path` (a fake repo with `.gitignore`, a `Cargo.lock`, a fake registry dir, a PRD); tests named for the rule they enforce.
- **Exports**: pytest cases listed under Test Strategy

### Module: create-prd SKILL.md

- **Maps to capability**: Authoring gate
- **Responsibility**: Step 5.55 text, the `New symbols:` rule in step 3, the script in Dependencies.
- **Exports**: `### 5.55. Grounding gate` heading

### Module: review-prd-backlog SKILL.md

- **Maps to capability**: Gate lens
- **Responsibility**: The step 1 grounding-resolution bullet and the Dependencies line naming the script.
- **Exports**: the `Grounding resolution` bullet

## Dependency Graph

### Foundation Layer (Phase 0)
No dependencies - built first.

- **ground_prd.py + test_ground_prd.py**: the checker and its contract tests.

### Core Layer (Phase 1)
- **create-prd SKILL.md**: Depends on [ground_prd.py]

### Integration Layer (Phase 2)
- **review-prd-backlog SKILL.md**: Depends on [ground_prd.py, create-prd SKILL.md]
- **CHANGELOG.md**: Depends on [create-prd SKILL.md, review-prd-backlog SKILL.md]

## Implementation Phases

### Phase 0: Foundation
**Goal**: A checker that reproduces the B18, B04 and stale-citation failure classes on fixtures.

**Tasks**:
- [ ] Write `skills/create-prd/scripts/ground_prd.py` with claim extraction, the citation lens, the symbol lens, `New symbols:` declarations and the `link-ok:` waiver, plus the matching tests (no deps) - Acceptance: `uv run pytest skills/create-prd/scripts/test_ground_prd.py -q -k "grounded or citation or symbol or declared or fenced or working_docs"` reports 0 failed; `test_a_symbol_present_only_under_working_docs_is_unresolved` plants the symbol only in `tmp_path/docs/dev/project-management/notes/x.md` and asserts `unresolved`.
- [ ] Add the library lens (`Cargo.lock` plus registry, node_modules, `.venv` site-packages), `--cargo-registry`, and the `(unverified library claim)` waiver, plus tests (no deps) - Acceptance: `uv run pytest skills/create-prd/scripts/test_ground_prd.py -q -k "library or marker"` reports 0 failed; the absent-API test asserts exit 0 with exactly one `unverified` row, the present-API test asserts `ok` against a fake `<registry>/idx/fake-1.0.0/src/lib.rs`, and `test_a_locked_crate_without_source_is_unverified_not_unresolved` plants `name = "fake"` in the fixture `Cargo.lock` with no registry directory, cites `fake::absent_fn`, and asserts exactly one `library`/`unverified` row, no `unresolved` row, exit 0.
- [ ] Add the CLI surface: table and `--json` output, sorted statuses, summary line, directory expansion, exit 2 on missing `rg` or unreadable input (no deps) - Acceptance: `uv run pytest skills/create-prd/scripts/test_ground_prd.py -q -k "cli or exits_two or directory"` reports 0 failed; the missing-rg test monkeypatches `shutil.which` to return `None` and asserts return code 2 with `rg` named on stderr.

**Exit Criteria**: `uv run pytest skills/create-prd/scripts/test_ground_prd.py -q` reports 0 failed and 0 errors.

### Phase 1: Core
**Goal**: The author runs the checker before every save.

**Tasks**:
- [ ] Insert `### 5.55. Grounding gate` between steps 5.5 and 5.6 of `skills/create-prd/SKILL.md` with the Step 5.55 Feature's Behavior as its body (command, four statuses, the three fixes, exit-2 rule, the one-sentence rationale, generic per the repository's public-prose rule: on a reviewed backlog, 12 of 24 Blocking findings were implementations that could not work; the project name stays in local evidence, never in SKILL.md), add the `New symbols:` rule as a new paragraph after the guess-marking paragraph in step 3, add `- Scripts: scripts/ground_prd.py (step 5.55; tests in scripts/test_ground_prd.py); CLI: rg` to Dependencies, and change step 5.5's hand-off ("proceed to step 5.6") to "proceed to step 5.55". Premise: `rg -n "^### 5\.5\. Guess-density gate|^### 5\.6\. Model-tier gate" skills/create-prd/SKILL.md` returns exactly two hits, 5.5 before 5.6 (line numbers are not pinned), and `rg -c "proceed to step 5\.6" skills/create-prd/SKILL.md` prints 1; re-check before editing and skip-and-report on a mismatch (depends on: Phase 0) - Acceptance: `rg -c "^### 5.55. Grounding gate" skills/create-prd/SKILL.md` prints 1; `rg -c "New symbols:" skills/create-prd/SKILL.md` prints at least 2 (one in step 3, one in step 5.55); `rg -c "proceed to step 5\.55" skills/create-prd/SKILL.md` prints 1; `uv run python3 skills/create-skill/scripts/validate_skill.py skills/create-prd` exits 0.

**Exit Criteria**: Step 5.5, 5.55 and 5.6 appear in that order in the file (`rg -n "^### 5\.5[5]?\. |^### 5\.6\. " skills/create-prd/SKILL.md` prints three ascending line numbers).

### Phase 2: Integration
**Goal**: The gate and the author run the same check.

**Tasks**:
- [ ] Add the `Grounding resolution` bullet from the Gate lens Feature directly after the `Citation resolution` bullet in step 1 of `skills/review-prd-backlog/SKILL.md`, and extend the Dependencies `Scripts:` line with `~/.agents/skills/create-prd/scripts/ground_prd.py` (owned by create-prd; absence is named in the recap). Premise: the `Citation resolution` bullet is at line 46 and the `Scripts:` line at line 23; re-check with `rg -n "Citation resolution|^- Scripts:" skills/review-prd-backlog/SKILL.md` and skip-and-report on a mismatch (depends on: Phase 1) - Acceptance: `rg -c "ground_prd.py" skills/review-prd-backlog/SKILL.md` prints 2; `rg -c "### D. Grounding" skills/review-prd-backlog/SKILL.md` still prints 1; `uv run python3 skills/create-skill/scripts/validate_skill.py skills/review-prd-backlog` exits 0.
- [ ] Add two Added entries to `CHANGELOG.md` under `[Unreleased]`: `**create-prd**: step 5.55 runs ground_prd.py ...` and `**review-prd-backlog**: step 1 runs the same grounding check ...`. Premise: `## [Unreleased]` sits at `CHANGELOG.md:8` with `### Added` at `:10`; re-check with `rg -n "^## \[Unreleased\]|^### Added" CHANGELOG.md` and skip-and-report if either is absent (depends on: Phase 1) - Acceptance: `rg -c "^- \*\*create-prd\*\*: step 5.55|^- \*\*review-prd-backlog\*\*: step 1" CHANGELOG.md` prints 2.

**Exit Criteria**: `uv run pytest skills/create-prd/scripts/test_ground_prd.py -q` reports 0 failed; both validator runs exit 0; the two CHANGELOG lines exist.

## Test Strategy

### Critical Scenarios
- **Happy path**: `test_a_grounded_prd_exits_zero_with_only_ok_rows` - a fixture PRD citing `src/lib.rs:2` beside the backticked symbol on that line, naming one repo symbol, one declared-new symbol and one installed-crate API → Expected: exit 0, statuses `ok`, `ok`, `declared-new`, `ok`. `test_a_library_api_in_installed_crate_source_is_ok` → Expected: `ok` from a fake registry crate directory.
- **Edge case**: `test_a_symbol_present_only_under_working_docs_is_unresolved` → Expected: `unresolved`, exit 1. `test_fenced_blocks_and_frontmatter_are_not_scanned` → Expected: no rows from those regions. `test_a_directory_argument_expands_to_its_markdown_files` → Expected: rows from every `*.md` in the directory. `test_the_unverified_marker_and_link_ok_waive_their_lines` → Expected: `waived` and no rows respectively, exit 0.
- **Error case**: `test_a_citation_to_a_missing_file_blocks`, `test_a_citation_past_end_of_file_blocks`, `test_a_cited_line_without_the_named_symbol_blocks`, `test_a_symbol_absent_from_the_repo_blocks_unless_declared_new` → Expected: exit 1 with one `missing` or `unresolved` row each. `test_a_library_api_absent_from_installed_source_warns_without_blocking` → Expected: one `unverified` row, exit 0. `test_a_locked_crate_without_source_is_unverified_not_unresolved` → Expected: one `library`/`unverified` row, exit 0. `test_a_missing_rg_exits_two` → Expected: return code 2. `test_cli_prints_table_json_and_exit_codes` → Expected: table order and JSON shape as specified.

## Risks

- **False blocks on prose in backticks**: the filter drops flags, paths, commands and short tokens; what remains is code by the author's own typography, and the fix is to un-backtick or declare. Lens D's manual pass stays for judgement.
- **False passes**: `rg -F -w` finds a segment in docs or prose, not code. Accepted; the lens catches absence, which is the measured failure class, and lens D re-checks by hand.
- **Fresh host without a registry or `rg`**: a missing registry yields `unverified` and never blocks; a missing `rg` exits 2 loudly rather than passing vacuously.
- **Cross-skill path**: the gate names the script through `~/.agents/skills/create-prd/scripts/`, the one path every host shares (`AGENTS.md:29`); an absent create-prd is reported, not silently skipped.
- **Loop self-harm**: this PRD edits the two skills that gate PRDs, not the loop that executes them, so no resequencing is required.
