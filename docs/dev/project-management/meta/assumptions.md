# Assumptions ledger — PRD 00131-crafted-template-archive-escapes-directory-v1

## 1: Fix build_template's duplicate-member/symlink-ancestor containment preflight

- `./escape` and `escape` count as "normalize to the same path" (Tess).
- On refusal, `dest` may exist but must be empty, as in the existing tests (Tess).
- The safe-seal test with a crafted archive is fine to keep, as the accept case that matches the refusal tests (Tess).
- The helper returns `None`, not the link map the design docstring mentions, because nothing uses that map (Ivan; the design review log raised this too — not acted on further since it does not affect correctness).
- Hardlink members are not handled separately; no test covers them (Ivan — matches the design's own "Likely next change 1" scoping note).

## 2: Cover finding 42: explicit safe extraction removes the omitted-filter deprecation warning

- Interpreted "the specific omitted-filter deprecation warning" as the message tarfile actually raises on this repo's pinned Python (3.12.16): "Python 3.14 will, by default, filter extracted tar archives and reject files or modify their metadata. Use the filter argument to control this behavior." Matched on a literal prefix substring (Ivan).
- Interpreted "treats ... as an error" as scoped per-branch: the `filter="data"` branch must never raise it (regression detector), while the compatibility branch is expected to raise it (explicit documentation of known, currently-accepted behavior) — rather than expecting zero warnings on both branches, since direct experimentation showed the compatibility branch genuinely triggers the warning under the current, correct implementation (Ivan).
- Reused the existing safe-link crafted-archive fixture shape (`pkg` dir + file + an internal symlink `escape -> pkg`) from `test_build_template_seals_a_crafted_archive_with_unique_safe_members` to satisfy "confirm safe-link controls still pass, including the compatibility path," rather than inventing a new archive shape (Ivan).

## 3/4 (rework, cycle 1): [D1] skills/use-qwen/scripts/test_eval_tree_links.py

- Fixing the pre-existing `test_build_template_seals_a_safe_tree_with_or_without_tar_data_filter[without-data-filter]` failure (same root-cause `delattr` bug, not explicitly named in either finding) was treated as in scope, since the task's own verification command runs the whole file and both findings are framed as "fix the unsafe `data_filter`-hiding approach" (Ivan).
- Dropped the `warnings.catch_warnings`/`filterwarnings("error")` instrumentation in the renamed compatibility-path test entirely, rather than keeping it and expecting no exception, because keeping `filterwarnings("error")` would turn the real (on Python 3.13) `DeprecationWarning` into a hard test failure there — incompatible with this project's 3.10/3.13 CI matrix (Ivan).

# Assumptions ledger — PRD 00160-template-archive-extraction-fails-closed-v1

## 1: Add failing A1-A7+A12 security matrix for archive extraction

- Either refusing the archive (`TreeError`, empty `dest`) or extracting with the special bits and the foreign owner stripped counts as passing A7; the brief says only "not applied" (Tess).
- Ownership metadata alone must not cause a refusal, because `git archive` writes uid 0 / `root` on every member; the accept case pins this (Tess).
- A12 "normalized names" means path-normalized and then compared case-insensitively (Tess).
- "File then a file under it", in both orders, counts as an A5 file/dir swap (Tess).
- `C:outside`, `\outside`, `\\?\...`, `name:stream` and `::$DATA` must be refused both as member names and as symlink targets, on every host OS (Tess).
- The no-filter seam extends `_hide_data_filter` with an `extractall` double that rejects `filter`, following the brief's contract; the existing helper alone does not reject the keyword (Tess).
- The empty-archive case is not tested: its behavior is unspecified, and the current code fails it with a git "nothing to commit" error (Tess).
- Combining several wrong behaviours in one passing implementation counts as proof for each of them, since every one is present at the same time (Devon).
- For world-writable/sticky modes (A7 strengthening), group/other write and sticky bits should be cleared or refused; the tests and module do not say (Tess, strengthen round).

## 2: Add valid-input controls to the archive safety matrix

- Controls were run on both seams, not limited to filter-present, since both pass and that matches the file's convention (Tess).
- "Round-trips byte-for-byte" means both the extracted file and the blob in the sealed commit (Tess).
- For the determinism test, the `GIT_*_DATE` env vars are environment, not input, so a correct seal must ignore them (Tess).
- Dangling links point inside the tree, as the task says (Tess).
- Comparing the sealed commit's author/committer date as epoch seconds (not the ISO string `trees.SEAL_DATE` carries) satisfies the "assert the seal date" strengthening, since git's `%aI` renders a `Z` suffix for the same instant `SEAL_DATE` writes as `+00:00` (Tess, strengthen round).
- **Flagged, not acted on:** on this runtime, `tarfile.data_filter` itself rewrites symlink target text on extraction (`./pkg/a.txt` -> `pkg/a.txt`, `../pkg/.` -> `../pkg`) rather than preserving it verbatim. The design doc's claim that `_extract_without_filter` "mirrors `data_filter`, which also preserves symlink text" (task 4's contract) does not hold for this stdlib version. A verbatim-link-text test was written, found to fail against the current (pre-fix) code on the filter-present seam, and was reverted rather than landed, since task 2's acceptance criterion requires controls to pass against unmodified `trees.py`. This is a product-decision flag for whoever implements/reviews task 4, not a task-1/2 defect (Tess, strengthen round).

