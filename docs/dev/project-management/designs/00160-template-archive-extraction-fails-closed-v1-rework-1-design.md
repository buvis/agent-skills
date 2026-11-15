# Rework design: 00160-template-archive-extraction-fails-closed-v1, cycle 1

Source review: docs/dev/project-management/reviews/00160-template-archive-extraction-fails-closed-v1-review-1.md (head_sha a8347f3c691d64e3eec1d2d124e3fa92953629bd)

The one 🔴 row this design closes:

> R1 — Case-folding ancestor alias lets an accepted archive write outside
> `dest`. `A -> .` plus a member named `a/../outside/secret.txt` passes
> validation: the duplicate/case rule folds whole normalized names, so it never
> notices that `a` aliases the symlink `A` on a case-insensitive host. On the
> manual (no-filter) path `dest.joinpath(member.name)` then mkdirs through
> `dest/a`, which case-folds onto `dest/A -> .`, so `..` climbs out of `dest`
> and the payload lands beside it. Reproduced: the file appeared at
> `<box>/outside/secret.txt`, outside the tree root. The filter path keeps it
> inside (`tree/outside/secret.txt`), so this is also a parity break. Breaks
> the PRD's first success metric on the manual path. Validate case-equivalent
> components for ancestor and symlink lookups before extraction, and pin the
> regression on both seams.
> File: `skills/use-qwen/scripts/eval_harness/trees.py:213`

R1 names one archive, but the defect is a class: **the module resolves archive
paths exactly while the host that will extract them merges names.** Review
found four more shapes in that class, each reproduced, and two of them also
write outside `dest`:

- a member whose aliasing component is reached through another link's target
  (`A -> .`, `B -> a/../outside`, `B/secret.txt`) - writes outside;
- a member whose first segment differs from the symlink only in normalization
  form, composed against decomposed (`é -> .`, `é/../outside/secret.txt`) -
  writes outside, because APFS is normalization-insensitive;
- a member directly beneath a case-aliased directory link;
- a link whose target case-aliases its own name, which is a self-cycle on a
  merging host and which the PRD already requires refusing.

This design closes the class. Closing only the named shape would leave two
equally critical siblings open, which is what the three review dispatches
established (`## Review log`).

## Architecture fit

Prior fix: none - there was no prior rework fix. This is cycle 1, so every
CRITICAL row here was introduced or left open by the PRD's first
implementation, not by a rework. `git diff --stat
3c0c9dbb46b05bda8a01470e75d7e4e088684736..HEAD` over the PRD's whole work range
touches `skills/use-qwen/scripts/eval_harness/trees.py` (+201),
`skills/use-qwen/scripts/test_eval_tree_archive_safety.py` (+709, new),
`skills/use-qwen/scripts/test_eval_tree_archive_safety_modes.py` (+197, new),
`skills/use-qwen/scripts/test_eval_tree_archive_staging.py` (+392, new),
`skills/use-qwen/scripts/test_eval_tree_links.py` (+34/-3) and
`skills/use-qwen/scripts/test_eval_tree_state.py` (+70), beside the design doc,
capsule and changelog. R1 was **introduced** by that work: the validation layer
it added (`_refuse_duplicate_or_crossing_members`, `_ancestor_crossing`,
`_land`) is where the case-equivalence hole lives, and the manual extraction
path it added (`_extract_without_filter`) is the one that writes through the
alias. Before this PRD there was a bare `extractall`, which had the same hole
and worse; the fix is to close it in the new layer, not to revert.

The work lands in one module,
`skills/use-qwen/scripts/eval_harness/trees.py`, in its validation layer. The
module is the harness's whole containment boundary: `build_template` validates
then extracts, and `hash_paths` / `fresh_clone` / `contained` read back through
the same `_land` walk. A hole in the write-side validation is the whole hole.

That shared walk is also the design's central tension, and resolving it is the
main decision here. The archive side must judge a path the way **the worst host
that might extract it** would, because a tar validated on Linux can be
extracted on macOS. The read side must judge the way **the host it is actually
on** does, because its link map comes from `_walk` of a real tree where the
filesystem has already decided which names are the same place. Those are
different questions, so `_land` gains a per-call switch rather than a global
behaviour change: archive-domain callers ask for case-folded resolution, and
`_walk`-derived callers keep today's exact semantics. Two earlier drafts of
this document got this wrong in both directions (`## Review log`).

The capsule records this module as the security-critical path of the qwen
evaluation harness, and the PRD sets `default_model: opus` for that reason.

## Module placement

Edits to existing files only. No new files.

- `skills/use-qwen/scripts/eval_harness/trees.py` - edit. Add `_fold`; add two
  keyword-only parameters to `_land` and use them; pass `fold=True` from the
  two archive-domain rules; replace `_ancestor_crossing`'s landing-equality
  test with a crossed-slot test.
- `skills/use-qwen/scripts/test_eval_tree_archive_safety.py` - edit. Add six
  refusal parametrisations to `ANCESTOR_ESCAPES`, which already runs every
  entry on both filter seams and in both member orders.

