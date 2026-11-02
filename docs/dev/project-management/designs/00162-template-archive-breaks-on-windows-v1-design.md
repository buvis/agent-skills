# Design: Seal and clone templates correctly on native Windows

## Architecture fit

All five causes live inside `skills/use-qwen/scripts/eval_harness/trees.py`,
the harness module that seals a Git tree from an archive (`build_template`)
and copies a sealed template per attempt (`fresh_clone`), plus their test
suite (five modules under `skills/use-qwen/scripts/`). No other module calls
into these causes: `hash_paths`/`contained`/`overlay_oracle` read an already
-built tree and are untouched by this PRD (00160's containment logic they sit
on stays as-is). This PRD edits `trees.py` and five test modules only — same
boundary the PRD's own Structural Decomposition names.

## Module placement

- Edit `skills/use-qwen/scripts/eval_harness/trees.py`:
  - `build_template`: add an index-mode-from-archive step after `git add -A`
    (new private helper `_set_index_modes`); replace the symlink-writing arm
    of `_extract_without_filter` and the old `shutil.rmtree(staging,
    ignore_errors=True)` cleanup with new helpers below.
  - New private helpers: `_set_index_modes(staging, members)`,
    `_lay_links_typed(dest, members, written)`, `_remove_tree(path)`.
  - `fresh_clone`: route its copy through a two-pass files-then-links
    sequence (new private helper `_copytree_links_typed`) instead of
    `shutil.copytree(..., symlinks=True)`.
- Edit tests (no new test files — the PRD's Repository Structure table names
  the five existing modules):
  - `test_eval_tree_archive_safety.py`: add the executable-bit-survives
    regression (`core.filemode=false` forced) next to the existing
    `test_control_build_template_keeps_the_executable_bit_and_only_where_it_was_set`.
  - `test_eval_tree_links.py`: add link-order regressions (`os.symlink` spy
    recording `target_is_directory`/target text) and extend the two fixture
    assertions at the extended-prefix line with the new helper.
  - `test_eval_tree_archive_staging.py`: add the read-only-staging regression
    (mark a staging file read-only, make deletion fail the old way, assert no
    `template.staging-*` sibling survives).
  - `test_eval_tree_archive_safety_modes.py`: make the owner/mode assertions
    host-neutral (add the `git ls-tree` sealed-mode check on every host; keep
    `st_uid`/`S_IMODE` on POSIX only).
  - `test_eval_tree_state.py`: extend the one fixture assertion at its
    extended-prefix line with the same helper.

## Interfaces & contracts

