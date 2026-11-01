# Design: Seal templates only from archives that cannot write outside the template

## Architecture fit

All work lands in `skills/use-qwen/scripts/eval_harness/trees.py`, the single
module that already owns template sealing (`build_template`), cloning
(`fresh_clone`), and containment (`contained`, `hash_paths`). No new module is
introduced: the PRD's four open findings (00155-00158) are all defects inside
this file's existing functions and the private helpers they call
(`_land`, `_refuse_duplicate_or_crossing_members`, `_refuse_escaping_links`,
`contained`). PRD 00131 already landed the duplicate/ancestor/cycle logic in
`_land` and `_refuse_duplicate_or_crossing_members` (commit `147d146`); this
PRD closes the remaining gaps in the same call graph rather than replacing it.

The harness-wide invariant this module exists to enforce — "nothing here
trusts a path a task hands over" (module docstring) — gains three refinements:
the ancestor check must see archive members that land *beneath* a symlink,
not only the symlink itself (00158); the no-filter extraction path must apply
the same byte-and-mode-only policy `data_filter="data"` applies (00156/00157);
and the read-side containment check (`contained`, used by `hash_paths`) must
resolve through the same hop-by-hop link walk `_land` already uses for
write-side containment, rather than through `Path.resolve()`, which the
Windows evidence shows diverges from it in native-separator and dangling-link
cases (00158's Q4/Q5 addendum).

## Module placement

All changes are edits to existing files. One new test file is added.

- **Edit** `skills/use-qwen/scripts/eval_harness/trees.py`:
  - `_land` — extend the single-hop escape logic so that, at every hop where
    it already looks up `links[landing]`, it refuses the resolved `target`
    via `_archive_name_escapes(target)` **in addition to** the existing
    `os.path.isabs(target)` check — this is the one and only place the
    archive-domain predicate is wired into target-following, so both the
    write-side ancestor walk and the read-side `contained` walk (both of
    which call `_land`) gain Windows-shaped-absolute detection for free, with
    no duplicated logic. (Superseded the earlier phrasing that left `_land`
    "unchanged" — see "Interfaces & contracts" below for why that was wrong.)
  - `_refuse_duplicate_or_crossing_members` — add the archive-domain
    pre-check over every member's own `name` (`_archive_name_escapes`, which
    catches an absolute *member name* with no symlink involved at all — a
    case `_land`'s target-following extension above does not cover, since a
    member name is never a "target"); add the ancestor-crossing check
    (00158, algorithm specified below); add the case-collision check
    (00158's A5). Device/FIFO/hardlink refusal (00158's A6) needs **no new
    runtime code**: `member.isfile() or member.isdir() or member.issym()`
    (trees.py:145-146) already rejects every other type today — A6's
    obligation here is a dedicated regression test proving it, not a new
    guard.
  - `build_template` — replace the bare `archive.extractall(dest)` fallback
    with `_extract_without_filter` (00156/00157); add staged extraction into
    a sibling temp directory with atomic rename on success (00158's A9); add
    the pre-existing-`dest`-exists guard; **delete** the current unconditional
    `dest.mkdir(parents=True, exist_ok=True)` (trees.py:174) — left in place,
    it would make `dest` exist by the time the new guard runs on every call,
    firing the guard unconditionally. `staging.mkdir(parents=True)` (already
    specified) takes over creating `dest.parent` when needed.
  - `contained` — resolve through `_land`-style hop walking instead of
    `Path.resolve()`, so `hash_paths` and `fresh_clone`'s callers share one
    containment algorithm with `build_template` (00158's Capability: Read
    containment, A11).
  - New private helpers: `_archive_name_escapes(name_or_target: str) -> bool`,
    `_ancestor_crossing(members, links) -> None`,
    `_extract_without_filter(archive, dest, members)`, `_safe_mode(mode: int) -> int`.
- **Edit** `skills/use-qwen/scripts/test_eval_tree_links.py`:
  - `_lay_links` — pass `target_is_directory=True` when the link's target is
    a directory, so Windows reparse points are typed correctly (00158's
    Q4/Q5 hypothesis).
- **Edit** `skills/use-qwen/scripts/test_eval_tree_state.py`:
  - add the absolute-target parametrization (POSIX-rooted, Windows-rooted,
    drive, UNC) to the existing symlink-escape test, asserting `TreeError`
    specifically (never tarfile's `LinkOutsideDestinationError`).
- **New** `skills/use-qwen/scripts/test_eval_tree_archive_safety.py`:
  the A1-A12 acceptance matrix, parametrized over the filter-present and
  filter-absent seams, reusing `_crafted_tar`, `_serve_archive`,
  `_hide_data_filter`, `_outside_sentinel` from `test_eval_tree_links.py`
  (imported, not duplicated).

## Interfaces & contracts

```python
def _archive_name_escapes(text: str) -> bool:
    """True iff `text` (a member name or a symlink target, archive-domain
    text — never a host path) names or reaches outside a tree root under
    either the POSIX or the Windows path-reading rules.

    Refuses, independent of the host OS:
      - POSIX-absolute: starts with "/".
      - Drive-absolute: matches `^[A-Za-z]:[/\\\\]`  (e.g. "C:\\x", "C:/x").
      - Drive-relative: matches `^[A-Za-z]:[^/\\\\]` (e.g. "C:x") — no
        leading separator after the drive letter.
      - Rooted backslash: starts with "\\" but is not a UNC/extended prefix
        below.
      - UNC: starts with "\\\\" followed by a non-"?"/"." component
        (`\\\\host\\share`).
      - Extended-length prefixes: starts with "\\\\?\\" or "\\\\.\\".
      - NTFS stream-like: a path component containing ":" after position 0
        that is not the drive-letter colon already matched above (catches
        `name:stream`).
      - **Any backslash at all**, anywhere in the text: `"\\" in text`.
        `_land` (below) splits only on `/` (`Path(path).as_posix().split("/")`,
        trees.py:92), so a name like `sub\\..\\..\\outside\\file` is one
        opaque component to it — no `/` means no `..`-climb is ever seen —
        yet on an actual Windows filesystem `\\` **is** a separator, so the
        OS-level write this member eventually causes would climb for real.
        Refusing any embedded backslash outright closes this without
        teaching `_land` a second separator grammar: the PRD's own
        justification for the ancestor rule's narrowing applies here too —
        `git archive` never emits a backslash-separated member name or
        symlink target.
    Does not itself walk `..` segments — that stays `_land`'s job. Called
    from two places: (1) `_refuse_duplicate_or_crossing_members`, once per
    member, against `member.name` (and, when `member.issym()`, also
    `member.linkname`) — this is what catches an absolute **member name**
    with no symlink dereference involved; and (2) from inside `_land`
    itself (see `_land`'s entry in "Module placement" above), against every
    symlink `target` text at the point `_land` already looks it up mid-walk
    — this is what makes the read-side `contained` walk, which calls `_land`
    but never touches archive members directly, inherit the same
    archive-domain absolute-target detection with no separate wiring. The
    two call sites are not redundant: (1) never resolves a chain, so it
    cannot see a target reached only after following an earlier link; (2)
    never sees a member's own top-level name, only targets reached through
    `links`. Both are required.
    """

def _ancestor_crossing(members: Sequence[tarfile.TarInfo], links: dict[str, str]) -> None:
    """Refuse any member whose path has an archive symlink as a proper
    ancestor, judged on where that symlink itself *lands* — not on whether
    its raw name textually prefixes the member's name (00158).

    `links` is the existing `{normalized member name: linkname}` map
    `_refuse_duplicate_or_crossing_members` already builds. The worked
    example this closes: `pkg/`, `alias -> pkg`, `alias/escape ->
    ../../outside`, `pkg/escape/secret.txt`. `alias/escape` is a symlink
    whose *own* location, once its ancestor `alias` is resolved, is
    `pkg/escape` — the same disk entry `pkg/escape/secret.txt`'s own parent
    directory names. Writing `pkg/escape/secret.txt` after `alias/escape`
    was extracted as a symlink to `../../outside` would write through that
    symlink, because `alias` and `pkg` are the same directory on disk.

    Algorithm — operates on each member's **raw, un-normalized** `member.name`
    throughout, never `posixpath.normpath(member.name)`: normalizing first
    would collapse a `..` segment before any symlink in that same name gets
    a chance to redirect it, which is exactly the mistake
    `_refuse_duplicate_or_crossing_members`'s own docstring already warns
    against for its sibling landing-collision check ("a name normalized
    ahead of the walk... throws away the very hop through `alias` that
    `_land` exists to judge," trees.py:130-134) — this helper must follow
    that same existing precedent, not reintroduce the mistake:
      1. For every symlink member, compute its own real location by
         splitting its **raw** name on `/` (the same split `_land` itself
         does — `Path(member.name).as_posix().split("/")`), resolving every
         segment but the last one through `_land` (so any symlink earlier
         in the symlink's own path redirects it), then joining the final
         segment: `own_landing = posixpath.join(_land(links, "/".join(segments[:-1])), segments[-1])`.
         Collect these into `symlink_landings: set[str]`.
      2. For every member (symlink or content), for every proper ancestor
         prefix of its **raw** name (every prefix of `member.name`'s `/`-split
         segments, shortest first, excluding the full name itself — i.e.
         `"/".join(segments[:k])` for `k` from 1 to `len(segments) - 1`):
         compute `_land(links, prefix)` and check it against
         `symlink_landings`. A match raises
         `TreeError("%s is beneath an archive symlink" % member.name)`.
    Tracing the worked example: `pkg/escape/secret.txt`'s raw ancestor
    prefixes are `pkg` and `pkg/escape`. `_land(links, "pkg")` = `"pkg"` (no
    hop) — not in `symlink_landings`. `_land(links, "pkg/escape")` =
    `"pkg/escape"` (still no hop: `links` has no key `pkg/escape`, only
    `alias/escape`) — but `symlink_landings` DOES contain `"pkg/escape"`
    (step 1, from `alias/escape`'s own resolved location) — match, refused.
    A second trace showing why raw text matters: archive has `alias ->
    deep/nested/dir` (a legal, non-escaping symlink reaching several levels
    down), `deep/nested/escape -> ../../outside` (legal on its own — it
    climbs back to `deep`, still inside), and a crafted member literally
    named `alias/../escape/secret.txt`. On extraction this member's write
    really does walk `alias` (→ `deep/nested/dir`) then `..` (→
    `deep/nested`) then `escape` (→ `deep/nested/escape`, the outside-
    reaching symlink) — an escape. Normalizing the member name first would
    collapse it to `escape/secret.txt` before any of that walk runs, and
    would then find no match (no top-level symlink literally named
    `escape`); walking the raw, un-normalized name through `_land` (as
    specified above) performs exactly the hop sequence just traced and
    refuses it correctly.
    Called from `_refuse_duplicate_or_crossing_members`, after the existing
    per-member duplicate/landing-collision loop, over the same `members`
    and `links` it already has in scope.
    """

def _extract_without_filter(
    archive: tarfile.TarFile, dest: Path, members: Sequence[tarfile.TarInfo]
) -> None:
    """Extract `members` into `dest` with the same policy `filter="data"`
    applies, for a tarfile build with no `data_filter` attribute at all.

    For each member, in archive order:
      - `isdir()`: `dest.joinpath(member.name).mkdir(parents=True, exist_ok=True)`,
        then `os.chmod(path, _safe_mode(member.mode))`.
      - `isfile()`: parent dirs created, bytes copied from
        `archive.extractfile(member)`, then `os.chmod(path, _safe_mode(member.mode))`.
      - `issym()`: `os.symlink(member.linkname, path)` — target text written
        verbatim, never resolved or rewritten (mirrors `data_filter`, which
        also preserves symlink text).
      - any other type: unreachable here — `_refuse_duplicate_or_crossing_members`
        already refused it before `build_template` calls this helper.
    Ignores `member.uid`, `.gid`, `.uname`, `.gname` entirely: never calls
    `os.chown` or any uid/gid-setting API (A7).
    Wraps every `OSError` raised during a single member's write in
    `TreeError(f"{member.name}: {cause}")`, chaining the cause
    (`raise ... from cause`) (A10). `tarfile.FilterError` cannot be raised by
    this path (it has no filter), so it is not caught here — `data_filter`'s
    own `FilterError` is instead caught around the `filter="data"` call site
    in `build_template`, translated to `TreeError` the same way (A10).
    """

def _safe_mode(mode: int) -> int:
    """`mode & ~(stat.S_ISUID | stat.S_ISGID | stat.S_ISVTX | stat.S_IWGRP | stat.S_IWOTH)`
    — setuid, setgid, sticky, and group/other *write* bits stripped; every
    other bit (owner read/write/execute, group/other read/execute) passed
    through unchanged. This is the PRD's own A7 wording, verbatim ("strips
    setuid, setgid, sticky and group/other write bits, and keeps owner
    read/write and the executable bit") — it is **not** a claim of bit-for-
    bit parity with CPython's actual `tarfile.data_filter` internals, which
    are materially different and more involved (verified against the
    installed interpreter's `tarfile._get_filtered_attrs`): that function
    also unconditionally forces owner read+write on (`mode |= 0o600`),
    clears *all* executable bits when the owner's own executable bit is
    unset (`mode &= ~0o111` — not only group/other), and sets `mode = None`
    (no explicit mode at all) for directories and symlinks, leaving tarfile's
    own default extraction behavior to apply. The PRD does not ask this
    helper to reproduce those internals; it defines the no-filter path's
    mode policy directly, as its own acceptance criterion (A7), and this
    formula satisfies that criterion exactly. True bit-for-bit parity with
    `data_filter` is explicitly out of scope — the PRD's A7 text is the
    source of truth here, not `data_filter`'s implementation.
    """
```

`build_template`'s own signature, and `hash_paths`/`fresh_clone`/`contained`'s
signatures, are **unchanged** (PRD "Module: trees" § Exports). `build_template`
gains internal staging:

```python
def build_template(repo: Path, first: str, dest: Path) -> str:
    """... (docstring gains one paragraph on staging/atomicity) ...

    Raises TreeError, and leaves `dest` exactly as it was, if anything —
    a file, a directory (empty or not), or a dangling symlink — already
    sits at `dest` before extraction starts.
    """
```

Staging mechanics (Feature: Staged, atomic template exposure):
- `os.path.lexists(dest)` → `raise TreeError(f"{dest} already exists")`
  before any extraction, **whether or not it is empty, and whether or not
  it is a dangling symlink**. `lexists` (not `Path.exists`/`dest.exists()`)
  is required specifically for the dangling-symlink case: `Path.exists()`
  follows symlinks and returns `False` for a symlink whose target is
  missing, even though a real filesystem entry named `dest` is there — a
  guard built on `exists()` would let a stale dangling-symlink `dest` (left
  behind by, e.g., an interrupted prior run, or any unrelated process) pass
  through unflagged, and the final `staging.rename(dest)` would then
  silently unlink and replace that symlink entry rather than performing the
  create-only rename this design relies on. `lexists` sees the symlink
  entry itself regardless of where (or whether) it points, closing that
  gap. An existing-but-empty `dest` is refused too, for an unrelated
  reason: `Path.rename`/`os.replace` onto an existing directory is not a
  portable atomic replace (POSIX allows replacing an empty directory;
  Windows does not allow replacing a directory at all, empty or not), and
  Windows CI is explicitly in scope for this PRD. Requiring `dest` to be
  wholly absent (in the `lexists` sense) before the call makes the final
  rename a plain create-only rename on every supported platform, with no
  platform-conditional code path to maintain.
- Extraction target becomes `staging = dest.parent / (dest.name + ".staging-" + os.urandom(4).hex())`,
  created fresh by this call (`staging.mkdir(parents=True)` — fails loudly if
  it already exists, which `urandom`-based naming makes practically
  impossible, not raced-with-itself).
- Validate members (`_refuse_duplicate_or_crossing_members`), extract into
  `staging` (filtered or `_extract_without_filter`), run the existing
  `git init` / `git add -A` / `git commit` seal sequence against `staging`.
- On any exception during validation, extraction, or the seal commit: if
  `staging` exists, `shutil.rmtree(staging, ignore_errors=True)`; re-raise
  (or re-raise as `TreeError` per the existing translation rules). `dest`
  itself is never created or touched on this path — the existence guard
  above has already confirmed there is nothing at `dest` to disturb.
- On success: `staging.rename(dest)`. `staging` is created from
  `dest.parent`, so this is a same-filesystem rename, and because the
  `lexists` guard already confirmed nothing — file, directory, or dangling
  symlink — sits at `dest`, it is a create-only rename — atomic and
  portable on POSIX and Windows alike (the platform divergence above
  applies only to replacing an *existing* `dest`, which this design never
  does). Return `head_sha(dest)` (unchanged).
- A caller that needs the old "merge into a non-empty `dest`" behavior does
  not exist today (`build_template`'s only caller always passes a fresh
  per-task `dest`); the guard tightening above is a narrowing of accepted
  input, not a removal of a behavior anything currently relies on. The
  TOCTOU between this existence check and the final rename (a concurrent
  second `build_template(..., dest)` call racing this one) is recorded as a
  known edge case, not fixed here — see Risks & edge cases.

## Data flow

```
build_template(repo, first, dest)
  -> _git_bytes(repo, "archive", ...)              # unchanged: read the tar bytes
  -> tarfile.open(fileobj=...)                     # unchanged
  -> archive.getmembers()                          # unchanged
  -> _refuse_duplicate_or_crossing_members(members) # extended: ancestor-cross,
                                                     # case-collision, device/FIFO
       -> _land(links, member.name)                 # extended: _archive_name_escapes
                                                      # checked before the `..`/cycle walk
  -> [NEW] non-empty-dest guard
  -> [NEW] staging = fresh sibling dir
  -> callable(getattr(tarfile, "data_filter", None))
       True  -> archive.extractall(staging, filter="data")   # unchanged call,
                 wrapped in try/except FilterError/OSError -> TreeError
       False -> _extract_without_filter(archive, staging, members)  # NEW,
                 replaces bare extractall(dest)
  -> git init / add -A / commit  (against staging, not dest)  # unchanged internals
  -> [NEW] staging.rename(dest); on any prior failure, rmtree(staging)
  -> head_sha(dest)                                 # unchanged

hash_paths(root, paths) / contained(root, relpath)
  -> os.path.isabs(relpath) check                   # UNCHANGED — kept exactly
                                                      # as today (trees.py:275-276);
                                                      # _land's own hop loop treats a
                                                      # leading "/" as a no-op segment,
                                                      # not a refusal, so this guard
                                                      # cannot be dropped
  -> [CHANGED] walk root's symlinks into a links map (reuse _walk, same as
     _refuse_escaping_links already does for fresh_clone)
  -> [CHANGED] _land(links, relpath) to find the real landing, raising
     TreeError on escape/cycle/absolute-target (now including the
     Windows-shaped-target case, via _land's _archive_name_escapes addition
     above) — replaces `destination.resolve().is_relative_to(...)`
  -> _digest(landing) as before
```

No new data enters or leaves the module's boundary: the inputs (`repo`,
`first`, `dest`, `root`, `paths`) and outputs (`str` sha, `dict[str, str]`
digests, or a raised `TreeError`) are exactly what the PRD's "Module: trees"
section already declares.

## Reuse inventory

- `_land(links, path, active)` (trees.py:82) — already implements hop-by-hop
  symlink-chain resolution with cycle and `..`-past-root detection. **Reused
  with one addition**: at the point it already evaluates `target = links[landing]`
  (trees.py:105), it also refuses `_archive_name_escapes(target)`, alongside
  the existing `os.path.isabs(target)` check. This single change is what
  makes BOTH callers — the archive ancestor walk (via `_ancestor_crossing`
  and the existing per-member landing loop, both of which call `_land`) and
  the rewritten `contained` (below, which also calls `_land`) — gain
  Windows-shaped-absolute-target detection without each needing its own
  copy of the check. `_archive_name_escapes`'s *other* call site (directly
  over `member.name`, from `_refuse_duplicate_or_crossing_members`) covers
  the case `_land`'s extension cannot: an absolute member name with no
  symlink dereference involved at all.