Unchanged, and deliberately so:

- `contained` (`trees.py:405`), `_refuse_escaping_links` (`trees.py:173`),
  `hash_paths` (`trees.py:349`), `fresh_clone` (`trees.py:331`) - **bodies
  untouched**. They call `_land` without the new keywords, so they keep
  today's case-sensitive resolution. Folding them would collapse two
  legitimately distinct case-aliased links on a case-sensitive host, which
  would make `_refuse_escaping_links` stop refusing a tree holding an escaping
  symlink - weakening PRD capability 3 while fixing capability 1.
- `_archive_name_escapes`, `_safe_mode`, `_extract_without_filter`,
  `build_template` - unchanged. Neither extraction path is touched: the fix is
  that the aliasing archive never reaches extraction.
- `test_eval_tree_links.py`, `test_eval_tree_state.py`,
  `test_eval_tree_archive_safety_modes.py`, `test_eval_tree_archive_staging.py`
  - unchanged.

## Interfaces & contracts

Every symbol is named exactly as it must appear in the code. Every verdict
quoted below was measured against the real module before this document was
written (`## Review log`).

### `_fold`

Closes: R1 — Case-folding ancestor alias lets an accepted archive write outside `dest`.

```python
def _fold(name: str) -> str:
    """`name` as a name-merging host would key it, for comparison only.

    A tar validated on one host is extracted on another, so the archive rules
    have to judge for the host that merges names. Two mergings matter, and both
    were measured on the development host:

      - case: on macOS and Windows `A` and `a` are one place;
      - normalization form: APFS is normalization-insensitive, so the composed
        and decomposed spellings of `é` are one place (verified: writing the
        composed name makes the decomposed name exist).

    So fold both. `unicodedata.normalize("NFC", name).lower()`.

    `str.lower`, not `str.casefold`: real filesystems do simple case folding,
    and APFS and NTFS both keep `straße.txt` and `strasse.txt` as two files,
    which full Unicode folding would merge. NFC rather than NFD because it is
    the composed form most sources already emit; either direction works as long
    as one is chosen and used on both sides of every comparison.

    Comparison only: no separator handling and no `.`/`..` walking. Never write
    or store the result.
    """
```

- Signature: `_fold(name: str) -> str`. Returns
  `unicodedata.normalize("NFC", name).lower()`. `import unicodedata` joins the
  module's existing stdlib imports.
- Module-level, private, placed directly above `_land`.
- Used by `_land`, `_ancestor_crossing`, and the whole-name case rule in
  `_refuse_duplicate_or_crossing_members` (which switches from a bare
  `name.lower()` to `_fold(name)`: same value for every ASCII name, one
  definition, and now normalization-aware as well).
- **Measured**: with the normalizing fold, all seven regression cases below are
  refused and every entry of all five existing matrices keeps its current
  verdict. With a `name.lower()`-only fold, the normalization case is ACCEPTED
  and writes outside `dest`.

### `_land` - two keyword-only parameters

Closes: R1 — Case-folding ancestor alias lets an accepted archive write outside `dest`.

```python
def _land(
    links: dict[str, str],
    path: str,
    active: frozenset[str] = frozenset(),
    *,
    fold: bool = False,
    crossed: set[str] | None = None,
) -> str:
```

- `links` stays **raw**-keyed. The caller never folds the map.
- `fold=False` (the default) is today's behaviour, byte for byte. Every
  existing caller that does not pass the keyword is therefore unchanged, which
  is what keeps the read side as it is.
- `fold=True` resolves each hop under case equivalence. Build the lookup once
  per call as `{_fold(key): key for key in links}`; for each landing compute
  `probe = _fold(landing) if fold else landing`, look `probe` up in that map,
  and dereference `links[<the raw key it found>]`. The **returned landing keeps
  its raw spelling** in both modes - a caller that joined a folded landing onto
  `dest` would write a lower-cased path.
- The cycle guard uses `probe` on both sides: membership is `probe in active`
  and the recursive call passes `active | {probe}`. Under `fold=True` this
  makes a case-equivalent self-reference a cycle, which is correct and
  required: `readme -> README` on a case-insensitive host points at itself, and
  the host reports `ELOOP` (measured: `OSError errno 62, Too many levels of
  symbolic links`). PRD capability 1 requires refusing self and cyclic chains,
  so today's acceptance of that archive is a defect, not a baseline.
- `crossed`, when a set is passed, receives `probe` for **every symlink slot
  the walk passes through**, including slots reached inside a link target's own
  resolution and at any recursion depth (pass `crossed` down the recursive
  call). This is the new information the ancestor rule needs: a final landing
  cannot tell you which links were traversed to reach it.
- Every refusal message is unchanged and keeps the raw spelling:
  `"%s leaves the tree" % path`, `"%s is a link cycle" % landing`,
  `"%s leaves the tree: %s" % (landing, target)`.

### `_ancestor_crossing` - crossed-slot test, not landing equality

Closes: R1 — Case-folding ancestor alias lets an accepted archive write outside `dest`.

