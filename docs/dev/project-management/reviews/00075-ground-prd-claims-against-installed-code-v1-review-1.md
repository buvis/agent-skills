---
prd: docs/dev/project-management/prds/wip/00075-ground-prd-claims-against-installed-code-v1.md
review: 1
date: 2026-10-11
head_sha: f169c266afdf46086ec2694d26150a5cff40a094
codex_thread_id: 01a12b18-df87-7a52-9c82-027b08466904
reviewers: alice,blake,bob
agents:
  alice: available
  blake: available
  bob: available
  carl: unavailable
dispatch_rows:
  bob: 993f9f5c
  carl: 9c88e555
---

# Review: 00075-ground-prd-claims-against-installed-code-v1

Diff range: `4acb735783e74f509f9c562e98816b11b96bbdf4..f169c266afdf46086ec2694d26150a5cff40a094`

codex_rung_guard: not fired

pack: failed (engram pack exit 1: not inside a registered repo; run `gita add /Users/bob/git/src/github.com/buvis/agent-skills`)

Mechanical checks: 0 `[MECH]` findings (65 test functions checked in 2 test files; replay: 0 touched tests ran, 2 test files could not be collected at base).

## Review Summary

Reviewed: 6 completed tasks
PRDs checked: 00075-ground-prd-claims-against-installed-code-v1

### Agent Status

- Alice: ✅ Available
- Blake: ✅ Available
- Bob: ✅ Available (first run was a lack-of-input refusal — the codex sandbox could not read the staged files; re-dispatched as the inlined retry per retry-policy.md, `after one retry (inlined)`)
- Carl: ⚠️ Unavailable: gemini-run.sh exit 1 on both the first dispatch and the retry — `backend=copilot model=gemini-3.8-flash`, "No authentication information found." Not exit 4, so not latched for the batch.

## Consolidated Findings

24 findings. No 🔴 Critical. Three 🟠 High (one at full 3/3 consensus).

