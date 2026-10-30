# Decision Audit Log: 00131-crafted-template-archive-escapes-directory-v1

PRD: `00131-crafted-template-archive-escapes-directory-v1.md`
Started: 2026-10-30T05:59:51Z
Completed: 2026-10-30T05:59:51Z
Autonomous: 8  |  Deferred: 10  |  Doubts: 0

### [autonomous] 2026-10-30T05:59:51Z

**Decision**: Cycle 1 review: 12 consolidated findings, 3 unresolved HIGH (R1 hardlink member accepted on the no-filter compatibility branch, R2 compatibility warning test pins a monkeypatch artifact and reverses PRD task 2, R4 normalization before _land erases pre-normalization traversal). Nine rows classified auto-fix, three discarded single-voice.

**Choice**: rework at cycle 1 of cap 2; auto-fix R1-R9, discard R10-R12

**Rationale**: Every fix is additive (a new refusal guard plus tests) with no signature, schema or data-model change, so the Classification auto-fix row applies and no research protocol or escalation is triggered. No CRITICAL row, so no rework design runs.

### [autonomous] 2026-10-30T05:59:51Z

**Decision**: Carl (gemini via copilot, model gemini-3.8-flash) exited 1 with 'You have exceeded your monthly quota' and published no output file.

**Choice**: logged and continued with Alice, Blake and Bob

**Rationale**: Safety Checks graceful-degradation row: a transient reviewer error is logged, not paused. Exit 1 is a one-off runtime failure, not exit 4, so Carl is not latched unavailable for the batch and the next cycle retries him.

### [autonomous] 2026-10-30T05:59:51Z

**Decision**: Compat branch (`archive.extractall(dest)` with no filter) still lets a hardlink member through. `_refuse_duplicate_or_crossing_members` never inspects `islnk()` members. A hand-built tar with one `LNKTYPE` member `h` -> `../outside/secret.txt` passed the preflight, the unfiltered extract created `dest/h`, and its inode equalled the outside file's. On the `filter="data"` branch the same member raises `tarfile.LinkOutsideDestinationError` (a `FilterError`) after a partial extract, not the `TreeError` the PRD requires. The PRD's "missing runtime support must never silently select unrestricted extraction" is therefore unmet, and the design's claim that the preflight "has proven every member's ancestry stays inside dest" is false for hardlinks. Fix: refuse `islnk()` members (and non-regular, non-dir, non-symlink members) with a `TreeError`, add a test for it, and add the missing test for the `os.path.isabs(member.name)` refusal

**Choice**: auto-fixed

**Rationale**: fixed by review-close

### [autonomous] 2026-10-30T05:59:51Z

**Decision**: `test_build_template_s_compatibility_path_still_raises_the_omitted_filter_warning` asserts that `DeprecationWarning` fires with `data_filter` removed. That state does not exist on a real runtime: on 3.12 the warning machinery is present and only `data_filter` was deleted; on a genuine pre-backport 3.10 there is no warning machinery, so `pytest.raises` fails DID NOT RAISE; on 3.14 the data filter is the default and it also fails. The test pins an artifact of the monkeypatch, not a contract, and it reverses PRD task 2, which requires the compatibility branch not to warn. It never verifies successful sealing on that branch either. Assert only what is portable: the compatibility branch seals the tree and emits no omitted-filter warning

**Choice**: auto-fixed

**Rationale**: fixed by review-close

### [autonomous] 2026-10-30T05:59:51Z

**Decision**: Several new tests pass against the pre-change code, so they do not pin the fix. Overlaying the new test file on base b0c6bf2: 6 failed, 10 passed. Passing at base: `escaping-link-then-directory`, `directory-then-escaping-link` and `safe-link-then-escaping-link-write-through`, because base's dict walk still sees the escaping link; all three `ANCESTOR_CROSSINGS` cases also pass at base, because each fixture's symlink already escapes and the old symlink-only walk catches it. The PRD's "reject member paths whose ancestors cross symlinks" requirement, and the design's "case the current code cannot catch", are therefore pinned by no base-failing test. The mechanical fail-first replay reports 9 touched tests passing at base. Add a case whose symlink is safe independently but whose file-member traversal escapes, or drop the per-member `_land` loop at trees.py:142-143 and record the redundancy

**Choice**: auto-fixed

**Rationale**: fixed by review-close

### [autonomous] 2026-10-30T05:59:51Z

**Decision**: Normalizing before `_land` erases security-relevant traversal: `alias -> .` plus member `alias/../outside/secret.txt` passes preflight as `outside/secret.txt`. Unfiltered extraction can overwrite the outside sentinel; filtered extraction can raise an untranslated tarfile error. Validate original path traversal before normalization and preserve the TreeError contract; add this regression on both branches. Note also R6/R8, the same ancestor-crossing laxity raised by two reviewers in words the consolidator did not merge: `_land` accepts a member beneath a symlink whose own target stays inside the tree, so `alias -> pkg` plus `alias/file` can overwrite `pkg/file` despite distinct normalized names.

**Choice**: auto-fixed

**Rationale**: fixed by review-close

### [autonomous] 2026-10-30T05:59:51Z

