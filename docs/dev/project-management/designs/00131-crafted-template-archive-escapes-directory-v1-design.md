# Design: crafted template archive escapes directory

## Architecture fit

`skills/use-qwen/scripts/eval_harness/trees.py` is the harness's one trust
boundary for untrusted repository content: `build_template()` turns a git
archive of an attacker-controlled commit into the sealed on-disk template
every attempt clones from (`fresh_clone()`). The existing containment model
is link-graph based: `_land()` walks a symlink name->target map hop by hop
and raises `TreeError` on an escape or cycle; `_refuse_escaping_links()`
applies this to an already-extracted tree before `fresh_clone()` copies it.
`build_template()` applies the same `_land()` walk, but only to the *tar
archive's* symlink members, before calling `tarfile.extractall()`. This fix
stays inside that one function — no new module, no new trust boundary — and
closes the gap between "every symlink member resolves safely" and "every
member, symlink or not, is safe to extract in the order the archive lists
it."

## Module placement

All changes are edits to existing files; no new modules.

- `skills/use-qwen/scripts/eval_harness/trees.py` — rewrite the preflight
  block inside `build_template()` (currently lines 136-141).
- `skills/use-qwen/scripts/test_eval_tree_links.py` — add the crafted
  duplicate-member regression and the benign-link/compat-path controls.

## Interfaces & contracts

No public signature changes. `build_template(repo: Path, first: str, dest: Path) -> str`
and `TreeError` keep their existing contracts; only the internal preflight
and the `extractall` call change.

### New module-level helper in `trees.py`

```python
def _refuse_duplicate_or_crossing_members(members: Sequence[tarfile.TarInfo]) -> dict[str, str]:
    """Reject an archive whose extraction order a link graph cannot describe.

    A `dict` keyed by member name collapses repeats to their last writer,
    which is exactly the ambiguity this guards: a member name that appears
    twice (symlink or not) means extraction order, not the final name table,
    decides what a later sibling's write reaches. Refuse that outright
    instead of resolving it. Returns the symlink name -> target map for the
    (now provably unique) member names, for `extractall`'s caller to re-walk
    containment with `_land` against every member, not only the symlinks.
    """
```

Behavior (replaces the current lines 136-141 preflight, called before
`archive.extractall(dest)`):

1. Normalize every member's name with `posixpath.normpath` (tar member names
   are already slash-form, but an archive is untrusted input — never assume
   its author normalized paths the way the harness will compare them). Any
   member whose raw `member.name` is absolute (`os.path.isabs(member.name)`)
   raises `TreeError("<name> is absolute")` immediately, **before** it is
   normalized or handed to `_land`. `_land` itself (`trees.py:82-111`) walks
   `Path(path).as_posix().split("/")` and only special-cases `.`/`..`
   segments — an absolute path's leading empty segment falls through
   unrecognized and the walk silently treats it as relative, so `_land`
   alone does **not** reject an absolute member path (unlike `contained()`,
   `trees.py:233-234`, which explicitly checks `os.path.isabs` first). This
   explicit check is why the helper is safe to rely on even on the
   `else` branch below, where `extractall` has no stdlib filter backing it.
2. Count occurrences of each **normalized** name across **all** members
   (symlinks, files, directories alike). Any name with count > 1 raises
   `TreeError("<name> is a duplicate member")` — this is the fix for the
   reported escape: a tree with a duplicate symlink/directory name no longer
   reaches extraction at all, so there is no "which occurrence does the link
   map describe" question left to answer incorrectly.
3. Build the symlink map **keyed by the same normalized names used in
   steps 1-2 and in the `_land` walk of step 4** —
   `{posixpath.normpath(m.name): m.linkname for m in members if m.issym()}`,
   not the raw `member.name` the current code uses (`trees.py:138`). Keying
   this map any other way means a hop built from a normalized path (step 4)
   could miss a symlink entry recorded under its unnormalized name (e.g. a
   member spelled `./foo` or `foo/`), silently passing an ancestor-crossing
   path the walk was supposed to catch. The map is unambiguous per key since
   step 2 already refused repeats.