| Ref | Consensus | Severity | Issue | File | Task | Found By |
|-----|-----------|----------|-------|------|------|----------|
| R1 | [3/3] | 🟠 | An `rg` failure (exit 2) raises an uncaught `RuntimeError`, and `main()` has no handler. Python then exits 1 with a traceback, and the create-prd gate and the backlog gate read exit 1 as "blocking findings". The design says to catch it in `main()` and exit 2 with the `rg` stderr. A nonexistent `--root` has the same problem: `subprocess.run(cwd=root)` raises. No test covers the exit-2 path for `rg` failures. | skills/create-prd/scripts/ground_prd.py:145 | 3 | ALICE, BLAKE, BOB |
| R2 | [2/3] | 🟠 | The spec requires `rg` lookups cached per segment and root with `functools.cache`. `resolve_symbols` spawns one `rg` per segment per claim with no cache, and `check_library_claims` does the same. The backlog gate runs over `backlog/` and `wip/` with many repeated tokens, so cost grows with total claims instead of unique segments. Fix: memoize a helper on `(segment, root, exclude)`. | skills/create-prd/scripts/ground_prd.py:139 | 1 | ALICE, BLAKE |
| R3 | [2/3] | 🟡 | The PRD success metric "every scenario in Test Strategy is a named test in that file" is not met. These PRD-named tests do not exist: `test_a_grounded_prd_exits_zero_with_only_ok_rows`, `test_a_library_api_in_installed_crate_source_is_ok`, `test_the_unverified_marker_and_link_ok_waive_their_lines`, `test_a_citation_to_a_missing_file_blocks`, `test_a_citation_past_end_of_file_blocks`, `test_a_cited_line_without_the_named_symbol_blocks`, `test_a_symbol_absent_from_the_repo_blocks_unless_declared_new`, `test_a_library_api_absent_from_installed_source_warns_without_blocking`, `test_a_missing_rg_exits_two`, `test_cli_prints_table_json_and_exit_codes`. Unit-level equivalents cover most scenarios. The B18-shaped and B04-shaped fixtures are never run through `main()` as end-to-end exit-code cases. | skills/create-prd/scripts/test_ground_prd.py:567 | 3 | ALICE, BLAKE |
| R4 | [2/3] | 🟡 | `main` is 56 lines, over the 50-line limit (mechanical facts). `SORT_ORDER` is a constant defined inside the function. Extract `render_table(result)` and move `SORT_ORDER` to module level. | skills/create-prd/scripts/ground_prd.py:281 | 3 | ALICE, BOB |
| R5 | [2/3] | 🟡 | The step 5.55 text lacks the PRD-specified "four statuses" explanation: `ok`, `declared-new` and `waived` rows are never described. It also omits the instruction to write a conversation-only draft to `docs/dev/tmp/` first. The prose uses " -- " in place of a regular dash. | skills/create-prd/SKILL.md:808 | 4 | ALICE, BLAKE |
| R6 | [1/3] | 🟠 | Declarations inside fenced examples, frontmatter, and `link-ok:` lines still enter `declared`, allowing an absent symbol elsewhere to pass as `declared-new`. Apply extraction's preprocessing to declaration collection; add regression tests for all three regions. | skills/create-prd/scripts/ground_prd.py:254 | 3 | BOB |
| R7 | [1/3] | 🟡 | `resolve_symbols` has an unspecified `exclude` parameter (it drops the PRD files being graded from the `rg` search so a claim cannot confirm itself). No test covers it. It also has an untested `ValueError` skip for PRDs outside `root`. Add a test where the symbol appears only in the PRD file itself and assert `unresolved`. | skills/create-prd/scripts/ground_prd.py:119 | 1 | ALICE |
| R8 | [1/3] | 🟡 | The row `detail` is always `f"{kind} {token}"`, which duplicates the kind and token columns. The spec examples show diagnostic text ("file not found", "line 42 exceeds 30 lines", "source not installed"). The author cannot tell from a `missing` citation whether the file is absent, the range is past the end, or the symbol is not in the range. Have the check functions return a reason string, or derive it in `_rows_for_file`. | skills/create-prd/scripts/ground_prd.py:230 | 3 | ALICE |
| R9 | [1/3] | 🟡 | `known_packages` registers every `Cargo.lock` `[[package]]`, including the repo's own workspace and path crates, which have no registry source. A PRD symbol such as `mycrate::fetch_report` then becomes a `library` claim. Its source is `None`, so the status is `unverified`, which is non-blocking. It never reaches the repo `rg` check. That is the B18 class (producers that do not exist in repo code), and it is demoted from Blocking to a warning. Consider skipping lock blocks without a `source =` line, or falling back to the repo `rg` check when the registry source is absent. | skills/create-prd/scripts/ground_prd.py:155 | 2 | ALICE |
| R10 | [1/3] | 🟡 | The diff includes unrelated work outside PRD 00075: `skills/glean/SKILL.md`, `skills/glean/scripts/glean.py`, `skills/glean/scripts/test_glean.py`, and the `**glean**` CHANGELOG entry (`git log` shows glean landed in separate commits b389276 and c161810). None of the six tasks cover it. Confirm it belongs to another PRD and exclude it from this PRD's review. | CHANGELOG.md:12 | general | ALICE |
| R11 | [1/3] | 🟡 | The JSON row shape drifts from the spec. The spec says "same fields per row" as `status \| kind \| token \| prd:line \| detail`. Rows carry `file` and `line` separately, plus `detail`, and no `prd:line` field. The gate lens must reassemble `file:line` itself | skills/create-prd/scripts/ground_prd.py:237 | 3 | BLAKE |
| R12 | [1/3] | 🟡 | The table output is not the specified column layout. It prints space-padded columns with no separators. The `detail` column is only `"<kind> <token>"` repeated, so it never says why a row is `missing` (file absent, line out of range, or symbol not in the cited range). That reason is the main thing an author needs to fix the row | skills/create-prd/scripts/ground_prd.py:332 | 3 | BLAKE |
| R13 | [1/3] | 🟡 | Cargo parsing requires adjacent name/version lines and ignores package boundaries, violating the specified within-three-lines contract. Parse each `[[package]]` block independently and test intervening lines and adjacent blocks. | skills/create-prd/scripts/ground_prd.py:37 | 2 | BOB |
| R14 | [1/3] | 🟡 | Symbol searches are never cached, despite the explicit requirement; repeated claims launch repeated repo scans. Add a cached segment-search helper keyed by root, segment, and exclusions, with a repeated-segment test. | skills/create-prd/scripts/ground_prd.py:143 | 1 | BOB |
| R15 | [1/3] | 🟡 | CLI root and registry paths are neither expanded nor resolved. A quoted `--cargo-registry '~/…'` therefore misses installed source. Normalize both paths with `expanduser().resolve()` and test quoted home-relative arguments. | skills/create-prd/scripts/ground_prd.py:293 | 3 | BOB |
| R16 | [1/3] | 🟡 | Citation extraction silently omits numeric-leading extensions such as `manual.1:7`, although the contract permits `\w+` extensions. Restore that grammar and add a numeric-extension extraction test. | skills/create-prd/scripts/ground_prd.py:39 | 1 | BOB |
| R17 | [1/3] | 🟡 | Package discovery scans every Python environment and takes an unsorted Cargo match, contrary to the specified first Python match and sorted Cargo selection. Implement deterministic selection and test multiple matching directories. | skills/create-prd/scripts/ground_prd.py:153 | 2 | BOB |
| R18 | [1/3] | 🟡 | Citation claims are unchanged during reclassification, so pairing original and reclassified lists adds unnecessary bookkeeping. Iterate over `reclassified` directly and use `citation_result[rc]`. | skills/create-prd/scripts/ground_prd.py:228 | 3 | BOB |
| R19 | [1/3] | ⚪ | `check_library_claims(..., line_text=None)` silently disables the `(unverified library claim)` waiver when the argument is omitted. A direct caller gets `unverified` instead of `waived`, and a test pins that behavior. Make `line_text` required, since `run()` is the only caller. | skills/create-prd/scripts/ground_prd.py:175 | 2 | ALICE |
| R20 | [1/3] | ⚪ | `main()` does not resolve `root` to an absolute path (Data flow step 1), and `--cargo-registry ~/x` is not `expanduser`'d, so a quoted tilde is taken literally. | skills/create-prd/scripts/ground_prd.py:293 | 3 | ALICE |
| R21 | [1/3] | ⚪ | The checker goes beyond the spec in small ways. The placeholder filter adds `XXXX\|YYYY`. `resolve_symbols` takes an extra `exclude` argument and excludes the PRD files being graded. Crate names are aliased with underscores. All are defensible, but none is specified, and the PRD-exclusion changes semantics. A symbol that appears only in the PRD under review is `unresolved` here | skills/create-prd/scripts/ground_prd.py:45 | 1 | BLAKE |
| R22 | [1/3] | ⚪ | Citation detection can false-block on non-path tokens that look like `name.ext:digits`, for example `example.com:443`, because the file is then looked up and reported `missing`. The same line check uses substring matching on the symbol's last segment, not a word match, so it passes more easily than the symbol lens does | skills/create-prd/scripts/ground_prd.py:38 | 1 | BLAKE |
| R23 | [1/3] | ⚪ | Frontmatter handling treats any first-line `---` without a closing `---` as frontmatter, so the whole file is silently skipped and no claims are checked (fail-open). Fences only toggle on triple backticks, so `~~~` fences are scanned | skills/create-prd/scripts/ground_prd.py:67 | 1 | BLAKE |
| R24 | [1/3] | ⚪ | Package classification treats any `node_modules` directory or site-packages module name as a library root. A repo symbol whose first segment shares such a name (for example `config.load`) is downgraded to a non-blocking `unverified` and never checked against the repo. This follows the spec design but is a fail-open path | skills/create-prd/scripts/ground_prd.py:217 | 2 | BLAKE |

