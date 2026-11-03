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

# Assumptions ledger — PRD 00162-template-archive-breaks-on-windows-v1

## 1: Add executable-bit-survives-the-seal regression

- Git reads `GIT_CONFIG_KEY_<n>` / `GIT_CONFIG_VALUE_<n>` with an underscore before the index, not the `GIT_CONFIG_KEY0`/`GIT_CONFIG_VALUE0` spelling the task description used; forced `core.filemode=false` via the environment using the underscore form (Ivan).
- Forced the config through the environment, not by patching `trees.IDENTITY`, since `IDENTITY` appears to be passed only to the commit call, not to `git add -A`; could not fully confirm since trees.py was outside the allowlist for this task (Ivan).
- One executable file and one plain file are enough; dropped the neighbouring test's second pair (it guards against guessing the bit from the file name, which doesn't apply to this cause) (Ivan).
- The test name contains `executable_bit_survives` to match the verify command's `-k` filter (Ivan).

## 2: Add symlink-order and symlink-chain-through-directory regressions

- Regressions A and B use the no-data-filter branch (`_hide_data_filter`), because the design leaves the `extractall(filter="data")` branch untouched; a test against that branch would stay red after the fix (Ivan).
- The spy keys calls by the link's base name (`Path(path).name`), since the staging directory name is random; every link in these tests sits at the top level (Ivan).
- The target text is compared as `os.fspath(target)`; these targets have no separators, so the Windows backslash form does not change them (Ivan).
- The task's premise that `fresh_clone` "currently passes by accident" does not hold on this runtime: today's `shutil.copytree(symlinks=True)` calls `os.symlink` with no `target_is_directory` at all, so the spy records `False` and the clone test fails on that assertion directly. Asserted what `os.symlink` is asked for rather than the non-existent `_copytree_links_typed` helper's `AttributeError`, so the test does not depend on that helper's name (Ivan).
- Regression B also asserts that `b` is typed as a directory, not only `a` (Ivan).

## 3: Add read-only-staging-survives-cleanup regression