```python
def _set_index_modes(staging: Path, members: Sequence[tarfile.TarInfo]) -> None:
    """Set the Git index mode of every regular-file member from its archive
    mode, after `git add -A` and before the seal commit.

    Runs `git update-index --chmod=+x -- <paths>` for every regular member
    whose archive mode has `stat.S_IXUSR` set, and `git update-index
    --chmod=-x -- <paths>` for every regular member that does not - one call
    per group, paths taken from `member.name` (archive-domain, slash form,
    already validated by `_refuse_duplicate_or_crossing_members`), each
    group's call omitted entirely when its path list is empty - required, not
    cosmetic: `git update-index --chmod=+x --` with zero trailing paths is a
    usage error per `git-update-index(1)` (`--chmod` requires at least one
    path argument), not a silent no-op. Directories
    and symlinks carry no file mode in Git's index and are not passed to
    either call. Reads the bit only from `member.mode & stat.S_IXUSR`, never
    from anything on disk, so the sealed mode is independent of what the
    staging filesystem (POSIX file bits, or Windows ACLs that recognize no
    executable bit at all) happened to record during extraction.
    """

def _lay_links_typed(
    dest: Path, members: Sequence[tarfile.TarInfo], written: set[str]
) -> None:
    """Create every symlink member under `dest`, after every file and
    directory member already exists there (`written` holds every
    non-symlink member's slash-form name, already created by the caller).

    For each symlink member, in archive order:
      - `target = member.linkname.replace("/", os.sep)` - converted once and
        passed as-is to `os.symlink`, so the text that actually lands on disk
        (and that `os.readlink`/`_entry`'s manifest `target` field later
        reads back) is **host-separator form on Windows**, matching the
        PRD's own Risks section ("On Windows the stored text uses `\\`").
        Only the *archive* domain (member names, `member.linkname` itself,
        and every `_land`/`_archive_name_escapes`/escape-detection input)
        stays slash-form; nothing here claims the on-disk bytes do. Portable
        comparison against the archive's slash-form text is the read-back
        helper's job (`_extended_prefix_stripped` plus `Path(...).as_posix()`
        on the test side), never a property of what is written to disk.
      - `landing = _land(links, member.name)` where `links` is the
        `{normalized member name: linkname}` map for every symlink member
        (built once by the caller, same shape `_refuse_duplicate_or_crossing_members`
        already builds) - the member's own landing, followed through every
        hop of a chain, never a single join against the immediate target
        text. A one-hop join is wrong for a chain (`a -> b -> c`, `c` a
        directory): it would resolve only `a`'s own text and miss that `b`
        itself is a symlink to a directory, reproducing the exact
        CPython mistyping bug one hop removed. `_land` already walks the
        whole chain and already ran once for escape detection before this
        point, so this reuses that walk rather than adding a second one.
      - `target_is_directory = landing in written_dirs or (dest / landing).is_dir()`
        where `written_dirs` is the subset of `written` that are directory
        members, falling back to a disk check for a landing that is itself
        reached through an already-created earlier link in this same pass
        (a chain). This mirrors CPython's own rule (a link types as a
        directory only if its target already exists as one at creation
        time) but makes the check true regardless of member order, because
        every non-symlink member exists before any symlink does.
      - `os.symlink(target, dest / member.name, target_is_directory=target_is_directory)`.
    A dangling link (its landing names no member at all) gets
    `target_is_directory=False` and is created file-typed, same as today.
    `target_is_directory` is accepted on every host (CPython exposes the
    keyword everywhere; it is a no-op where the host OS has no file/directory
    symlink distinction).
    """

def _copytree_links_typed(template: Path, dest: Path) -> None:
    """Copy `template` to `dest`: every file and directory first
    (`shutil.copytree(template, dest, symlinks=True, ignore=<symlinks>)`,
    or an equivalent walk), then every symlink in a second pass using the
    same `target_is_directory` rule as `_lay_links_typed`, keyed off the
    **template's own on-disk layout** (a target already a directory in
    `template` lands as a directory in `dest` too, since the first pass
    already copied it). `fresh_clone` still calls `_refuse_escaping_links`
    on `template` before any copying, unchanged.
    """

def _remove_tree(path: Path) -> None:
    """Remove `path` and everything under it, clearing a read-only
    attribute once per unremovable entry and retrying it, so a Git object
    file Windows (or a POSIX read-only directory) refuses to unlink does
    not abort the removal.

    `shutil.rmtree(path, onexc=_clear_readonly_and_retry)` on Python >=3.12,
    `shutil.rmtree(path, onerror=_clear_readonly_and_retry_onerror)` on
    3.10/3.11 (selected once by `hasattr(shutil, "_USE_CB_SHUTIL_ONEXC")`
    is not reliable across patch versions - select by Python feature,
    `sys.version_info >= (3, 12)`, which both signatures document). The
    handler: `os.chmod(failing_path, stat.S_IWRITE)`, retry the original
    `func(failing_path)` once; if that retry also raises, re-raise the
    retry's exception (never swallow it, never the first exception - the
    retry's own failure is what the caller should see). No `ignore_errors`
    anywhere in this call chain. Replaces every
    `shutil.rmtree(staging, ignore_errors=True)` call site in
    `build_template` (the `except BaseException` cleanup and nowhere else -
    `fresh_clone` never removes a staging path).
    """

def _extended_prefix_stripped(text: str) -> str:
    """`text` with a leading Windows extended-length prefix removed: `\\\\?\\UNC\\`
    becomes `\\\\`, a leading `\\\\?\\` is dropped, anything else is returned
    unchanged (including every POSIX path and every already-short Windows
    path). Pure string rewrite - never touches the filesystem. Lives beside
    the fixture helpers in `test_eval_tree_links.py` (the module both
    affected assertions already import from) and is imported by
    `test_eval_tree_state.py` the same way `test_eval_tree_links` constants
    already cross that boundary (see `_outside_sentinel`, `_serve_archive`
    imports today).
    """
```