## 3: Implement archive-domain classification, ancestor crossing, and type refusal in trees.py

- A symlink's landing in the duplicate/collision check is its own location (its parent resolved through `_land`, then its own last segment), not where its target points — using the target's landing would break the SAFE_LINKS/LINK_CHAINS controls, since e.g. `file-link -> pkg/a.txt` would then collide with `pkg/a.txt` itself (Ivan).
- The "ancestor is a file" check only treats regular-file landings as blocking ancestors; directory and symlink landings are not (Ivan).
- Case folding (A5/A12) is applied to whole normalized names only, not to resolved landings reached through a link (e.g. `alias/A.txt` against `pkg/a.txt`) — no test exercises that combination (Ivan).
- Under the "NTFS stream-like" rule's "after position 0" wording, a path component that STARTS with a colon (e.g. `:foo`) is not refused by this implementation (Ivan).
- **Known gap, deliberately left:** `_archive_name_escapes`'s "any backslash anywhere" rule, applied inside `_land`, now also reaches `_refuse_escaping_links` (used by `fresh_clone`) — a cloned tree whose link text holds a backslash or an embedded colon is refused too, past the archive-extraction path the PRD scoped. The design's own contract calls for this (the predicate is shared by construction), but it is a behavior change outside `build_template`'s surface; flagged for the review phase (Ivan).
- Per-task review (Pat) could not run for this task: `sonnet-run.sh` failed with "OAuth token revoked" on the first dispatch, then "Session ID already in use" on the retry (the first attempt's partial session). This is the known headless-child OAuth issue (coordinator token not propagated to `claude -p` children); recorded as `review: failed:...` on the attempt. The mandatory PRD-level review phase (Alice/Blake/Bob/etc.) still covers this task's diff.

## 4: Replace bare extractall fallback with _extract_without_filter and _safe_mode

- The filter-present branch's new `TreeError` message (for the FilterError/OSError try/except wrapper) is `"extraction failed: %s" % cause` - the contract named no message format for that branch (Ivan).
- A symlink member's parent directories are created before `os.symlink`, the same as for a file member (Ivan).
- **Flagged, not acted on:** directories are chmod'ed to their safe mode immediately in archive order (not deferred to the end, unlike `tarfile`'s own extraction). If an archived directory's mode lacks the owner-write bit, a later member written inside it would fail with `TreeError` instead of extracting. No test in this matrix covers that case; `git archive` directories are ordinarily `0755` so this has not been observed to bite in practice (Ivan).
- **Infra, recurring:** Pat's per-task review (`sonnet-run.sh`) failed identically to task 3 (OAuth token revoked, then session-id collision on retry) - confirmed deterministic, not transient, across two tasks. Stopped re-attempting the retry for subsequent tasks in this batch to avoid spending a doomed dispatch each time; `review: failed:...` recorded and the mandatory PRD-level review phase covers the gap. This is an environment/session issue (coordinator `CLAUDE_CODE_OAUTH_TOKEN` not reaching the `claude -p` child), not a finding about the code.