Signature unchanged: `_ancestor_crossing(members: Sequence[tarfile.TarInfo], links: dict[str, str]) -> None`.

- `symlink_landings` keeps its meaning (the place each symlink itself sits) and
  is now a set of **folded** slots: compute
  `posixpath.join(_land(links, "/".join(segments[:-1]), fold=True), segments[-1])`
  and add `_fold(...)` of it.
- The proper-prefix loop no longer compares landings. For each proper prefix it
  lands the prefix with a fresh `crossed` set and refuses when that set
  intersects the slots:

  ```python
  for end in range(1, len(segments)):
      crossed: set[str] = set()
      _land(links, "/".join(segments[:end]), fold=True, crossed=crossed)
      if crossed & symlink_landings:
          raise TreeError("%s is beneath an archive symlink" % member.name)
  ```

- **Why the equality test had to go, and why this is not a bigger change than
  needed.** With `fold=True`, landing a prefix that case-aliases a symlink
  *dereferences* it, so the returned landing is the link's target and can never
  equal the link's own slot. Keeping the equality test would silently disable
  the ancestor rule for exactly the shapes this fix exists to catch. The
  crossed set is the minimal replacement: it asks the question the rule always
  meant to ask ("did reaching this member's parent go through a symlink"),
  which a landing cannot answer once links resolve.
- Refusal text unchanged, carrying the member's raw name.

### `_refuse_duplicate_or_crossing_members` and `_refuse_colliding_landings`

Closes: R1 — Case-folding ancestor alias lets an accepted archive write outside `dest`.

- `_refuse_duplicate_or_crossing_members` - its `folded` set switches from
  `name.lower()` to `_fold(name)` (identical value, single definition).
  Everything else is unchanged: the `_archive_name_escapes` checks, the
  `os.path.isabs` check, the type refusal, the `names` duplicate set, their
  order, and every refusal string. It still builds the raw-keyed `links` map
  and still calls `_refuse_colliding_landings` then `_ancestor_crossing`, in
  that order.
- `_refuse_colliding_landings` - every `_land` call inside it gains
  `fold=True`, and nothing else changes: the `landings` and `files` sets, both
  refusal strings, and the ancestor-file loop stay as they are. It is an
  archive-domain rule, so it must judge collisions for the merging host too;
  leaving it raw while folding the ancestor rule would let two members collide
  on a case-insensitive host without either rule noticing.

### Unchanged, and load-bearing that it stays unchanged

Closes: R1 — Case-folding ancestor alias lets an accepted archive write outside `dest`.

Part of the contract: the fix is correct only if these stay as they are. An
implementor who "finishes the job" by folding them reintroduces a defect or
breaks valid input. Each exclusion below was measured, not assumed.

- `contained(root: Path, relpath: str) -> Path`,
  `_refuse_escaping_links(root: Path) -> None`,
  `hash_paths(root: Path, paths: Sequence[str]) -> dict[str, str]`,
  `fresh_clone(template: Path, dest: Path) -> Path` - **bodies untouched; do
  NOT pass `fold=True` from any of them.** Their link maps come from `_walk` of
  a real tree, where the host has already decided which names are the same
  place. Measured on the map `{'A': '../../outside', 'a': '.'}`: folding
  collapses the two keys, `_refuse_escaping_links` stops refusing a tree
  holding an escaping symlink, and `contained('A/file.txt')` returns
  `root/file.txt`, a path the OS would not walk. No test enforces this; it
  rests on this contract.
- `_land`'s **returned landing stays raw** in both modes. A folded value is a
  lookup key, a cycle-guard member or a set element, never a return value, a
  `links` key, a refusal message, or a path joined onto `dest`.
- `_archive_name_escapes(text: str) -> bool`, `_safe_mode(mode: int) -> int`,
  `_extract_without_filter(archive, dest, members) -> None`,
  `build_template(repo: Path, first: str, dest: Path) -> str` - unchanged.
  Neither extraction path is touched: the fix is that the aliasing archive
  never reaches extraction.
- Every existing refusal string in the module is unchanged, byte for byte.
  `COLLISIONS` and the near-miss matrices do not assert reasons today, so a
  changed message would not fail a test - which is exactly why it is pinned
  here.

### Regression contract

Closes: R1 — Case-folding ancestor alias lets an accepted archive write outside `dest`.

Seven entries added to `ANCESTOR_ESCAPES` (`test_eval_tree_archive_safety.py:157`),
whose test is
`test_build_template_refuses_a_link_reached_through_an_ancestor_link_in_either_order`.
That matrix already parametrises every entry over the filter-present and
filter-absent seams and over both member orders, and
`_assert_refused_on_seam` already asserts the outside sentinel's bytes and
modes are unchanged before asserting the `TreeError` and the absent `dest`.
Each case is paired with the mutation it must kill, so the guard cannot be
partially deleted and still pass:

- `id="case-alias-self-link"` - `[("A", ("sym", ".")), ("a/../outside/secret.txt", PAYLOAD)]`.
  Measured today: ACCEPTED, and the manual path writes outside `dest`.
