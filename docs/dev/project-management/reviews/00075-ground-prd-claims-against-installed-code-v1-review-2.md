---
prd: docs/dev/project-management/prds/wip/00075-ground-prd-claims-against-installed-code-v1.md
review: 2
date: 2026-10-11
head_sha: 2ad5280f0935c817306b89fa0170c7963e2c62ce
codex_thread_id: 01a12b45-db22-7e30-9bd6-f3422fa6896b
reviewers: alice,blake,bob
agents:
  alice: available
  blake: available
  bob: available
  carl: unavailable
dispatch_rows:
  bob: ee52e636
  bob_retry: d8fc26af
  carl: 35b927ce
---

# Review: 00075-ground-prd-claims-against-installed-code-v1 (cycle 2, incremental)

Diff range: `f169c266afdf46086ec2694d26150a5cff40a094..2ad5280f0935c817306b89fa0170c7963e2c62ce`

codex_rung_guard: not fired

pack: failed (engram pack exit 1: not inside a registered repo; run `gita add /Users/bob/git/src/github.com/buvis/agent-skills`)

Mechanical checks: 1 `[MECH]` finding (65 test functions checked in 1 test file, 0 tautological shapes; replay: 17 touched tests ran, 7 failed against base, 10 passed). The passing-against-base line is folded into R11, which names the same file and tests.

## Review Summary

Reviewed: 9 completed tasks (incremental: the cycle-1 rework, tasks 7-9)
PRDs checked: 00075-ground-prd-claims-against-installed-code-v1

### Agent Status

- Alice: ✅ Available
- Blake: ✅ Available
- Bob: ✅ Available (first run was a lack-of-input refusal — the codex sandbox could not read the staged files; re-dispatched as the inlined retry per retry-policy.md, `after one retry (inlined)`)
- Carl: ⚠️ Unavailable: `gemini-run.sh` exit 1 on both the first dispatch and the retry — `backend=copilot model=gemini-3.8-flash`, "No authentication information found." Not exit 4, so not latched for the batch.

## Consolidated Findings

14 findings. No 🔴 Critical. Two 🟠 High (R1 at full 3/3 consensus).