Call sites inside `build_template`:

```python
_git(staging, "add", "-A")
_set_index_modes(staging, archive.getmembers())   # new, before the dated commit
...
_git(staging, *IDENTITY, "commit", ...)
...
except BaseException:
    _remove_tree(staging)   # was: shutil.rmtree(staging, ignore_errors=True)
    raise
```

`_extract_without_filter` keeps its file/directory arm unchanged (mode is now
set from the index, not from the extracted file's own `os.chmod`, but the
directory/file writes stay as they are - only the **symlink arm** moves out of
the per-member loop):

```python
def _extract_without_filter(archive, dest, members):
    written = set()
    for member in members:
        if member.issym():
            continue
        ...  # unchanged dir/file handling; written.add(normalized name)
    _lay_links_typed(dest, members, written)
```

Two fixture call sites change from:

```python
assert os.readlink(root / "escape") == target
```

to:

```python
assert _extended_prefix_stripped(os.readlink(root / "escape")) == target
```

at `test_eval_tree_links.py:663` and `test_eval_tree_state.py:577`.

## Data flow

**Seal path (`build_template`):** archive bytes -> `tarfile` -> staging tree
(files/dirs via the existing per-member loop or `extractall(filter="data")`;
when the per-member loop is used, symlinks are laid in a second pass by
`_lay_links_typed` - `extractall(filter="data")` already passes today and is
untouched) -> `git add -A` ->
`_set_index_modes` rewrites the index's own file-mode bits from the archive,
independent of what landed on disk -> dated commit -> rename to `dest`. On
any failure the `except BaseException` arm now calls `_remove_tree`, which
clears read-only attributes before retrying the delete.

**Clone path (`fresh_clone`):** `_refuse_escaping_links` walks the template
(unchanged) -> `_copytree_links_typed` copies every file/dir first, then lays
every symlink typed from the template's own disk state.

`_entry` (`eval_harness/trees.py:359`) is untouched by this PRD and keeps
reading `os.readlink` raw into the manifest's `target` field: that field is
deliberately host-form, not cross-host-portable text - the contract is
template-and-clone consistency on one host (both written by this same code,
so they always agree), never a promise that a Windows manifest's `target`
matches a POSIX one byte-for-byte. `prove_state`'s manifest comparison (the
only consumer) only ever compares two manifests captured on the same run, so
this is not a regression this PRD introduces.

**Read-back path (tests only):** `os.readlink` -> (new) strip an extended
prefix -> compare to the fixture's original text. Production code (`_land`,
`contained`, `_refuse_escaping_links`) never calls `os.readlink` through this
helper; they already read archive-domain text or `os.readlink`'s raw return
and compare it against `_archive_name_escapes`'s own backslash/colon rules,
which already reject every Windows-shaped form before an extended prefix
would ever appear in that comparison.

## Reuse inventory

- `trees._git` / `trees.IDENTITY` (`eval_harness/trees.py:45,25`) - reused
  verbatim for the `git update-index` calls; no new subprocess wrapper.
- `trees._archive_name_escapes` / `trees._land` (`eval_harness/trees.py:114,82`)
  - reused unchanged to compute a symlink member's own landing inside
  `_lay_links_typed`; no new escape-detection logic is written.