**Decision**: Cycle 2 ended with 4 unresolved HIGH findings (R1-R4) at rework cap 2; cap-check classified none as a regression introduced by cycle-1 rework (exit 0)

**Choice**: cap-out: deferred all 9 unresolved findings to batch end as cap-overflow records and proceeded to finalize

**Rationale**: loop-mode cap-out defers rather than pausing; no CRITICAL row, so no cap_critical stall applies

### [autonomous] 2026-10-30T05:59:51Z

**Decision**: Carl (gemini) failed with exit 1, monthly copilot quota exhausted, for the second cycle running

**Choice**: recorded as a one-off runtime failure; no retry dispatched, no batch latch

**Rationale**: exit 1 is not exit 4, so the batch latch does not apply; a retry would re-hit the same monthly quota ceiling in the same calendar month, so the cycle proceeded on Alice, Blake and Bob (graceful degradation)

### [deferred] 2026-10-30T05:59:51Z

**Decision**: No CHANGELOG.md entry for a containment security fix that changes user-visible refusal behaviour (duplicate and absolute members now raise `TreeError`). CHANGELOG.md already carries `**use-qwen**:` entries under Fixed, so the project convention applies. Add one under `[Unreleased]` / Fixed

**Choice**: deferred

**Rationale**: deferred by review-close

### [deferred] 2026-10-30T05:59:51Z

**Decision**: The rework adds three refusal paths with no test: non-file/dir/symlink members, the os.path.isabs(member.name) refusal (trees.py:143), and the landing-collision refusal (alias -> pkg plus alias/file, trees.py:161). Cycle-1 R1 asked for a hardlink test and an absolute-member test and neither exists; deleting trees.py:145-146 or :161-163 leaves the suite green. _crafted_tar needs a hardlink kind. Merged with Alice's false compat-test comment (test_eval_tree_links.py:490) and Blake's missing warning-as-error check on the compatibility path (:487).

**Choice**: deferred to batch end

**Rationale**: rework cap reached with this finding unresolved

### [deferred] 2026-10-30T05:59:51Z

**Decision**: The compatibility branch is an unfiltered fallback: with tarfile.data_filter missing, build_template calls bare archive.extractall(dest). The preflight checks no modes, so setuid/setgid bits and ownership metadata from a crafted tar are applied unfiltered. The PRD forbids an unfiltered fallback; the fallback should be a safe manual filter or a TreeError refusal.

**Choice**: deferred to batch end

**Rationale**: rework cap reached with this finding unresolved

### [deferred] 2026-10-30T05:59:51Z

**Decision**: The compatibility path still raises the omitted-filter DeprecationWarning that finding 42 requires removed. With -W error::DeprecationWarning on CPython 3.12.16 two tests fail on the warning raised from trees.py:183 (test_build_template_seals_a_safe_tree_with_or_without_tar_data_filter[without-data-filter] and the compatibility-path sealing test).

**Choice**: deferred to batch end

**Rationale**: rework cap reached with this finding unresolved

### [deferred] 2026-10-30T05:59:51Z

**Decision**: Symlink ancestors still permit a containment bypass: for pkg/, alias -> pkg, alias/escape -> ../../outside and pkg/escape/secret.txt, the map records alias/escape but _land looks up pkg/escape after resolving alias, so the escaping target is missed. Reject members beneath archive symlinks before extraction, with a regression on both branches.

**Choice**: deferred to batch end

**Rationale**: rework cap reached with this finding unresolved

### [deferred] 2026-10-30T05:59:51Z

**Decision**: The compatibility-branch tests only seal benign trees with the filter hidden. No test shows the crafted attack archives refused, or the sentinel untouched, with data_filter hidden, although the PRD asks for both filter-support branches.

**Choice**: deferred to batch end

**Rationale**: rework cap reached with this finding unresolved

### [deferred] 2026-10-30T05:59:51Z

**Decision**: Prior R1's hardlink and absolute-member regressions remain absent, and the new unsupported-type refusal and landing-collision check also lack tests. Add isolated refusal cases and exercise the compatibility branch, verifying unchanged outside state.

**Choice**: deferred to batch end

**Rationale**: rework cap reached with this finding unresolved

### [deferred] 2026-10-30T05:59:51Z

**Decision**: Prior R2 remains incomplete: the replacement compatibility test removes warning verification entirely, and the proxy still delegates extraction to modern tarfile, so it does not reproduce legacy warning behavior. Mechanical replay confirms the test passes against the previous implementation.

**Choice**: deferred to batch end

**Rationale**: rework cap reached with this finding unresolved

### [deferred] 2026-10-30T05:59:51Z

**Decision**: `originals` duplicates every member.name solely to zip it back onto the same members; iterate `for member in members` and pass member.name directly to _land and the diagnostics.

**Choice**: deferred to batch end

**Rationale**: rework cap reached with this finding unresolved

### [deferred] 2026-10-30T05:59:51Z

**Decision**: The landing-collision check skips symlink members: a symlink alias/ln and a file pkg/ln under alias -> pkg are both accepted although they write the same path, so extraction order decides which survives, while the docstring promises such members are refused.

**Choice**: deferred to batch end

**Rationale**: rework cap reached with this finding unresolved