- `_walk(root)` (trees.py:69) — already yields every non-`.git` path as
  (relpath, Path); reused to build the links map `contained` needs, the same
  way `_refuse_escaping_links` (trees.py:114) already builds one.
- `_refuse_duplicate_or_crossing_members` (trees.py:125) — already classifies
  members, refuses absolute/non-file-dir-symlink members, duplicates, and
  (via `_land`) same-landing collisions. Extended in place, not duplicated,
  for the ancestor-crossing and case-collision rules.
- `test_eval_tree_links.py`'s `_crafted_tar`, `_serve_archive`,
  `_hide_data_filter`, `_outside_sentinel`, `DIRECTORY`, `PAYLOAD` — already
  build and serve crafted tar fixtures over both filter seams. Imported into
  the new `test_eval_tree_archive_safety.py` rather than re-implemented.
- Greps tried confirming no other tar/zip extraction exists in the repo to
  consolidate with: `rg "extractall|tarfile\.open|data_filter" --type py`
  (only `trees.py` and its two test files); `rg "zipfile" --type py` (nothing
  under `skills/use-qwen/`). `trees.py` is the sole archive-extraction surface.

## Alternatives considered

1. **Smallest-diff option: patch only the four named defects in place**
   (fix `_land`'s ancestor miss, swap `extractall` for a minimal manual
   loop, suppress the warning, add tests) with no staging/atomicity change.
   Rejected as the sole change because A9 (staged, atomic exposure) is an
   explicit PRD acceptance row with its own failure-injection tests; skipping
   it would leave a failed `build_template` capable of leaving a half-written
   `dest` behind, which is exactly what two of the PRD's open findings already
   describe. Still the right *shape* for the other three findings — no new
   module, no new public functions — which the chosen design keeps.