## 5: Stage extraction and seal, then rename into dest atomically

- The cleanup handler catches `BaseException`, not `Exception` (so an interrupt mid-build still removes the staging directory), and always re-raises - never swallows a signal, only runs cleanup before propagating it (Ivan).
- `git archive` is still fetched before the `os.path.lexists(dest)` guard; the contract only requires the guard before extraction, not before the archive read (Ivan).
- The final-rename failure message ("... could not be published: ...") was authored freely; the contract gave no wording for it (Ivan).
- No `lexists` re-check runs immediately before the final `staging.rename(dest)` - the design accepts the TOCTOU race as out of scope; a `dest` that appears mid-build still gets refused because `rename` onto an existing non-empty directory/file raises `OSError`, translated to `TreeError` the same as any other failure on this path (Ivan).

## 8 (rework, cycle 1): [D1] skills/use-qwen/scripts/eval_harness/trees.py

- `NFC_E`/`NFD_E` sit at module level under the `-- A1` section rule, since the brief said "in the test module" without naming a line; the file's own habit is to define constants beside the section that uses them (Tess).
- No per-entry comment was written for the two `-inverse` entries, reading "give the individually non-obvious ones ... one line each" plus "do not restate what an entry's id already says" as excluding them (Tess).
- The two `case-alias-directory-link*` member lists were wrapped across two source lines to match the surrounding entries' line width (Tess).
- The host merges names by case and by normalization form (the APFS behaviour named in the task description), so `éDir` / `édir` spelled across NFC and NFD count as one merged name for the `case-and-normalization-alias-in-one-name` entry (Tess). Coordinator note: the contract's `_fold` uses `str.lower`, not `str.casefold`, and every added entry is still refused under simple lowering, so the looser wording does not affect the implementation.
- A link whose own target text stays inside the tree (`.`, `..`, a sibling link name) is not refused by any already-implemented rule, so each added entry can only be refused by the merged-name logic this task targets; confirmed empirically by all 12 new parametrizations failing against the pre-change tree (Tess).
- `_land`'s folded lookup was built as a single uniform `{(_fold(key) if fold else key): key}` dict rather than branching on `fold` in two places; the contract specified the folded map only, and this keeps `fold=False` byte-identical in behaviour while avoiding a second code path (Ivan).
- `crossed.add(probe)` runs immediately after a slot is confirmed to be a link and before the cycle check; the contract did not order the two, and the ordering is unobservable because the cycle branch raises (Ivan).
- The 1 skipped test in the adjacent-file run is assumed to be a pre-existing capability guard rather than a regression, on the reasoning that this change can only make a check raise or not raise and so cannot produce a skip; not verified against the pre-change tree (Ivan).
- `_refuse_colliding_landings`'s docstring was left unchanged even though its `_land` calls now fold, because the contract pins "nothing else changes" for that function (Ivan).
- The pre-existing UP031 ruff findings in `trees.py` (16, across lines the task did not touch) are out of scope and deliberately tolerated, since the design contract forbids changing any refusal string (Ivan, style-fix pass).
- The style gate measures a function's span from its `def` line through its last body line inclusive, so cutting 3 lines from the recursive call and 2 from the docstring (54 -> 49) clears the 50-line limit; the gate itself was not run by the fixer (Ivan, style-fix pass). Coordinator note: the gate was re-run by the orchestrator and exited 0.

## 9 (rework, cycle 1): [D1] skills/use-qwen/scripts/eval_harness/trees.py (4 HIGH + 1 MEDIUM)