- `id="case-alias-self-link-inverse"` - `[("a", ("sym", ".")), ("A/../outside/secret.txt", PAYLOAD)]`.
  The inverse casing, so a fold applied to only one side of a comparison fails here.
- `id="case-alias-directory-link"` - `[("Pkg", DIRECTORY), ("Alias", ("sym", "Pkg")), ("alias/escape/secret.txt", PAYLOAD)]`.
  Measured today: ACCEPTED. This is the case the crossed-slot test exists for.
- `id="case-alias-directory-link-inverse"` - `[("Pkg", DIRECTORY), ("alias", ("sym", "Pkg")), ("Alias/escape/secret.txt", PAYLOAD)]`.
- `id="case-alias-inside-a-link-target"` - `[("A", ("sym", ".")), ("B", ("sym", "a/../outside")), ("B/secret.txt", PAYLOAD)]`.
  Measured today: ACCEPTED, and the manual path writes `outside/secret.txt`
  outside `dest`. The alias is consumed inside `B`'s own target, so only a
  folded `_land` catches it.
- `id="case-equivalent-self-cycle"` - `[("readme", ("sym", "README"))]`.
  Measured today: ACCEPTED. It is a self-cycle on a case-insensitive host
  (`ELOOP`), so PRD capability 1 requires refusing it.
- `id="normalization-alias-self-link"` - a symlink named with the **composed**
  spelling of `é` targeting `.`, plus a content member whose first segment is
  the **decomposed** spelling of the same character, climbing out:
  `[(NFC("é"), ("sym", ".")), (NFD("é") + "/../outside/secret.txt", PAYLOAD)]`.
  Build the two spellings with `unicodedata.normalize("NFC", "é")` and
  `unicodedata.normalize("NFD", "é")` in the test module rather than
  pasting literals, so an editor or a git filter cannot normalize the file and
  silently turn the two members into one. Measured today: ACCEPTED, and the
  manual path writes `outside/secret.txt` outside the tree root - the third
  reproduced escape in R1's class.

Acceptance criterion, the PRD's first success metric stated as a test: for each
case the outside sentinel's bytes and modes are unchanged and nothing exists at
`dest`, on both seams and in both member orders.

**No accept-side case is added, and none is changed.** `NEAR_MISSES`,
`SAFE_LINKS` and `LINK_CHAINS` must stay exactly as they are and must stay
green unedited; that is the regression statement for over-refusal. An earlier
draft proposed adding `readme -> README` as an accept-side control, which was
wrong: that archive must be refused.

## Data flow

`build_template(repo, first, dest)` is unchanged in shape:

1. `_git_bytes(repo, "archive", "--format=tar", "%s^" % first)` yields the tar
   bytes; `dest` is refused if anything already sits there; a staging directory
   is created beside `dest`.
2. `_refuse_duplicate_or_crossing_members(archive.getmembers())` runs on tar
   metadata alone, before any write: text rules, absolute check, type refusal,
   duplicate set and the whole-name case rule. It builds the raw-keyed `links`
   map and calls `_refuse_colliding_landings(members, links)` then
   `_ancestor_crossing(members, links)`.
3. Both of those resolve with `fold=True`, so a case alias is followed wherever
   it appears - as a member's own ancestor, or inside another link's target.
   `_ancestor_crossing` additionally collects the symlink slots each prefix walk
   crosses and refuses on an intersection with the archive's own symlink slots.
   Folded strings exist only as lookup keys, cycle-guard members and
   set elements; none is returned, stored in `links`, interpolated into a
   message, or joined onto a path.
4. Only an archive that survived steps 2-3 extracts, via
   `archive.extractall(staging, filter="data")` or
   `_extract_without_filter(archive, staging, archive.getmembers())`. Neither
   is touched.
5. Seal in staging, then `staging.rename(dest)`.

The read-back path - `hash_paths` -> `contained` -> `_land`, and
`fresh_clone` -> `_refuse_escaping_links` -> `_land` - calls `_land` with no
keywords, so it resolves exactly as today and does **not** fold. That is the
deliberate asymmetry argued in `## Architecture fit`.

## Reuse inventory

Synonym sets taken from `~/.claude/rules-library/rationalizations.md`
("Synonyms-to-grep"), which is present on this host.

- **`_land` (`trees.py:82`)** - the existing hop-by-hop walk and the single
  resolution point for archives and read-back alike. Extended in place with two
  keyword-only parameters rather than copied: a second walker would be two
  containment rules that could drift apart, which is precisely the failure this
  module exists to prevent. The default-off switch is what lets one function
  serve both domains.
- **`_archive_name_escapes` (`trees.py:114`)** - the archive-domain text
  classifier. Unchanged: case folding is orthogonal and the two compose at the
  caller.
- **`ANCESTOR_ESCAPES` (`test_eval_tree_archive_safety.py:157`)** - the
  existing ancestor-escape matrix, already both-seams and both-orders. All six
  new cases are parameters there, not a new test or fixture. Every current
  entry carries a victim member that trips the landing-based rule, which is why
  none catches a case alias.