| Ref | Consensus | Severity | Issue | File | Task | Found By |
|-----|-----------|----------|-------|------|------|----------|
| R1 | [3/3] | 🟠 | R1 only half fixed. `main()` now catches `RuntimeError` and exits 2, but a nonexistent `--root` still raises an uncaught `FileNotFoundError` from `subprocess.run(cwd=root)`. A traceback follows and the gates read exit 1 ("blocking"). The cycle-1 finding named this case explicitly. Fix: validate `root.is_dir()` in `main()` next to the unreadable-input check and exit 2 with a stderr message, or catch `OSError` alongside `RuntimeError`. Add a test. Blake adds the same class for `Cargo.lock`'s unguarded `read_text` in `known_packages`. | skills/create-prd/scripts/ground_prd.py:377 | 7 | ALICE, BLAKE, BOB |
| R2 | [1/3] | 🟠 | Relative PRD exclusions now resolve against `root` instead of the process cwd. With cwd `/work`, `--root repo`, and input `repo/prd.md`, the exclusion targets `/work/repo/repo/prd.md`; the real PRD can confirm its own invented symbols. Resolve input paths against the original cwd. Replace the regression fixture with a CLI call using these differing paths. | skills/create-prd/scripts/ground_prd.py:157 | 7 | BOB |
| R3 | [1/3] | 🟡 | R6 only half tested. `_scannable_lines` now feeds the `declared` scan, so frontmatter and `link-ok:` lines are skipped as well as fences. Only the fenced region has a regression test (`test_new_symbols_line_inside_fence_does_not_declare_the_symbol`). The finding asked for tests on all three regions. Add one for a `New symbols:` line inside frontmatter and one for a line carrying `link-ok:`. | skills/create-prd/scripts/test_ground_prd.py:695 | 9 | ALICE |
| R4 | [1/3] | 🟡 | Tautological PRD-named test. `test_a_cited_line_without_the_named_symbol_blocks` cites a symbol that is itself `unresolved` in the repo, so exit 1 comes from the symbol lens whether or not the citation lens works. The test cannot fail if `check_citations` is broken. Fix: use a symbol that exists in the repo but not on the cited line, and assert the single row is a `missing` citation. | skills/create-prd/scripts/test_ground_prd.py:832 | 9 | ALICE |
| R5 | [1/3] | 🟡 | Tautological PRD-named tests. `test_a_library_api_in_installed_crate_source_is_ok` and `test_the_unverified_marker_and_link_ok_waive_their_lines` assert only exit 0. `unverified` rows exit 0 as well, so neither test can tell `ok` from `unverified` or `waived` from `unverified`. Fix: parse `--json` and assert the row status, and that no `link-ok:` line produced a row. | skills/create-prd/scripts/test_ground_prd.py:792 | 9 | ALICE |
| R6 | [1/3] | 🟡 | Weak PRD-named tests. `test_a_grounded_prd_exits_zero_with_only_ok_rows` has no citation, no `declared-new` symbol and no library claim, so it does not match the Happy-path scenario in the PRD. `test_cli_prints_table_json_and_exit_codes` checks substrings and never asserts the table sort order or the JSON row fields the scenario calls for. | skills/create-prd/scripts/test_ground_prd.py:782 | 9 | ALICE |
| R7 | [1/3] | 🟡 | Simplification (behavior-preserving) in `check_citations`/`_rows_for_file`. The `reasons: dict \| None = None` parameter forces four `if reasons is not None:` guards, and `_rows_for_file` re-guards with a 100+ character conditional. `reasons` is only populated for `missing`, so `detail = citation_reasons.get(orig, f"citation {rc.token}")` is equivalent. Also, the `OSError` branch reports "not found" for an unreadable file, which is misleading. | skills/create-prd/scripts/ground_prd.py:271 | 7 | ALICE |
| R8 | [1/3] | 🟡 | Locked crates without a `source =` line (path or workspace-local) are dropped from `known_packages`. The spec says known packages are "every `name = "<crate>"` in `<root>/Cargo.lock`". The deviation is defensible and a test pins it, but it contradicts the spec's package-identity rule. | skills/create-prd/scripts/ground_prd.py:189 | 2 | BLAKE |
| R9 | [1/3] | 🟡 | Two Test Strategy scenarios lack the exact test names the Success Metrics require. `test_fenced_blocks_and_frontmatter_are_not_scanned` and `test_a_directory_argument_expands_to_its_markdown_files` do not exist; near-equivalents cover the behavior. The contract is a literal name match. | skills/create-prd/scripts/test_ground_prd.py:109 | 1 | BLAKE |
| R10 | [1/3] | 🟡 | Both search helpers retain `--no-messages` and discard subprocess stderr, so exit-2 handling reports only a generic failure instead of the underlying diagnostic. Capture stderr, enable diagnostics, and assert the error text reaches CLI stderr; the current test only checks that stderr is nonempty. | skills/create-prd/scripts/ground_prd.py:141 | 7 | BOB |
| R11 | [2/3] | 🟡 | Added acceptance tests do not fully enforce their named scenarios: the installed-library test accepts `unverified` because it checks only exit 0; the citation-symbol mismatch test can pass from the independently unresolved symbol; the happy-path fixture omits citations, declarations, and libraries. The computed fail-first replay confirms 10 of the touched tests pass against the pre-change code. | skills/create-prd/scripts/test_ground_prd.py:852 | 9 | BOB, mech-check |
| R12 | [1/3] | 🟡 | The test file now exceeds the 800-line limit: the mechanical facts place its final test at line 941. Split supporting fixtures and lower-level tests into focused modules while retaining the PRD-required named scenarios in `test_ground_prd.py`. | skills/create-prd/scripts/test_ground_prd.py:941 | 9 | BOB |
| R13 | [1/3] | ⚪ | Redundant assertion. `assert "workspace_crate" not in packages.values()` can never fail, since the values are dicts. The `not in packages` line above it already covers the check. | skills/create-prd/scripts/test_ground_prd.py:759 | 9 | ALICE |
| R14 | [1/3] | ⚪ | Duplicate identical claims on one line each produce a row and each increment `blocking`, so the counts are inflated. Also, `check_citations` counts declared-new and library symbols as "names on the citing line", so a citation beside a not-yet-existing symbol would be marked `missing`. | skills/create-prd/scripts/ground_prd.py:94 | 1 | BLAKE |