4. Call `_land(links, name)` for **every** member's normalized name (not
   only the symlink members, as today) — this is the "reject member paths
   whose ancestors cross symlinks" requirement: a plain file member whose
   parent directory is a symlink the dict-based preflight had deduplicated
   away is now walked like any other path, hop by hop, by the same `_land`
   the rest of the module already trusts for this job.

`build_template()` calls this helper with `archive.getmembers()` in place of
the current two-line `links = {...}; for name in links: _land(links, name)`
block, keeping everything else (the tar read, the extraction call site, the
git init/add/commit sequence) unchanged in shape.

### `extractall` call: explicit safe filter, version-gated

Replace the bare `archive.extractall(dest)` with:

```python
if hasattr(tarfile, "data_filter"):
    archive.extractall(dest, filter="data")
else:
    archive.extractall(dest)
```

- `tarfile.data_filter` exists on every CPython that ships PEP 706 (3.12+,
  and the 3.9.17+/3.10.12+/3.11.4+ security backports) — the project's own
  floor is `>=3.10` (`pyproject.toml`), so this branches correctly on any
  3.10/3.11 patch release regardless of whether it got the backport.
  `filter="data"` is the strictest stdlib filter (strips absolute paths,
  device files, refuses writes outside the destination for its own
  extraction pass) and is also what makes the `trees.py:141`
  `DeprecationWarning` fire in the first place when omitted — passing it
  explicitly is finding 42's whole fix: an explicit choice, not a suppressed
  warning.
- The `else` branch is reached only on a pre-backport runtime that has no
  filter support at all. It is not an unfiltered fallback in the sense the
  PRD forbids: by the time `extractall` runs, `_refuse_duplicate_or_crossing_members`
  has already proven every member's name is unique and every member's
  ancestry stays inside `dest` — the same two properties `filter="data"`
  itself is enforcing for *this* escape class. The stdlib filter adds device
  file / absolute-path stripping this harness does not need (git archives
  carry neither), so losing it on an old patch release does not reopen the
  reported defect.

## Data flow

1. `build_template(repo, first, dest)` is called with the commit before the
   task and an empty `dest`.
2. `git archive` produces the tar bytes for `first^`'s tree (unchanged).
3. The tar is opened in memory (unchanged).
4. **New:** `_refuse_duplicate_or_crossing_members(archive.getmembers())`
   walks every member name once, raising `TreeError` before any byte is
   written if the archive is unsafe. On success it returns the symlink map.
5. `archive.extractall(dest, filter="data")` (or the unfiltered call on an
   old runtime whose safety was already established in step 4) writes the
   tree.
6. `git init`/`add -A`/`commit` seal it (unchanged) and `head_sha(dest)` is
   returned (unchanged).

Nothing downstream of `build_template` changes: `fresh_clone`'s own
`_refuse_escaping_links` + `copytree` path is untouched, since sealed
templates are git-committed trees without the raw-archive ordering problem
(git itself refuses duplicate paths in a tree object).

## Reuse inventory

- `_land(links: dict[str, str], path: str, active: frozenset[str] = frozenset())`
  (`trees.py:82`) — reused as-is for the new per-member ancestor check; no
  change to its signature or cycle/escape semantics.
- `TreeError` (`trees.py:41`) — reused as the refusal type for both the
  duplicate-member and the ancestor-crossing case, matching "report an
  unsafe archive through the existing TreeError contract" in the PRD.
- Greps tried, nothing else found:
  - `rg -n "extractall|data_filter|fully_trusted" skills/use-qwen/scripts/` —
    only the one call site in `trees.py:141` and this module's own tests.
  - `rg -n "normpath|posixpath" skills/use-qwen/scripts/eval_harness/trees.py` —
    `posixpath` is already imported and used by `_land`; no second
    normalization helper exists to reuse or duplicate.
  - `rg -n "duplicate" skills/use-qwen/scripts/eval_harness/` — no existing
    duplicate-detection helper in the harness; this is new.

## Alternatives considered

1. **Chosen: reject duplicate member names outright, plus walk every member
   (not just symlinks) through `_land`.** Smallest change that removes the
   ambiguity at its source — a name that never repeats has only one
   possible link-graph interpretation, so the existing `_land` logic is
   sufficient once applied to every member.