- **`_assert_refused_on_seam` (`:124`)**, **`_select_seam` (`:87`)**,
  **`_hide_data_filter` (`test_eval_tree_links.py:368`)** - the existing
  both-seams refusal harness and the faithful no-filter seam.
- **`_outside_sentinel` (`test_eval_tree_links.py:373`)** and **`_snapshot`
  (`test_eval_tree_archive_safety.py:103`)** - the outside-sentinel fixture and
  its byte-and-mode comparison. They already assert the exact property R1
  violates.
- **`NEAR_MISSES` (`:380`)**, **`SAFE_LINKS` (`:593`)**, **`LINK_CHAINS`
  (`:631`)** - the accept-side matrices. Reused as the over-refusal
  regression: unedited and green. `NEAR_MISSES` is the sharpest of the three
  here, because it deliberately holds `alias -> pkg` together with members
  under `pkg/...` and none under `alias/...`, so it would catch a crossed-slot
  rule that fired on the symlink's target rather than on a traversal.
- **`COLLISIONS` (`:264`)** - existing case-collision coverage
  (`case-only-file-names-not-adjacent`, `case-only-directory-names`,
  `case-collision-only-after-normalizing`): archives the suite requires be
  refused, covering two content members colliding by case. None covers a
  symlink whose name case-aliases another member's ancestor component, which is
  the gap behind R1.
- **Case folding for path lookups: nothing found.** Greps tried over
  `skills/use-qwen/scripts/`: `casefold`, `\.lower\(\)`, `normcase`,
  `normalize`, `unicodedata`, `NFC`, `NFD`. The only hits are `trees.py:214`
  and `:217` (the whole-name case rule, which `_fold` now backs),
  `engines.py:76` (a `.py` suffix test) and `test_eval_tree_state.py:347` (a
  hex-digest assertion). Control: `rg -n "def contained|def _land"` over the
  same tree returns `trees.py:82` and `trees.py:405`, so the pattern works and
  the absence is real. `os.path.normcase` is deliberately not reused: it is a
  no-op on POSIX, so it would let the host decide a rule the PRD says must be
  decided in the archive domain.

## Alternatives considered

The axis is **where case equivalence applies**. All options are small; they
differ in correctness, and every verdict below was measured, not argued.

**Option A - fold the archive-domain resolution under case AND NFC
normalization, leave the read side raw, replace the ancestor rule's landing
equality with a crossed-slot test (chosen).** Measured: refuses all seven new
cases; leaves `ANCESTOR_ESCAPES`, `COLLISIONS`, `NEAR_MISSES`, `SAFE_LINKS` and
`LINK_CHAINS` at their current verdicts, with zero verdict changes across every
entry of all five.

**Option B - the smallest diff: fold only the equality test inside
`_ancestor_crossing`, touch nothing else.** This was the second draft's choice.
Measured: it refuses the self-link and directory-link shapes but **still
accepts** `case-alias-inside-a-link-target`, which writes outside `dest` - so
it leaves a reproduced critical escape open. It also leaves the case-equivalent
self-cycle accepted. Rejected: a fix that closes two of four reproduced escapes
is not a fix. What Option A's extra size buys over it is exactly those two
escapes.

**Option C - fold `_land`'s lookup but keep the landing-equality ancestor
test.** This was the first draft's choice. Measured: the fold makes `_land`
dereference the aliased prefix, so the equality test can never fire and
`case-alias-directory-link` stays ACCEPTED - the fold cancels the fix.
Rejected, and it is the reason the equality test is replaced rather than kept.

**Option D - fold everywhere, read side included.** Measured on a constructed
real-tree map `{'A': '../../outside', 'a': '.'}`: the two raw keys collapse to
one entry, `_refuse_escaping_links` stops refusing a tree holding an escaping
symlink, and `contained('A/file.txt')` returns `root/file.txt`, a path the OS
would not walk. Rejected: it weakens PRD capability 3 in the act of fixing
capability 1.

**Option E - refuse any archive holding two case-equivalent names anywhere.**
Safe and about as small, but it refuses valid `git archive` output; `NEAR_MISSES`
exists to pin that acceptance. Rejected as over-refusal.

**Option F - fold case only, leaving normalization form exact.** This was the
third draft's choice. Measured: it accepts
`[NFC("é") -> ., NFD("é")/../outside/secret.txt]`, and the manual path writes
`outside/secret.txt` outside the tree root. Rejected: on a
normalization-insensitive filesystem that is the same escape as R1 with a
different alphabet.

What Option A deliberately does **not** buy: name-merging rules beyond case and
NFC, the collision rule's own case-insensitivity, and any read-side change.
All three are stated under `## Risks & edge cases` as open rather than silently
skipped.

## Risks & edge cases

- **This design also closes review row R3's first half, which has its own fix
  row.** Measured: under Option A the archive
  `[pkg/, alias -> pkg, alias/file.txt]` becomes REFUSED
  (`alias/file.txt is beneath an archive symlink`), because the crossed-slot
  test fires on a safe symlink ancestor too - which is what the PRD text asks
  for. R3 is a separate 🟠 row covering that plus a manual-path link-target
  containment check. **The implementor of R3 must re-check what is left of it
  after this change lands, and must not add a second ancestor mechanism.** Said
  plainly here because two tasks silently fixing one defect is how a rework
  cycle produces conflicting code.