### Auto-dismissed (ledger)

- [BLAKE] 🟡 Several behaviors go beyond the spec (crate-name underscore aliasing, the `XXXX|YYYY` placeholder filter, the `isidentifier()` site-packages check, the PRD-exclusion `--glob`). | File: skills/create-prd/scripts/ground_prd.py:195 — scope-overflow: the exclude argument is covered by R7's test; the rest are defensible extensions
- [BLAKE] 🟡 Table output is space-padded columns rather than a `status | kind | token | prd:line | detail` layout. | File: skills/create-prd/scripts/ground_prd.py:334 — scope-overflow: cycle 1 raised 24 findings; top 10 by severity routed to rework. The `detail` half is covered by R8, which was fixed.

Consolidation note: run with `--ledger --ledger-dismiss BLAKE`. Row 1 merged four citations that matched only after suffix stripping (`ground_prd.py:377 ~ :143 ~ :187 ~ :379`) — the three uncaught-`OSError` reports plus Blake's `Cargo.lock` `read_text` variant, which is the same class.

## Alice

Consensus lens, implementation-aware, incremental against the 10 routed cycle-1 findings. Confirmed resolved: R2 (rg caching, with a failing-on-old-code test), R4 (`render_table` extracted, `SORT_ORDER` at module level, `main` now 50 lines), R5 (SKILL.md statuses and the `docs/dev/tmp/` draft instruction, " -- " gone), R7 (relative-path exclude test), R8 (citation `detail` reasons), R9 (sourceless lock blocks dropped), R11 (`prd:line` per row). 7 findings remain (rows R1, R3, R4, R5, R6, R7, R13 above). Verified `uv run pytest skills/create-prd/scripts/test_ground_prd.py -q`: 65 passed; `validate_skill.py skills/create-prd` OK. No regression shown from the `exclude` change on her probe.

```
R1: fail
R2: fail
R3: pass
R4: pass
R6: pass
R7: pass
R8: pass
R9: pass
R10: fail
R11: pass
R12: pass
R13: pass
```

## Blake

Blind lens, PRD-only (no diff, no file list, no history). 7 findings, 2 auto-dismissed against the ledger; rows R1, R8, R9, R14 above. Verified: 65 tests pass; both `validate_skill.py` runs exit 0; the SKILL.md step 5.5/5.55/5.6 ordering, the `New symbols:` rule, both `review-prd-backlog` edits and both CHANGELOG entries are in place; sort order, JSON shape, `unverified` exit 0, missing-`rg` exit 2, and the fence/frontmatter/`link-ok:`/`docs/dev` skips are implemented as specified.

```
B1: fail
B2: pass
B3: pass
B4: pass
B5: fail
B6: fail
B7: pass
B8: pass
B9: pass
B10: pass
B11: pass
B12: pass
B13: pass
B14: pass
B15: pass
B16: pass
B17: pass
B18: pass
B19: pass
```

## Bob

Doubt lens + de-slop (codex), `after one retry (inlined)`. 5 findings (2 🟠, 3 🟡) — rows R1, R2, R10, R11, R12 above.

FIX: 5 items (the rows above). VERIFY: (none). KNOWN: (none).

```
R1: fail
R2: fail
R3: pass
R4: fail
R6: pass
R7: pass
R8: pass
R9: fail
R10: fail
R11: pass
R12: pass
R13: fail
D1: pass
D2: pass
D3: pass
D4: pass
D5: pass
```

## Carl

⚠️ Unavailable: `gemini-run.sh` exit 1, `backend=copilot model=gemini-3.8-flash`, "No authentication information found." Retried once unchanged, same failure. No `ui` lens output this cycle.

Verdict: 14 findings
Tests: 3799 passed, 0 failed, 6 skipped (suite run this cycle)