- Patched only `os.unlink`, not `os.rmdir`: the spec reads "os.unlink/os.rmdir (or Path.unlink)" as a choice, and refusing one read-only file alone is enough to leave staging behind (Ivan).
- The patched `os.unlink` refuses every file without the owner-write bit inside staging, not only the one explicitly chmod'ed - this includes Git's 0444 object files, matching the real Windows cause (Ivan).
- The patch accepts a `dir_fd` argument, because on this Python (3.14) `shutil.rmtree` deletes through dir_fd (Ivan).
- Did not verify the planned `_remove_tree` fix would pass this test (the fix doesn't exist yet and trees.py was outside the allowlist); inferred from the design doc only that chmod to `S_IWRITE` plus retry would route through the patched `os.unlink` to a real delete (Ivan).

## 4: Set Git index modes from archive members before the seal commit

- **Adversarial finding (Devon), confirmed before implementation:** calling `archive.getmembers()` after the `with tarfile.open(...)` block in `build_template` has closed raises `OSError: TarFile is closed` - members must be captured inside that block. Fixed in the implementation: `members = archive.getmembers()` now runs inside the `with` block and is reused for `_refuse_duplicate_or_crossing_members` too (Devon, then Ivan).
- Devon broke the task-1 regression test with 7 exploits (hardcoded name lists, reading the exec bit off the staging disk instead of the archive, keying on the wrong mode bit, exact-mode matching, `bin/`-only scoping) before this task's implementation existed. The test was strengthened in response (see task 1's ledger entry above) before the real fix was written (Devon, Ivan).
- Paths passed to `git update-index` use the raw `member.name`, not a normalized one, per the design contract; the archive members are already validated upstream (Ivan).
- `_extract_without_filter`'s existing `os.chmod` calls were left unchanged to keep the diff small, rather than also reusing the newly-captured `members` there (Ivan).
- **Infra, recurring:** Pat's per-task review (`sonnet-run.sh`) failed with "OAuth token revoked" - the same deterministic headless-child OAuth issue recorded for PRD 00160 tasks 3/4 (coordinator `CLAUDE_CODE_OAUTH_TOKEN` not reaching the `claude -p` child). A workaround (injecting the token via a wrapper script) was blocked by warden as an unrecognized command. Recorded as `review: failed:oauth_token_revoked`; not re-attempted for later tasks in this batch. The mandatory PRD-level review phase covers this task's diff.
- **Regression fix (step 7, after task 8):** the full suite caught 10 setup errors in `test_eval_tree_proofs.py`, all `git update-index --chmod` exit 128 on a file ("stale-artefact.txt" in that module's fixture) that the original repo force-committed despite a `.gitignore` rule. `git archive` still includes it, so `_set_index_modes` saw it in `members`, but in the fresh staging repo `git add -A` silently skips an as-yet-untracked, now-gitignored path - so `update-index --chmod` refuses the whole pathspec (it refuses an untracked path where `add -A` would have quietly skipped it). The regression-fix brief (written by the orchestrator, not from the design doc) proposed force-adding the file instead; Ivan tried it, found it broke three `prove_state` tests that rely on the ignored file staying OUT of the sealed commit (`git status --porcelain` must stay silent about it - that is the exact property those tests check), reverted the force-add, and instead filtered `_set_index_modes`'s own member list down to `git ls-files -z`'s tracked set - restoring the pre-task behavior for an ignored-but-archived member (stays untracked in the seal, still covered by `fresh_clone`/the manifest) while fixing the crash. Correctly treated the tests as the spec over the orchestrator's own (wrong) brief, per the implementor's standing rule; no test file was touched (Ivan).

## 5: Create symlinks in a typed, native-separator second pass

- **Adversarial finding (Devon), confirmed before implementation:** the original task-2 tests (all links landing on a directory, short dot-free names, forward archive order) left 5 distinct ways to type every link as a directory without actually resolving landings correctly. The tests were strengthened in response (see task 2's ledger entry above) before this task's implementation was written (Devon, then Ivan).
- `_lay_links_typed` takes `(dest, members)` with no separate `written`/`written_dirs` set: by the time links are laid (a strict second pass, after every file and directory member is already on disk), `_land`'s own chain-walk already resolves a landing to a real (non-symlink) path, so `(dest / landing).is_dir()` alone gives the same answer the design's `written_dirs` check would, and also covers a directory that exists only as the parent of a file member (Ivan).
- In `fresh_clone`'s second pass, symlinks under the template's `.git` directory (if any) are also re-laid, because the `copytree` ignore callback that skips symlinks in the first pass sees every directory, `.git` included (Ivan).
- **Infra, recurring:** Pat's per-task review was not attempted for this task - the OAuth-revoked infra failure confirmed twice already this PRD (tasks 4 and this one's own first attempt would hit the same deterministic cause) is not re-attempted per the task-4 precedent. Recorded as `review: failed:oauth_token_revoked`. The mandatory PRD-level review phase covers this task's diff.

## 6: Replace staging cleanup with read-only-aware removal

- **Adversarial finding (Devon), confirmed before implementation:** the original task-3 regression left 7 distinct ways to pass without a real read-only-aware delete: renaming the undeletable staging aside instead of removing it, shelling out to `chmod -R`/`rm -rf` and ignoring the result, deleting via `os.remove` (unpatched) instead of `os.unlink`, swallowing a persistent cleanup failure, retrying on any error rather than only a read-only refusal, and discarding the original exception for an unrelated `TreeError`. The test was strengthened in response (a tightened `_names(tmp_path) == present` assertion, `os.remove` patched alongside `os.unlink`, an `excinfo.value is error or excinfo.value.__cause__ is error` check, and a new twin test for a refusal that never lifts) before this task's implementation was written (Devon, then Tess).
- With a cleanup that never succeeds, the caller may see the `PermissionError` on top, chained to the injected error, or the reverse; the twin test's assertion accepts either order (Tess, strengthen round).
- A refusal counts as "never lifts" by file basename, since `shutil.rmtree`'s fd mode passes bare names with `dir_fd`; Git's own read-only object files are refused and retried too, so the twin does not require `a.txt` specifically to be the file that surfaces (Tess, strengthen round).
- Restoring permissions in the twin test's `request.addfinalizer` is test hygiene (so pytest's own tmp-dir cleanup can still delete the fixture), not new behavior under test (Tess, strengthen round).
- Kept the `onerror` branch (Python 3.10/3.11) alongside the `onexc` branch (3.12+) per the design contract, though only the `onexc` branch is exercised on this runtime's Python 3.14 (Ivan).
- One handler function serves both the `onexc` and `onerror` signatures; its third argument (the exception, or the `exc_info` tuple) is unused by either (Ivan).