- **`fold` must stay default-off, and no test enforces that.** The single most
  likely implementation error is to make folding unconditional, or to pass
  `fold=True` from `contained` or `_refuse_escaping_links` for consistency.
  That is Option D, measured to break read-side containment. The `_land`
  contract and the Module placement list pin it in prose only: the existing
  suite stays green either way, so **this invariant is review-backed, not
  test-backed**. An earlier draft listed an "expected to pass" mutation here
  and called the pass evidence; dispatch 3 correctly rejected that as a
  coverage gap dressed up as a check, and it has been removed. Closing it
  properly means a focused read-side regression built on the measured map
  `{'A': '../../outside', 'a': '.'}`, asserting `_refuse_escaping_links` still
  refuses that tree and `contained('A/file.txt')` still resolves through `A`.
  Recorded as open, not fixed here: it is read-side coverage, and this rework
  row is a write-side escape.
- **A folded string must never be written or stored.** Folded values are lookup
  keys, cycle-guard members and set elements only. If one reaches a returned
  landing, a `links` key, a refusal message or a joined path, it silently
  lower-cases real paths. The deterministic-seal and read-back-chain tests
  would catch the worst of that, but not all of it.
- **No test asserts a refusal reason, so green is weaker evidence than it
  looks.** `rg -n "match=|pytest.raises"` over the five-file set finds no
  `match=`; `_assert_refused_on_seam` asserts `isinstance(raised,
  trees.TreeError)` plus the sentinel snapshot. A case can therefore pass while
  being refused for the wrong reason. The paired mutation checks below are the
  compensating control, not the suite being green.
- **`_fold` covers case and NFC normalization, and nothing else.** Those are
  the two mergings measured on the development host. It does not cover a host
  that merges by some other rule (compatibility folding, legacy codepage
  equivalence, or the HFS+ variant of NFD with its own exclusion ranges). The
  design's claim is bounded to the two it refuses, not to "host equivalence" in
  general. Cycle-1 ledger row R16 recorded Unicode normalization as a discarded
  low; dispatch 3 showed that was wrong where it touches this escape class, and
  this design now covers it. The ledger entry stands as the record of the
  narrower case-fold-only question it was raised about.
- **The collision rule did not become case-insensitive, and the design does not
  claim it did.** `fold=True` changes how `_land` resolves *through links*; it
  does not change the `landings` and `files` sets in
  `_refuse_colliding_landings`, because `_land` still returns raw spellings. So
  a file member `Pkg` beside a content member `pkg/file.txt` is still accepted,
  and on a case-insensitive host the second would write under the first. That
  is a collision defect, not an escape - nothing lands outside `dest` - and it
  is left open rather than fixed here. Raised by dispatch 3; recorded in the
  Review log.
- **The escape's failure mode is host-dependent; the refusal is not.** On a
  case-insensitive host (macOS, where all four escapes were reproduced) the
  self-link and target-alias cases fail pre-fix by writing outside the
  sentinel. On a case-sensitive host `dest/a` is a real directory, the payload
  lands inside `dest`, the sentinel is untouched, and the same tests fail only
  on the missing `TreeError`. Both are failures and both are fixed; record
  which host the fail-first run used so a Linux reader does not conclude the
  defect is absent.
- **Likely next changes after this cycle.** (1) The residue of R3 - see the
  first bullet. (2) R4's filter/manual mode parity, which touches `_safe_mode`
  and `_extract_without_filter` and not the validation layer. (3) Unicode
  normalization (R16) if a native Windows or APFS result justifies it. None is
  boxed in: all three extend the same predicate chain, and `_fold` plus the
  `crossed` record are single-purpose additions.
- **Windows remains simulated.** The PRD's Risks section says native results
  come only from the hosted Windows job. The new cases assert path-domain
  behaviour, which is host-independent, so they are valid locally; they do not
  claim to prove native Windows link semantics.

## Test strategy outline

