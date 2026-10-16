# Decision Audit Log: 00075-ground-prd-claims-against-installed-code-v1

PRD: `00075-ground-prd-claims-against-installed-code-v1.md`
Started: 2026-10-16T19:22:33Z
Completed: 2026-10-16T19:22:33Z
Autonomous: 26  |  Deferred: 15  |  Doubts: 0

### [autonomous] 2026-10-16T19:22:33Z

**Decision**: ground_prd.py design choices

**Choice**: rg-backed stdlib checker reusing check_links.py patterns; reviewed 3 dispatches (claude, claude-fallback, claude-fallback), fixed Cargo glob resolution, WAIVER citation, symbol/library reclassification timing, declared-new backtick stripping

**Rationale**: codex sandbox-broken both dispatches, degraded to Claude fallback each time; accepted 2 limitations (duplicate crate versions, scoped npm/site-packages metadata dirs) as PRD-inherited, deferred bare-citation-continuation support as a future change

### [autonomous] 2026-10-16T19:22:33Z

**Decision**: check_library_claims's PRD/design-pinned signature check_library_claims(claims, root, registry) has no way to reach the citing line's text, yet the Behavior bullet requires it to return "waived" when that line holds "(unverified library claim)"; Claim itself is pinned to (kind, token, line) with no text field

**Choice**: extended check_library_claims with an optional 4th keyword parameter line_text: dict[int, str] | None = None (default None means never waived), preserving the pinned 3-positional-arg call shape for existing/future callers; run() (task 3) will build and pass the per-line text dict