- Finding 3b (fully-restrictive file mode) is written to accept either a consistent accept or a consistent refuse outcome across both seams, since the task's own wording says "either is acceptable PROVIDED both seams agree"; only agreement and the TreeError-not-raw-exception requirement are pinned, not which disposition is "correct" (Tess).
- For finding 5, "no sibling staging directory left behind" is verified by snapshotting `tmp_path`'s own direct children before/after the call, since the entire `a/b/c` ancestor chain is absent before the call and must remain absent after (Tess).
- For finding 4, host-portability on the manual path was first interpreted (Tess) as POSIX-observable behavior only (`is_symlink()`, read-through, `readlink()`), without inspecting `target_is_directory` itself. Coordinator note: on POSIX, `target_is_directory` is a no-op, so that test cannot discriminate a fix from no fix at all — confirmed the production `os.symlink` call still carried no `target_is_directory` argument after Ivan's pass, and the finding was genuinely unresolved. Implemented the fix directly (a `_symlink_targets_a_directory` helper resolving the target through the archive's own validated member graph) and replaced the non-discriminating assertion with one that spies on `os.symlink`'s own call arguments across a directory-target and a file-target link side by side — confirmed red against the unfixed code before landing.
- Finding 1 (filter-detection predicate, `hasattr` vs `callable(getattr(...))`): the original success-only assertion did not distinguish the predicates because named filters resolve through tarfile's internal registry. The claim that no test can observe this distinction was incorrect. Cycle-2 R4 recovery spies on `_extract_without_filter`, requires one invocation for a non-callable `data_filter`, and checks the real extracted content. Replacing the callable check with `hasattr` now fails that regression without modifying CPython internals.
- Ivan's own assumptions, from his report: the directory-permission fix (finding 3a) defers `_safe_mode` chmod to after every member is written (matching the level of parity the filter seam needs for child extraction), rather than mimicking `data_filter`'s more drastic "never apply a directory's archive mode at all" behavior — the given tests only assert child-content readability, not the directory's own final mode, so both approaches would pass; the deferred-chmod choice keeps `_safe_mode`'s existing "applies to files and directories alike" contract intact. The file-permission fix (finding 3b) ORs exactly `stat.S_IRUSR | stat.S_IWUSR` onto the chmod call (matching `data_filter`'s own floor), without also replicating `data_filter`'s executable-bit-clearing step, since the given tests exercise no executable member and leaving exec bits untouched keeps the diff minimal.
- Recovery note (2026-11-08): cycle-2 R1 recovery supersedes the directory-mode choice in Ivan's preceding historical report. Deferred directory chmod was removed; directories now use mkdir defaults and the process umask, matching `data_filter`. The file-mode behavior and its recorded limitations remain unchanged.
- Per-task review (Pat): `sonnet-run.sh` failed identically to tasks 3/4/8 (OAuth token revoked, then session-id collision on retry) - the same deterministic headless-child OAuth issue. Fell back to the native `autopilot:pat` Claude subagent at sonnet for both task 9 and task 10's reviews, recording the actual backend used.
- Pat's first review of task 9 found finding 5 only half-fixed: `staging.mkdir(parents=True)` still sat outside the `try:` block, so its own `OSError` still escaped unwrapped (as a raw `PermissionError`) and skipped the `created_ancestor` cleanup — filed MEDIUM, CLOSURE unresolved. Verified directly (confirmed the raw exception leaks, by temporarily reverting the structure and re-running the new test), then fixed by nesting `staging.mkdir(parents=True)` in its own `try/except OSError -> TreeError` inside the outer try, with a new regression test (monkeypatches `os.mkdir` to fail only for the staging path) confirmed red against the pre-fix structure before landing.
- Pat's second review (after the mkdir fix) closed all 5 quoted findings `resolved`, with one residual LOW: `created_ancestor = _topmost_missing_ancestor(dest.parent)` itself still runs before the outer `try:`, and `Path.exists()` can re-raise `OSError` for errors `_ignore_error` does not treat as "doesn't exist" (e.g. `EACCES` on an inaccessible intermediate ancestor) - the same class of defect finding 5 named, at a different call site, pre-existing and not introduced by this task. Confirmed by reading `pathlib.Path.exists()`'s source directly (it re-raises unless `_ignore_error(e)` is true). Left unfixed and carried to the PRD-level review per the LOW-only outcome rule (`review` left unset on both tasks' attempt records; both reviews closed CLOSURE-resolved/LOW-only, no HIGH/MEDIUM survives).