- **Fail-first is mandatory** (the project's rule for a bug fix). Add all seven
  parametrisations first and watch them fail against `a8347f3`, recording the
  host because the pre-fix failure mode differs by filesystem (see Risks).
- **Paired mutation checks - each mutation named with the exact cases it must
  kill, and only mutations the cases actually distinguish.** Run each once and
  record the result. Two earlier drafts specified mutations that could not fail
  any of their own cases; every pairing below was measured before being
  written, and three candidate mutations were deleted for being unsatisfiable.
  - Remove `_fold` from the `symlink_landings` insertion -> must fail
    `case-alias-directory-link`. Measured: that case becomes ACCEPTED.
    **Must NOT be paired with `case-alias-directory-link-inverse`**, whose
    symlink is already named in lower case, so its stored slot is unaffected by
    the fold; measured, the inverse case stays refused under this mutation.
  - Remove `fold=True` from `_ancestor_crossing`'s `_land` calls -> must fail
    both directory-link cases.
  - Revert the crossed-slot test to landing equality, keeping `fold=True` ->
    must fail both directory-link cases. This is Option C, measured to cancel
    the fix.
  - Change `_fold` to `name.lower()` (drop the NFC normalization) -> must fail
    `normalization-alias-self-link`. Measured: that case becomes ACCEPTED and
    writes outside `dest`.
  - **Deleted as unsatisfiable, with the reason, so nobody re-adds them.**
    (1) "Remove the `crossed` propagation through `_land`'s recursive call ->
    must fail `case-alias-inside-a-link-target`": measured, nothing fails.
    `_refuse_colliding_landings` runs first, resolves `B`'s target through the
    aliased `A` with `fold=True`, and refuses the root-level `..` before
    `_ancestor_crossing` is ever reached - so folded resolution, not the
    recursive `crossed` record, is what closes that escape. The recursion is
    still specified because the ancestor rule's correctness should not depend
    on another rule running first, but it has no case of its own in this suite;
    a direct unit assertion on `_land`'s `crossed` output is what would cover
    it. (2) "Remove `fold=True` from `_refuse_colliding_landings` -> must leave
    every matrix green": vacuous as a check, since it asserts nothing fails.
    (3) "Make `fold` unconditional -> expected to pass": a coverage gap, not
    evidence; see Risks.
- Regression surface: the focused five-file set under
  `-W error::DeprecationWarning` on Python 3.10, 3.12 and 3.13 (the PRD's third
  success metric), then the full gate `mise exec -- uv run pytest`.
  `NEAR_MISSES`, `SAFE_LINKS` and `LINK_CHAINS` must need no edits; an existing
  case needing a change means the fold reached further than designed.

## Review log

dispatch 1 (claude): cardinal-sin 0, blocker 3, non-blocker 4, question 1
dispatch 2 (codex): cardinal-sin 0, blocker 3, non-blocker 1, question 0
dispatch 3 (codex): cardinal-sin 0, blocker 2, non-blocker 4, question 0

**Dispatch 1 (Claude subagent)** simulated the five validation functions with
each fold site switchable and drove them with the then-current parametrisations
plus every existing matrix. Its three blockers were independently reproduced by
the caller against the real module (`/tmp/probe3-00160.py`) and all three were
fixed, which replaced the first draft's "fold throughout" with "fold the
ancestor equality test only" and changed `_fold` from `str.casefold` to
`str.lower`:

- blocker: folding `_land`'s lookup cancels the ancestor fold, so the
  directory-link shape stays accepted. Reproduced. Fixed - and this is now
  Option C, and the reason the equality test is replaced by a crossed-slot
  test rather than kept.
- blocker: folding `_land`'s cycle guard refuses a dangling `readme -> README`
  the current code accepts. Reproduced. **Later overturned by dispatch 2** - see
  below; that refusal is correct, and dispatch 1's premise (current acceptance
  proves validity) was wrong.
- blocker: `contained` does not inherit the fold "for free"; on a
  case-sensitive host folding loses a refusal and misresolves landings.
  Reproduced. Fixed, and it is why `fold` is a per-call keyword defaulting to
  off rather than a change of behaviour.

Dispatch 1 non-blockers and question, recorded and NOT fixed: `str.casefold`
over-refuses `straße.txt`/`strasse.txt` (it shaped `_fold`'s choice of
`str.lower`); folded `landings`/`files` would print a lower-cased path in the
"beneath a file member" message and add an undesigned refusal class - still
open against `_refuse_colliding_landings`, which this design does fold, so the
message there can now name a folded path and the file-plus-case-aliased-directory
shape is uncovered; the Risks claim that existing matrices assert refusal
reasons was false (corrected, and the real guard named); Option C's rejection
mis-cited `case-only-file-names-not-adjacent` (now cites `NEAR_MISSES`); and the
question about the host-dependent fail-first failure mode (recorded in Risks and
the test strategy). Dispatch 1 was not weak: 8 findings, each anchored to a
section or `file:symbol`, with measured verdict tables.

**Dispatch 2 (codex, `gpt-6-astra`)** reviewed the second draft and found three
blockers, every one of which the caller reproduced against the real module
(`/tmp/probe4-00160.py`, `/tmp/probe5-00160.py`, `/tmp/probe6-00160.py`) before
this third draft was written. All three are fixed:

- blocker: case aliases inside link targets still permit an outside write -
  `[A -> ., B -> a/../outside, B/secret.txt]`. Reproduced: ACCEPTED by the
  current code AND by the second draft's ancestor-only fold, and the manual
  path wrote `outside/secret.txt` outside the tree root. This is a second
  critical escape in R1's class. Fixed: `_land` itself now folds in the archive
  domain, and `crossed` propagates through the recursive call, so an alias
  consumed inside a target is caught. Added as
  `id="case-alias-inside-a-link-target"`.