**Rationale**: Tess (test author) flagged this as a genuine contract gap per rule 10a (never invent a contract) rather than guessing a mechanism; resolving it required a design call the PRD/design doc did not pin, so the orchestrator picked the least invasive option (additive optional kwarg) over changing Claim's arity (would break task 1's already-committed 3-arg Claim constructor) or moving the waiver check into run() only (would contradict check_library_claims's own stated "waived" return value)

### [autonomous] 2026-10-16T19:22:33Z

**Decision**: An `rg` failure (exit 2) raises an uncaught `RuntimeError`, and `main()` has no handler. Python then exits 1 with a traceback, and the create-prd gate and the backlog gate read exit 1 as "blocking findings". The design says to catch it in `main()` and exit 2 with the `rg` stderr. A nonexistent `--root` has the same problem: `subprocess.run(cwd=root)` raises. No test covers the exit-2 path for `rg` failures.

**Choice**: auto-fixed

**Rationale**: fixed by review-close

### [autonomous] 2026-10-16T19:22:33Z

**Decision**: The spec requires `rg` lookups cached per segment and root with `functools.cache`. `resolve_symbols` spawns one `rg` per segment per claim with no cache, and `check_library_claims` does the same. The backlog gate runs over `backlog/` and `wip/` with many repeated tokens, so cost grows with total claims instead of unique segments. Fix: memoize a helper on `(segment, root, exclude)`.

**Choice**: auto-fixed

**Rationale**: fixed by review-close

### [autonomous] 2026-10-16T19:22:33Z

**Decision**: Declarations inside fenced examples, frontmatter, and `link-ok:` lines still enter `declared`, allowing an absent symbol elsewhere to pass as `declared-new`. Apply extraction's preprocessing to declaration collection; add regression tests for all three regions.

**Choice**: auto-fixed

**Rationale**: fixed by review-close

### [autonomous] 2026-10-16T19:22:33Z

**Decision**: The PRD success metric "every scenario in Test Strategy is a named test in that file" is not met. These PRD-named tests do not exist: `test_a_grounded_prd_exits_zero_with_only_ok_rows`, `test_a_library_api_in_installed_crate_source_is_ok`, `test_the_unverified_marker_and_link_ok_waive_their_lines`, `test_a_citation_to_a_missing_file_blocks`, `test_a_citation_past_end_of_file_blocks`, `test_a_cited_line_without_the_named_symbol_blocks`, `test_a_symbol_absent_from_the_repo_blocks_unless_declared_new`, `test_a_library_api_absent_from_installed_source_warns_without_blocking`, `test_a_missing_rg_exits_two`, `test_cli_prints_table_json_and_exit_codes`. Unit-level equivalents cover most scenarios. The B18-shaped and B04-shaped fixtures are never run through `main()` as end-to-end exit-code cases.

**Choice**: auto-fixed

**Rationale**: fixed by review-close

### [autonomous] 2026-10-16T19:22:33Z

**Decision**: `main` is 56 lines, over the 50-line limit (mechanical facts). `SORT_ORDER` is a constant defined inside the function. Extract `render_table(result)` and move `SORT_ORDER` to module level.

**Choice**: auto-fixed

**Rationale**: fixed by review-close

### [autonomous] 2026-10-16T19:22:33Z

**Decision**: The step 5.55 text lacks the PRD-specified "four statuses" explanation: `ok`, `declared-new` and `waived` rows are never described. It also omits the instruction to write a conversation-only draft to `docs/dev/tmp/` first. The prose uses " -- " in place of a regular dash.

**Choice**: auto-fixed

**Rationale**: fixed by review-close

### [autonomous] 2026-10-16T19:22:33Z

**Decision**: `resolve_symbols` has an unspecified `exclude` parameter (it drops the PRD files being graded from the `rg` search so a claim cannot confirm itself). No test covers it. It also has an untested `ValueError` skip for PRDs outside `root`. Add a test where the symbol appears only in the PRD file itself and assert `unresolved`.

**Choice**: auto-fixed

**Rationale**: fixed by review-close

### [autonomous] 2026-10-16T19:22:33Z

**Decision**: The row `detail` is always `f"{kind} {token}"`, which duplicates the kind and token columns. The spec examples show diagnostic text ("file not found", "line 42 exceeds 30 lines", "source not installed"). The author cannot tell from a `missing` citation whether the file is absent, the range is past the end, or the symbol is not in the range. Have the check functions return a reason string, or derive it in `_rows_for_file`.

**Choice**: auto-fixed

**Rationale**: fixed by review-close

### [autonomous] 2026-10-16T19:22:33Z

**Decision**: `known_packages` registers every `Cargo.lock` `[[package]]`, including the repo's own workspace and path crates, which have no registry source. A PRD symbol such as `mycrate::fetch_report` then becomes a `library` claim. Its source is `None`, so the status is `unverified`, which is non-blocking. It never reaches the repo `rg` check. That is the B18 class (producers that do not exist in repo code), and it is demoted from Blocking to a warning. Consider skipping lock blocks without a `source =` line, or falling back to the repo `rg` check when the registry source is absent.

**Choice**: auto-fixed

**Rationale**: fixed by review-close

### [autonomous] 2026-10-16T19:22:33Z

**Decision**: The JSON row shape drifts from the spec. The spec says "same fields per row" as `status | kind | token | prd:line | detail`. Rows carry `file` and `line` separately, plus `detail`, and no `prd:line` field. The gate lens must reassemble `file:line` itself

**Choice**: auto-fixed

**Rationale**: fixed by review-close

### [autonomous] 2026-10-16T19:22:33Z

**Decision**: [R1] uncaught RuntimeError from rg failure exits 1 with a traceback instead of exit 2

**Choice**: auto-fix (routed to cycle-1 rework task)

**Rationale**: mechanical or additive fix with a clear contract from the PRD and design doc; no new dependency, no public-API or data-model change

### [autonomous] 2026-10-16T19:22:33Z

**Decision**: [R2] rg lookups are not cached per segment/root as the design requires

**Choice**: auto-fix (routed to cycle-1 rework task)

**Rationale**: mechanical or additive fix with a clear contract from the PRD and design doc; no new dependency, no public-API or data-model change

### [autonomous] 2026-10-16T19:22:33Z

**Decision**: [R6] declarations inside fences/frontmatter/link-ok lines still enter the declared set

**Choice**: auto-fix (routed to cycle-1 rework task)

**Rationale**: mechanical or additive fix with a clear contract from the PRD and design doc; no new dependency, no public-API or data-model change

### [autonomous] 2026-10-16T19:22:33Z

**Decision**: [R3] Test Strategy scenarios are not named tests; no end-to-end CLI exit-code cases

**Choice**: auto-fix (routed to cycle-1 rework task)

**Rationale**: mechanical or additive fix with a clear contract from the PRD and design doc; no new dependency, no public-API or data-model change

### [autonomous] 2026-10-16T19:22:33Z

**Decision**: [R4] main() is 56 lines, over the 50-line limit; SORT_ORDER defined inside it

**Choice**: auto-fix (routed to cycle-1 rework task)

**Rationale**: mechanical or additive fix with a clear contract from the PRD and design doc; no new dependency, no public-API or data-model change

### [autonomous] 2026-10-16T19:22:33Z

**Decision**: [R5] step 5.55 omits the four-status explanation and the docs/dev/tmp draft guidance

**Choice**: auto-fix (routed to cycle-1 rework task)

**Rationale**: mechanical or additive fix with a clear contract from the PRD and design doc; no new dependency, no public-API or data-model change

### [autonomous] 2026-10-16T19:22:33Z

**Decision**: [R7] resolve_symbols' exclude parameter and its ValueError skip are untested

**Choice**: auto-fix (routed to cycle-1 rework task)

**Rationale**: mechanical or additive fix with a clear contract from the PRD and design doc; no new dependency, no public-API or data-model change

### [autonomous] 2026-10-16T19:22:33Z

**Decision**: [R8] row detail duplicates kind and token instead of naming the failure reason

**Choice**: auto-fix (routed to cycle-1 rework task)

**Rationale**: mechanical or additive fix with a clear contract from the PRD and design doc; no new dependency, no public-API or data-model change

### [autonomous] 2026-10-16T19:22:33Z

**Decision**: [R9] known_packages registers path/workspace crates, demoting a B18-class symbol to unverified

**Choice**: auto-fix (routed to cycle-1 rework task)

**Rationale**: mechanical or additive fix with a clear contract from the PRD and design doc; no new dependency, no public-API or data-model change

### [autonomous] 2026-10-16T19:22:33Z

**Decision**: [R11] JSON row shape drifts from the specified status|kind|token|prd:line|detail fields

**Choice**: auto-fix (routed to cycle-1 rework task)

**Rationale**: mechanical or additive fix with a clear contract from the PRD and design doc; no new dependency, no public-API or data-model change

### [autonomous] 2026-10-16T19:22:33Z

**Decision**: Review cycle 1 produced 24 consolidated findings, over the 10-follow-up scope limit

**Choice**: kept the top 10 by severity for rework; deferred the remaining 14 to batch end as scope-overflow records

**Rationale**: loop-mode Safety Checks rule for >10 follow-up tasks: defer the tail rather than pause the batch

### [autonomous] 2026-10-16T19:22:33Z

**Decision**: Carl (gemini) failed twice with 'No authentication information found' (gemini-run.sh exit 1, backend=copilot)

**Choice**: continued with Alice, Blake and Bob; Carl recorded unavailable for this cycle and not latched for the batch

**Rationale**: exit 1 is a one-off runtime failure, not the exit-4 permanent-unavailability latch; graceful degradation keeps the cycle valid

### [autonomous] 2026-10-16T19:22:33Z

**Decision**: Bob's first codex run returned a lack-of-input refusal (sandbox_apply: Operation not permitted)

**Choice**: re-dispatched Bob once with the inlined retry prompt (context + full diff inlined); the retry produced 9 findings and all five D verdicts

**Rationale**: retry-policy.md lack-of-input refusal path; the doubt lens must not silently drop

### [autonomous] 2026-10-16T19:22:33Z

**Decision**: consolidate_findings.py dropped all nine of Bob's findings because his persona emits them as '- [BOB] ...' bullets and the parser anchors on '[AGENT]'

**Choice**: stripped the bullet prefixes from bob-output-202610111300.txt and re-ran the consolidator; noted the tooling gap in the review file

**Rationale**: fixable invocation problem per step 6's retry rule; dropping a whole lens's findings silently is the failure mode the step exists to prevent

### [deferred] 2026-10-16T19:22:33Z

**Decision**: The diff includes unrelated work outside PRD 00075: `skills/glean/SKILL.md`, `skills/glean/scripts/glean.py`, `skills/glean/scripts/test_glean.py`, and the `**glean**` CHANGELOG entry (`git log` shows glean landed in separate commits b389276 and c161810). None of the six tasks cover it. Confirm it belongs to another PRD and exclude it from this PRD's review.

**Rationale**: deferred by review-close

### [deferred] 2026-10-16T19:22:33Z

**Decision**: R1 only half fixed. `main()` now catches `RuntimeError` and exits 2, but a nonexistent `--root` still raises an uncaught `FileNotFoundError` from `subprocess.run(cwd=root)`. A traceback follows and the gates read exit 1 ("blocking"). The cycle-1 finding named this case explicitly. Fix: validate `root.is_dir()` in `main()` next to the unreadable-input check and exit 2 with a stderr message, or catch `OSError` alongside `RuntimeError`. Add a test. Blake adds the same class for `Cargo.lock`'s unguarded `read_text` in `known_packages`.

**Rationale**: rework cap reached with this finding unresolved

### [deferred] 2026-10-16T19:22:33Z

**Decision**: Relative PRD exclusions now resolve against `root` instead of the process cwd. With cwd `/work`, `--root repo`, and input `repo/prd.md`, the exclusion targets `/work/repo/repo/prd.md`; the real PRD can confirm its own invented symbols. Resolve input paths against the original cwd. Replace the regression fixture with a CLI call using these differing paths.

**Rationale**: rework cap reached with this finding unresolved

### [deferred] 2026-10-16T19:22:33Z

**Decision**: R6 only half tested. `_scannable_lines` now feeds the `declared` scan, so frontmatter and `link-ok:` lines are skipped as well as fences. Only the fenced region has a regression test (`test_new_symbols_line_inside_fence_does_not_declare_the_symbol`). The finding asked for tests on all three regions. Add one for a `New symbols:` line inside frontmatter and one for a line carrying `link-ok:`.

**Rationale**: rework cap reached with this finding unresolved

### [deferred] 2026-10-16T19:22:33Z

**Decision**: Tautological PRD-named test. `test_a_cited_line_without_the_named_symbol_blocks` cites a symbol that is itself `unresolved` in the repo, so exit 1 comes from the symbol lens whether or not the citation lens works. The test cannot fail if `check_citations` is broken. Fix: use a symbol that exists in the repo but not on the cited line, and assert the single row is a `missing` citation.

**Rationale**: rework cap reached with this finding unresolved

### [deferred] 2026-10-16T19:22:33Z

**Decision**: Tautological PRD-named tests. `test_a_library_api_in_installed_crate_source_is_ok` and `test_the_unverified_marker_and_link_ok_waive_their_lines` assert only exit 0. `unverified` rows exit 0 as well, so neither test can tell `ok` from `unverified` or `waived` from `unverified`. Fix: parse `--json` and assert the row status, and that no `link-ok:` line produced a row.

**Rationale**: rework cap reached with this finding unresolved

### [deferred] 2026-10-16T19:22:33Z

**Decision**: Weak PRD-named tests. `test_a_grounded_prd_exits_zero_with_only_ok_rows` has no citation, no `declared-new` symbol and no library claim, so it does not match the Happy-path scenario in the PRD. `test_cli_prints_table_json_and_exit_codes` checks substrings and never asserts the table sort order or the JSON row fields the scenario calls for.

**Rationale**: rework cap reached with this finding unresolved

### [deferred] 2026-10-16T19:22:33Z

**Decision**: Simplification (behavior-preserving) in `check_citations`/`_rows_for_file`. The `reasons: dict \| None = None` parameter forces four `if reasons is not None:` guards, and `_rows_for_file` re-guards with a 100+ character conditional. `reasons` is only populated for `missing`, so `detail = citation_reasons.get(orig, f"citation {rc.token}")` is equivalent. Also, the `OSError` branch reports "not found" for an unreadable file, which is misleading.

**Rationale**: rework cap reached with this finding unresolved

### [deferred] 2026-10-16T19:22:33Z

**Decision**: Locked crates without a `source =` line (path or workspace-local) are dropped from `known_packages`. The spec says known packages are "every `name = "<crate>"` in `<root>/Cargo.lock`". The deviation is defensible and a test pins it, but it contradicts the spec's package-identity rule.

**Rationale**: rework cap reached with this finding unresolved

### [deferred] 2026-10-16T19:22:33Z

**Decision**: Two Test Strategy scenarios lack the exact test names the Success Metrics require. `test_fenced_blocks_and_frontmatter_are_not_scanned` and `test_a_directory_argument_expands_to_its_markdown_files` do not exist; near-equivalents cover the behavior. The contract is a literal name match.

**Rationale**: rework cap reached with this finding unresolved

### [deferred] 2026-10-16T19:22:33Z

**Decision**: Both search helpers retain `--no-messages` and discard subprocess stderr, so exit-2 handling reports only a generic failure instead of the underlying diagnostic. Capture stderr, enable diagnostics, and assert the error text reaches CLI stderr; the current test only checks that stderr is nonempty.

**Rationale**: rework cap reached with this finding unresolved

### [deferred] 2026-10-16T19:22:33Z

**Decision**: Added acceptance tests do not fully enforce their named scenarios: the installed-library test accepts `unverified` because it checks only exit 0; the citation-symbol mismatch test can pass from the independently unresolved symbol; the happy-path fixture omits citations, declarations, and libraries. The computed fail-first replay confirms 10 of the touched tests pass against the pre-change code.

**Rationale**: rework cap reached with this finding unresolved

### [deferred] 2026-10-16T19:22:33Z

**Decision**: The test file now exceeds the 800-line limit: the mechanical facts place its final test at line 941. Split supporting fixtures and lower-level tests into focused modules while retaining the PRD-required named scenarios in `test_ground_prd.py`.

**Rationale**: rework cap reached with this finding unresolved

### [deferred] 2026-10-16T19:22:33Z

**Decision**: Redundant assertion. `assert "workspace_crate" not in packages.values()` can never fail, since the values are dicts. The `not in packages` line above it already covers the check.

**Rationale**: rework cap reached with this finding unresolved

### [deferred] 2026-10-16T19:22:33Z

**Decision**: Duplicate identical claims on one line each produce a row and each increment `blocking`, so the counts are inflated. Also, `check_citations` counts declared-new and library symbols as "names on the citing line", so a citation beside a not-yet-existing symbol would be marked `missing`.

**Rationale**: rework cap reached with this finding unresolved