2. **Rewrite extraction as a validate-then-copy-tree approach**: extract to a
   scratch dir with Python's own filter disabled, build the tree in memory,
   then walk and write validated bytes. Rejected: it re-derives the file-type
   and mode semantics `tarfile.data_filter` already implements correctly on
   the filter-present seam, doubling the surface that has to agree with it,
   for no behavior the simpler member-by-member `_extract_without_filter`
   does not already provide.
3. **Chosen: extend the existing four functions in place, add two small
   internal helpers (`_extract_without_filter`, `_safe_mode`) and one
   archive-domain predicate (`_archive_name_escapes`), add staging around the
   existing seal sequence.** This is alternative 1 plus the A9 staging it was
   missing — the extra size (the staging directory and its rename) buys the
   one acceptance row that a smaller diff cannot satisfy, and nothing else
   grows the public surface or adds a new module.

## Risks & edge cases

- **Windows link typing differs from POSIX** (inherited from the PRD's own
  Risks section): `_lay_links`'s `target_is_directory=True` fix is a
  hypothesis verified only by the hosted Windows CI job, not locally. If the
  hosted run still shows the same symlink-readback failures after this fix,
  the next likely cause is `os.symlink`'s Windows requirement for the
  `SeCreateSymbolicLinkPrivilege` or Developer Mode on the runner image,
  which is outside this module's control — record that as a further finding
  rather than iterating blindly on `_lay_links`.