- `trees._walk` (`eval_harness/trees.py:69`) - `_copytree_links_typed`'s file
  /directory pass can walk the template with this existing helper rather than
  a second copy of its `.git`-skipping logic.
- `shutil.rmtree`'s `onexc`/`onerror` hooks (stdlib) - reused as the retry
  mechanism; no custom tree-walking deletion is written.
- `os.symlink(..., target_is_directory=...)` (stdlib, documented as a no-op
  off Windows) - reused directly; no per-host branch is needed in the
  production call site itself.
- Greps tried: `rg "chmod.*-x|update-index" skills/` (nothing - no existing
  index-mode helper); `rg "ignore_errors|onexc|onerror" skills/use-qwen`
  (only the one `shutil.rmtree(..., ignore_errors=True)` this PRD replaces);
  `rg "extended.prefix|\\\\\\\\\\?\\\\\\\\" skills/use-qwen` (nothing - no
  existing prefix-stripping helper); `rg "target_is_directory" skills/`
  (nothing - no existing typed-symlink helper).

## Alternatives considered

1. **Chosen: index-mode write via `git update-index --chmod`, two-pass typed
   symlinks, `onexc`-based cleanup retry.** Fixes all three product causes
   (3, 4, 5) at their root without touching extraction order for files, and
   without adding a new dependency.
2. **Smallest-diff alternative: `git config core.filemode false` plus a
   post-seal `git update-index --chmod` pass driven by `git ls-tree` instead
   of archive members.** Rejected: reading modes back from `git ls-tree`
   after `git add -A` already recorded them wrong is circular - the index
   never held the right bit to read back. The chosen design sets the bit
   from the archive member, the one place it is known correct, which is no
   larger a diff (same call shape) and avoids the circularity.
3. **Alternative for links: resolve the whole archive's link graph first
   (topological sort) and extract strictly dependency-first.** Rejected as
   larger-diff for no behavior gain: the two-pass split (all non-links, then
   all links) already guarantees every link's intra-archive target exists
   first, with no graph or cycle analysis needed beyond what `_land` already
   does for escape detection.
4. **Alternative for cleanup: `tempfile.TemporaryDirectory` with its own
   Windows-aware cleanup.** Rejected: would restructure `build_template`'s
   staging-path naming (today `dest.parent / (dest.name + ".staging-" +
   random)`, asserted on by `test_eval_tree_archive_staging.py`'s sibling
   checks) for a stdlib feature that itself only gained `ignore_cleanup_errors`
   in 3.10 and still has no retry-after-chmod behavior - `onexc` solves the
   same problem with a smaller diff.

## Risks & edge cases