Consolidation note: `consolidate_findings.py` parses only lines anchored at `[AGENT]`. Bob's persona emits his issue lines as `- [BOB] …` bullets inside the FIX bucket, so the first consolidation run silently dropped all nine of them. The bullet prefixes were stripped from `bob-output-202610111300.txt` and the script re-run; the table above is the script's output with Bob parsed. This is a tooling gap in the consolidator, not a reviewer failure.

## Alice

Consensus lens, implementation-aware. 11 findings (1 🟠, 7 🟡, 3 ⚪) — rows R1, R3, R4, R5, R7, R8, R9, R10, R19, R20 above. Verified `uv run pytest skills/create-prd/scripts/test_ground_prd.py -q`: 48 passed. Also ran the checker on the PRD itself: exit 1 with 14 blocking rows, of which two are expected artefacts (a shifted `skills/create-prd/SKILL.md` line reference and the `src/lib.rs:2` fixture example) and the rest are the missing Test-Strategy test names in R3.

```
R1: fail
R2: pass
R3: pass
R4: pass
R6: pass
R7: pass
R8: pass
R9: fail
R10: fail
R11: pass
R12: fail
R13: pass
```

## Blake

Blind lens, PRD-only (no diff, no file list, no history). 10 findings (2 🟠, 4 🟡, 4 ⚪) — rows R1, R2, R3, R5, R11, R12, R21, R22, R23, R24 above. Verified: `uv run pytest skills/create-prd/scripts/test_ground_prd.py -q` 48 passed; both SKILL.md edits match their acceptance greps; CHANGELOG carries both Added entries.

```
B1: fail
B2: fail
B3: pass
B4: pass
B5: fail
B6: pass
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

Doubt lens + de-slop (codex), `after one retry (inlined)`. 9 findings (2 🟠, 7 🟡) — rows R1, R4, R6, R13, R14, R15, R16, R17, R18 above.

FIX: 9 items (the rows above). VERIFY: (none). KNOWN: (none).

```
R1: fail
R2: pass
R3: pass
R4: pass
R6: pass
R7: pass
R8: pass
R9: fail
R10: fail
R11: pass
R12: fail
R13: pass
D1: pass
D2: pass
D3: pass
D4: pass
D5: pass
```

## Carl

⚠️ Unavailable: `gemini-run.sh` exit 1, `backend=copilot model=gemini-3.8-flash`, "No authentication information found." Retried once unchanged, same failure. No `ui` lens output this cycle.

Verdict: 24 findings
Tests: 3782 passed, 0 failed, 6 skipped (suite run this cycle)