- blocker: the required prefix-fold mutation cannot fail the proposed
  regressions, because the decisive prefixes (`a`, `alias`) are already
  lowercase. Reproduced: folding the stored-slot side alone refuses both
  second-draft cases identically, so the specified mutation was unsatisfiable.
  Fixed: inverse-case cases added
  (`case-alias-self-link-inverse`, `case-alias-directory-link-inverse`), and
  every mutation check is now paired with the specific cases it must kill.
- blocker: the acceptance control required accepting a filesystem-dependent
  self-cycle. Reproduced: `readme -> README` resolves to
  `OSError errno 62, Too many levels of symbolic links` on this host, so it is
  a self-cycle that PRD capability 1 requires refusing. Fixed: the accept-side
  control is withdrawn entirely and the archive is added as a **refusal** case,
  `id="case-equivalent-self-cycle"`. This overturns dispatch 1's second
  blocker, and is exactly the cross-model catch the second dispatch exists for.

Dispatch 2 non-blocker, recorded and NOT fixed: the refusal tests do not
establish that validation precedes extraction, since `_assert_refused_on_seam`
checks only the final exception, the sentinel and the destination, so an
implementation that extracted safely and then rejected during sealing would
satisfy them; an extraction-entry spy on both seams would close it. Real, and
left for a later cycle.

Dispatch 2 was not weak: 4 findings, each anchored to a named section, each
reproducible, and one of them overturned a prior dispatch's blocker.

**Dispatch 3 (codex verification, `gpt-6-astra`)** reviewed the third draft. It
confirmed all three of dispatch 2's blockers closed, tracing each of the six
then-specified cases through the designed control flow and noting that folded
resolution rather than the recursive `crossed` record is what closes the
target-alias escape. It then raised two new blockers, both of which the caller
reproduced (`/tmp/probe7-00160.py`) and both of which are fixed in this draft:

- blocker: the paired mutation requirements remain unsatisfiable. Reproduced,
  twice over. Dropping the `crossed` recursion fails nothing, because
  `_refuse_colliding_landings` resolves and refuses the target-alias archive
  before `_ancestor_crossing` runs; and dropping the `symlink_landings` fold
  fails only the FORWARD directory-link case, because the inverse case's
  symlink is already lower case. Fixed: every mutation is now paired with the
  exact cases it was measured to kill, three unsatisfiable mutations are
  deleted with their reasons, and the causal explanation is corrected here and
  in the test strategy.
- blocker: the excluded normalization escape contradicts the absolute safety
  metric. Reproduced, and it is a third out-of-`dest` write: this host's
  filesystem is normalization-insensitive (writing the composed `é` makes the
  decomposed spelling exist), the archive
  `[NFC("é") -> ., NFD("é")/../outside/secret.txt]` is accepted by the current
  code and by a case-only fold, and the manual path wrote
  `outside/secret.txt` outside the tree root. Fixed: `_fold` now normalizes to
  NFC before lower-casing, `id="normalization-alias-self-link"` is added as a
  seventh regression, and a mutation pins it. Measured after the fix: all seven
  cases refused, zero verdict changes across all five existing matrices.

Dispatch 3 non-blockers, recorded and NOT fixed as findings (two of them did,
however, correct false statements in this document, which are corrected rather
than restated): the three prior blockers are closed, with the causal
correction noted above; the crossed-slot rule preserves `NEAR_MISSES` and
`LINK_CHAINS`, and `git` cannot place a symlink and descendants at one path so
the new refusal does not exclude valid `git archive` output; the collision rule
did **not** become case-insensitive, because `_land` returns raw landings, so a
file `Pkg` beside `pkg/file.txt` still evades the ancestor-file comparison -
now stated correctly under Risks and left open; and the read-side exclusion is
defensible but its "expected to pass" mutant was coverage, not evidence - the
mutation is deleted and the invariant is now labelled review-backed, with the
focused regression that would close it named under Risks.

Dispatch 3 was not weak: 6 findings, each anchored to a named section, each
reproducible, and it caught two defects that two prior passes had missed.

**Honest caveat on the dispatch budget.** The 3-dispatch ceiling is spent, so
dispatch 3's two fixes - the NFC normalization in `_fold` and the re-paired
mutation list - carry caller measurement but no reviewer pass of their own. The
measurement is specific: seven refusals, zero verdict changes across
`ANCESTOR_ESCAPES` (6 entries), `COLLISIONS` (18), `NEAR_MISSES`, `SAFE_LINKS`
and `LINK_CHAINS` (2), and each surviving mutation shown to kill its named
cases. A reader who wants a fourth opinion on those two fixes has not had one.

Caller measurements behind this draft, all against the real module at
`a8347f3`: zero verdict changes across every entry of `ANCESTOR_ESCAPES` (6),
`COLLISIONS` (18), `NEAR_MISSES`, `SAFE_LINKS` and `LINK_CHAINS` (2); all seven
new cases refused where the current code accepts them; three of those seven
shown to write outside `dest` today on the manual path; and the
`[pkg/, alias -> pkg, alias/file.txt]` safe-ancestor archive now refused, which
is R3's overlap recorded in Risks.

result: ok