- **Native behavior is inferred** (PRD's own risk): the two-pass link order
  and the `onexc` retry are designed from the CI log evidence; only the
  hosted Windows run proves them. No change here reduces that risk further
  than running CI.
- **A symlink chain inside the second pass** (`a -> b -> c`, `c` a directory):
  `_lay_links_typed` creates links in archive member order, so `b` may not
  exist as a symlink yet when `a` is typed. The contract above computes
  `a`'s landing with `_land` through the *full link map* (chain included),
  not by joining `a`'s own one-hop text or by checking a partially-created
  `b` on disk - so `a` is typed as a directory correctly regardless of
  creation order, and this needs no retry pass.
- **Likely next changes:** (1) applying the same `target_is_directory` typing
  rule inside `apply_patch`'s `git apply` if a future change teaches the
  harness to write symlinks there too - this design keeps the rule in one
  importable place (`_lay_links_typed`'s inner logic), not inlined twice;
  (2) extending `_set_index_modes` to other index attributes (e.g. a future
  `core.symlinks=false` host) - the helper's archive-mode-only contract
  leaves room for that without a rewrite.
- **Boxed-in by this design:** none identified beyond the above - the two new
  private helpers are pure functions over already-validated member lists and
  do not introduce new state.

## Test strategy outline

- **Regressions first (Phase 0, all platforms):** a `os.symlink` spy in
  `test_eval_tree_links.py` recording `(target_is_directory, target_text)`
  per call, run against a fixture ordered so a link precedes its directory
  target - fails today (wrong `target_is_directory`, or the old separator).
  A second link regression covers a **chain landing on a directory through
  an intermediate symlink** (`a -> b`, `b -> c`, `c` a directory, laid in
  archive order `a, b, c` so both links precede both their eventual
  directory landing and each other): asserts `a` is still typed
  `target_is_directory=True`, catching a one-hop (non-`_land`) landing
  computation that resolves only `a`'s immediate text.
  A `core.filemode=false`-forced seal in `test_eval_tree_archive_safety.py`
  expecting `100755` - fails today (bit already lost before this PRD, lost
  worse once the environment forces the git config that exposed it on CI).
  A staging test that chmods a file read-only inside `staging` before the
  seal commit raises, then asserts no `template.staging-*` sibling survives
  - fails today only when run on a host that honors read-only on delete; the
  regression therefore also monkeypatches `os.unlink`/`os.rmdir` to raise
  `PermissionError` for the read-only path on POSIX, so the test is
  host-independent.
- **Fixes (Phase 1):** each regression above passes; every existing test in
  the five modules keeps passing unchanged on Linux/macOS (no assertion
  count or strength change outside the two files this PRD explicitly edits).
- **Host-neutral checks (Phase 2):** `test_eval_tree_archive_safety_modes.py`
  gains a `git ls-tree` mode assertion run on every host; its `st_uid`/
  `S_IMODE` assertions are wrapped to run only where `os.getuid`/the real
  mode bits are meaningful (POSIX), gated by `sys.platform != "win32"` or
  `hasattr(os, "getuid")` rather than a whole-test `skipif`, per the PRD.
  The extended-prefix helper gets its own direct unit test
  (`\\?\C:\x`, `\\?\UNC\h\s\x`, `C:\x`, a POSIX path) before the two fixture
  call sites are updated to use it.
- **Native proof:** the hosted Windows CI job, unchanged test selection,
  all 72 previously-failing nodes in the five modules green.

## Review log

- non-blocker: PRD's symbol list (`_lay_links_typed`, `_remove_staging`) names fewer/differently-named symbols than this design's Module placement section (`_remove_tree`, `_set_index_modes`, `_copytree_links_typed`, `_extended_prefix_stripped`). Not fixed - the design's symbol list is the complete and correct source; a PRD wording update is out of scope for this doc.
dispatch 1 (claude): cardinal-sin 0, blocker 1, non-blocker 1, question 1
- non-blocker: if `_remove_tree`'s own retry fails, the new exception becomes the headline error (original cause demoted to `__context__`). Not fixed - out of this PRD's acceptance criteria (which test cleanup success, not double-failure); a future PRD on failure-reporting ergonomics can revisit.
- question: the `(dest / landing).is_dir()` disk-state fallback in `_lay_links_typed`'s `target_is_directory` rule may be unreachable, since `_land` already resolves a landing through the full link map before any symlink is created and every non-symlink member exists first - `landing in written_dirs` may already cover every real case. Left in the design as a defensive fallback (harmless if dead) rather than removed, since proving it unreachable for every archive shape is itself nontrivial and the cost of keeping it is one `or` clause.
dispatch 2 (claude-fallback): cardinal-sin 0, blocker 1, non-blocker 1, question 2
- non-blocker: Data flow's seal-path sentence read as if `_lay_links_typed` applies to both extraction branches; reworded to scope it to the per-member loop only (`extractall(filter="data")` is untouched).
dispatch 3 (claude-fallback): cardinal-sin 0, blocker 0, non-blocker 1, question 0