## 7: Make owner and mode checks host-neutral

- `_sealed_modes` exists in `test_eval_tree_archive_safety.py` with the shape the brief describes; did not read that file directly (outside the allowlist), confirmed by the import resolving and the suite passing (Ivan).
- Used `hasattr(os, "getuid")` as the one POSIX-vs-host guard for both the uid check and the raw `st_mode`/special-bit/`UNSAFE_DIRECTORY_BITS` checks, rather than a separate `hasattr(os, "chmod")`-style guard per check (Ivan).
- The new sealed-mode assertion in the refusal-or-accept test runs only in the `else` (accept) branch, since a refused archive leaves no sealed tree at `dest` to read (Ivan).
- Left `status.st_gid == dest.stat().st_gid` unguarded (runs on every host), since the brief named only the uid and mode-bit checks as POSIX-only (Ivan).

## 8: Add extended-prefix normalization helper and apply it at both fixture assertions

- The brief's top-of-file import for `test_eval_tree_state.py` is circular: `test_eval_tree_links.py` already imports from `test_eval_tree_state` at load time, so importing `_extended_prefix_stripped` back at the top of `test_eval_tree_state.py` fails in either module-load order (`ImportError: cannot import name ... from partially initialized module`, confirmed by running it). Moved the import inside the one test function that needs it instead, with a comment explaining why; the helper still lives only in `test_eval_tree_links.py` (Ivan).
- Chose the parametrize ids (`extended-drive`, `extended-unc`, `short-drive`, `posix`) and the new unit test's name myself, since the brief did not specify them (Ivan).

# Assumptions ledger — PRD 00164-clone-links-and-disk-mode-check-on-windows-v1

## 1: Add a spy regression for host-separator link text in fresh_clone

- `_template_on_disk` writes `calc.py` with the content `inside\n`. Taken from the existing assertion at line 754, not from reading the helper.
- `trees.os` is the global `os` module, so the red check patched `os.sep` for the whole process. `monkeypatch` undid it, and `_host_form` saw the same patched value.
- Targets were compared as a dict and the type flag was ignored, because the task asked only for the name-to-target mapping.

## 2: Convert clone link text to the host separator in _copytree_links_typed

- The Windows-only test (task 1's regression) is the one this task targets. It is the only test in the commit, and nothing fails on this host.
- On Windows, `os.readlink` returns a relative target with the same separators it was created with, so converting `/` to the host separator gives the expected form.
- Call order across links is not part of the contract, so the strengthened test's comparison is `sorted(calls) == sorted(expected)`, which still counts duplicates. This matches the sibling typing test just above it.
- `same -> alias/calc.py` should be typed as a file (`False`), because its chain resolves to the regular file `calc.py`.

## 3: Guard the on-disk executable-bit loop with the host capability probe

- Running the probe (`_host_carries_an_executable_bit()`) in a separate process counts as the check the spec asked for (that the `if` branch is taken on macOS), in place of a temporary print.