- **The ancestor rule's deliberate narrowing** (inherited from the PRD): a
  hand-built archive with a member literally named `alias/escape` where
  `alias` is a symlink is refused even though some tar tools could in
  principle construct and accept such a layout; `git archive` of an ordinary
  repository never emits one, which is the PRD's own justification. Likely
  next change #1: a future PRD may need to relax this if a legitimate
  `git archive --add-virtual-file` or submodule-rewrite workflow starts
  producing such members — this design does not box that in, since the
  ancestor check (`_ancestor_crossing`) is one isolated helper called from
  `_refuse_duplicate_or_crossing_members`; it is `_archive_name_escapes`,
  not the ancestor rule, that is threaded into `_land` (see "Module
  placement"), and relaxing the ancestor rule alone leaves that untouched.
- **`_archive_name_escapes`'s Windows-shaped checks run unconditionally on
  every host**, including POSIX CI and POSIX developer machines, because
  `git archive` output is platform-independent text and a POSIX-built
  archive can still contain a member crafted to look Windows-absolute.
  Likely next change #2: if this predicate's false-positive rate on *valid*
  archives ever surfaces (e.g. a real file legitimately named with a colon
  on a POSIX filesystem), the fix is narrowing the NTFS-stream heuristic, not
  removing the Windows branch — removing it would reopen 00158's Q6 symptom.
- **Staging directory naming** uses `os.urandom(4).hex()` for uniqueness
  rather than `tempfile.mkdtemp`, so that the staging dir is guaranteed to
  share `dest.parent`'s filesystem (required for the atomic rename). Likely
  next change #3: if `build_template` is ever called concurrently for the
  same `dest` from multiple processes, a collision is still astronomically
  unlikely but not provably impossible; `mkdir`'s own `FileExistsError` would
  surface it as a `TreeError`-translated failure rather than silent
  corruption, which is an acceptable degradation, not a fix owed by this PRD.
- **`contained`'s behavior change**: switching from `Path.resolve()` to a
  `_land`-based walk changes behavior for a `root` that is itself reached
  through a symlink from the caller's cwd, or for a `relpath` that does not
  exist yet (a legal case per `contained`'s own docstring — "a path the tree
  does not hold yet is legal"). The implementation must call `_land` with the
  links map built from `root`'s *own* tree only (via `_walk(root)`, which
  reads real directories, never resolving `root` itself through `Path`), and
  `_land` must already accept a target path with no existing file at the
  final component (it does — `_land` is a text/link walk, never a filesystem
  existence check) — verified by the existing
  `test_contained_answers_for_a_destination_the_tree_does_not_hold_yet` test,
  which the new implementation must keep passing unchanged.

## Test strategy outline

- **Phase 0** (`test_eval_tree_archive_safety.py`, new): the A1-A7, A12
  matrix, each case parametrized over `("with-data-filter", "without-data-filter")`
  via the existing `_hide_data_filter` monkeypatch fixture pattern, each with
  an `_outside_sentinel` asserted byte-and-mode-unchanged after the call.
  Includes a deliberate no-filter seam (module docstring's own description:
  delete `tarfile.data_filter` and make the local `TarFile.extractall`
  double reject the `filter` keyword) so a regression that quietly re-adds
  a bare `extractall(dest)` call fails loudly rather than happening to work
  because the test's own tarfile build still has `data_filter`. Plus valid-
  input controls: binary and CRLF blobs, an executable bit, file/dir/
  dangling safe links, root and subdirectory link chains, and a determinism
  check (`build_template` twice on the same input, same `head_sha`).
- **Phase 1**: extend `test_eval_tree_links.py` and `test_eval_tree_state.py`
  in place for A1-A10 (ancestor/collision/case/type refusal; no-filter mode
  stripping and chown-never-called via a `monkeypatch.setattr(os, "chown", ...)`
  spy that raises if called; `-W error::DeprecationWarning` run over both
  link/state files as its own CI-shaped check, not only a unit assertion).
  Includes the PRD's own worked example (`alias -> pkg`, `alias/escape ->
  ../../outside`, `pkg/escape/secret.txt`) as a named `_ancestor_crossing`
  regression, and a member named with an embedded backslash
  (`sub\\..\\..\\outside\\file`) as a named `_archive_name_escapes`
  regression, each refused on both filter seams.
- **Phase 2**: extend `test_eval_tree_links.py`'s `hash_paths`/`fresh_clone`
  tests for A11 (containment via the shared `_land` walk) and add the
  absolute-target `TreeError`-not-`LinkOutsideDestinationError` parametrized
  case (POSIX-rooted, Windows-rooted, drive, UNC) to
  `test_eval_tree_state.py`'s existing `test_build_template_refuses_a_source_tree_whose_symlink_leaves_it`.
  A test added to `_lay_links`'s call sites asserts the fixture link actually
  reaches its sentinel (readback) *before* asserting any refusal, per the
  PRD's own Phase 2 acceptance wording — this catches the Windows symlink-
  typing regression at its source instead of only at the refusal boundary.
- **Regression-bites check**: for every A-row test, the design requires that
  deleting the specific guard it exercises (the ancestor check, the mode
  stripping, the `_archive_name_escapes` call, the staging rename) makes that
  test fail — this is the PRD's own Success Metric 2 and is verified by hand
  during review (temporarily comment out the guard, confirm red, revert)
  rather than by an automated mutation step.
- Full gate: `uv run pytest skills/use-qwen/scripts/test_eval_tree_links.py skills/use-qwen/scripts/test_eval_tree_state.py skills/use-qwen/scripts/test_eval_tree_archive_safety.py -W error::DeprecationWarning` under `uv run --python 3.10`, `--python 3.12`, `--python 3.13`.

## Review log

- non-blocking: `_walk` excludes `.git`, so a symlink living under `.git` is
  invisible to `contained`'s new links map. Harmless in practice (not a
  legitimate `hash_paths`/`contained` target); unaddressed by design.
- non-blocking: TOCTOU between the staging rename's existence guard and the
  rename itself (two concurrent `build_template` calls for the same `dest`)
  is recorded, not fixed — `mkdir`'s `FileExistsError` on the staging name
  collision is the only concurrency guard this design provides, and a
  `dest`-level race surfaces as a `TreeError`-translated rename failure
  rather than silent corruption, which is an acceptable degradation for a
  single-writer harness, not a fix owed by this PRD.
- question: the read-side reuse of `_land` for `contained`/`hash_paths` is
  safe only because every on-disk tree those callers see was already
  produced by `build_template`'s now-stricter member validation; `_land`'s
  own per-component walk re-looks-up the *reassembled landing string*
  against the links map (trees.py:92-111), which is the exact shape of
  00158's original bug for a tree `build_template` did not build. This
  invariant (read-side callers only ever see `build_template`-built trees)
  is implicit in today's callers and is not changed by this PRD; recorded
  here in case a future caller hands `contained`/`fresh_clone` an
  externally-built tree.
- question: `_archive_name_escapes`'s drive-relative pattern
  (`^[A-Za-z]:[^/\\]`) requires a character after the colon, so a member
  literally named `C:` (no trailing component) matches none of the listed
  branches. `git archive` never emits a bare `C:` member name; left as an
  implementor judgment call rather than a required branch.
- dispatch 1 (claude): cardinal-sin 0, blocker 3, non-blocker 2, question 2
- non-blocking: A6 (device/FIFO refusal) is largely already satisfied by the
  existing `isfile()/isdir()/issym()` type check (trees.py:145-146); this
  PRD's A6 obligation, reflected in the Module placement text above, is a
  dedicated regression test, not new runtime code.
- dispatch 2 (claude-fallback): cardinal-sin 0, blocker 4, non-blocker 1, question 1
- dispatch 3 (claude-fallback): cardinal-sin 0, blocker 3, non-blocker 0, question 0