2. **Smallest-diff alternative: keep the dict-based symlink map, but build
   it from *all* occurrences in order and re-validate after each duplicate
   rather than rejecting.** Rejected: this would mean modeling tar's
   mid-extraction filesystem state (what does "the tree looks like" after
   member 3 of 7, with member 5 about to overwrite member 2's symlink)
   purely in Python before ever calling `extractall`, essentially
   re-implementing a tar extractor to get the ordering right. The PRD's own
   wording — "rather than relying on a dictionary that loses duplicate-member
   information" — reads as ruling this out; outright rejection is both
   simpler and strictly safer, since a git-produced archive from this
   harness's own `git archive` call never legitimately contains a duplicate
   member name (git trees cannot hold two entries with the same name), so
   rejecting one is never a true-positive cost to normal operation.
3. **Rejected: always require `tarfile.data_filter` and drop pre-3.12
   support in this function.** The PRD requires preserving Python 3.10+
   behavior and testing the compatibility branch explicitly; this harness's
   `pyproject.toml` floor is `>=3.10`, and CI runs a Windows matrix job at
   that floor (the known-flaky `use-qwen` Windows failures already visible
   in the current CI run are unrelated path-ordering/hash assertions, not a
   filter-availability issue) — raising the floor is out of scope for a
   containment bug fix and would be a larger, unrelated diff.

## Risks & edge cases

- **Risk of over-rejection:** a legitimate tree that happens to need two
  entries normalizing to the same path (e.g. case-only differences on a
  case-sensitive filesystem) is now refused. This cannot occur from this
  harness's own `git archive` output (git trees are case-sensitive and
  unique by construction), so the risk is theoretical for this call site.
- **Likely next change 1:** if the harness ever accepts an archive from a
  source other than its own `git archive` call (e.g. a user-supplied patch
  bundle), the same `_refuse_duplicate_or_crossing_members` helper should be
  the first thing applied to it — it is written as a standalone function
  precisely so a second caller does not have to re-derive the logic.
- **Likely next change 2:** `apply_patch`'s `git apply` already refuses
  writes outside its clone on its own (per its docstring); if that trust is
  ever questioned, the same `_land`-based ancestor check here is the
  pattern to reuse rather than re-deriving a third containment scheme.
- **Edge case — reversed order:** the PRD's Phase 0 task explicitly calls
  out "reversed/duplicate member ordering." Because step 2 above counts
  occurrences over the whole member list before extraction starts, order
  never matters to the duplicate check — a (symlink, dir) pair and a (dir,
  symlink) pair are refused identically.
- **Edge case — a safe, non-duplicate symlink elsewhere in the tree:** must
  keep sealing correctly (the existing `INSIDE_CHAINS`/`DANGLING_LINKS`
  cases in `test_eval_tree_links.py`), since the new per-member `_land` walk
  is strictly additive to, not a replacement of, the existing symlink-only
  walk's logic — same function, larger input set.
- Python 3.14 breakage was flagged by the audit as unverified; this design
  does not claim 3.14 compatibility beyond "the explicit `filter='data'`
  path removes the specific deprecation warning finding 42 observed," which
  is the only claim the PRD asks this change to make.

## Test strategy outline

All new/changed tests live in `skills/use-qwen/scripts/test_eval_tree_links.py`
beside the existing `build_template` link-chain tests, using the same
`built_repo`/`_commit_symlink`/`_task_start_commit` fixtures already imported
there.

1. **Regression (Phase 0, task 1):** commit a tree whose task-start commit
   contains a duplicate normalized member name — one occurrence a directory
   (or benign symlink) and the other a symlink escaping to a sentinel
   outside the destination (mirrors the reported evidence: `before: outside
   holds []` / `after: outside holds ['pwned']`). Assert `build_template`
   raises `TreeError`, the sentinel directory is untouched (`list(outside.glob("*")) == []`
   before and after), and `dest` holds nothing (`list(dest.glob("*")) == []`,
   matching the existing escaping-chain tests' assertion shape). Parametrize
   both member orderings (symlink-then-dir, dir-then-symlink).
2. **Ancestor-crossing, non-symlink member:** a tree where a safe-looking
   symlink member's name is unique but a *different*, non-symlink member's
   path has an ancestor that is itself a symlink crossing outside — assert
   `TreeError` and nothing extracted. This is the case the current code
   cannot catch today because it only walks symlink names through `_land`.
3. **Existing link-chain tests must keep passing unmodified**
   (`ESCAPING_CHAINS`, `CYCLES`, `INSIDE_CHAINS`, `DANGLING_LINKS` against
   `build_template`) — they prove the new per-member walk does not change
   behavior for the cases the module already handled.
4. **Filter-compatibility branch:** one test that monkeypatches
   `tarfile.data_filter` to absent (`monkeypatch.delattr(tarfile, "data_filter", raising=False)`)
   and confirms `build_template` still seals a benign template correctly on
   that branch (covers "testing the compatibility branch as well as the
   standard filtering path").
5. **Finding 42, warning check:** `recwarn`/`pytest.warns(None)`-style
   assertion (or `warnings.catch_warnings(record=True)` wrapped around a
   `build_template` call on a benign tree) that no `DeprecationWarning`
   mentioning tar extraction filtering is raised on the current Python's
   standard `filter="data"` branch. Run alongside the existing
   `test_build_template_seals_a_link_chain_that_stays_inside_the_tree`-style
   benign cases so the check exercises real template sealing, not a no-op
   tree.
6. Full acceptance per the PRD: `uv run pytest skills/use-qwen/scripts/test_eval_tree_links.py`
   passes with the new regression failing against pre-change code (verified
   by running it once before the fix lands), then `uv run pytest`,
   `uv run python3 skills/create-skill/scripts/validate_skill.py skills/use-qwen`,
   and `braid --check` all green.

## Review log

- [question] Docstring and Behavior section disagree about who performs the per-member ancestor walk — the docstring implies `extractall`'s caller re-walks containment, while step 4 says the helper itself walks every member. Fix: align the docstring with step 4 (the helper raises before returning; drop or reframe the "caller re-walks" language).
- [non-blocker] Risk section's case-sensitivity example doesn't match what `posixpath.normpath` can collide on (it never folds case). Fix: replace with an actual normpath-collision example (e.g. `a/./b` vs `a/b`, or `foo/` vs `foo`).
- [non-blocker] No stated behavior for hardlink (`islnk()`) tar members, despite the design anticipating reuse on non-git-archive input. Fix: either scope hardlinks out explicitly for any future non-git-archive caller, or have the preflight reject `islnk()` members outright now.
- [question] No verification that `filter="data"` preserves executable-bit/setuid/setgid assertions in existing tests (a real behavior change from PEP 706 sanitization, independent of the preflight logic). Fix: confirm via `rg` against `test_eval_tree_state.py` that no existing test asserts those bits; update if one does.
dispatch 1 (claude): cardinal-sin 0, blocker 0, non-blocker 2, question 2
- [FIXED, blocker] `_land` does not reject absolute member paths, undermining the no-filter branch's safety claim. Fix applied: explicit `os.path.isabs(member.name)` check raises `TreeError` before normalization/`_land`, documented in Interfaces & contracts step 1.
- [FIXED, blocker] Normalization mismatch between the symlink map's keys and the normalized names used by the ancestor walk was unspecified. Fix applied: step 3 now states the map is keyed by the same `posixpath.normpath` names used everywhere else.
- [non-blocker] The "git trees cannot hold two entries with the same name" framing understates that duplicate names are the real attack surface this PRD defends against (a malformed/fsck-bypassing tree), not just a false-positive risk. Not fixed — recorded for the implementor to phrase carefully in code comments if desired.
dispatch 2: codex unavailable (sandbox-exec: Operation not permitted, no usable findings), Claude fallback
dispatch 2 (claude-fallback): cardinal-sin 0, blocker 2, non-blocker 1, question 0
dispatch 3: codex unavailable (sandbox-exec: Operation not permitted, no usable findings), Claude fallback
dispatch 3 (claude-fallback): cardinal-sin 0, blocker 0, non-blocker 0, question 0
