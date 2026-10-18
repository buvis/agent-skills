## Architecture fit

`skills/survey/scripts/run.py` is the single-file implementation of the
`survey` skill's atlas builder (`_survey`, called by `main`/the CLI). This
work stays entirely inside that one module plus its test files; no other
layer or skill touches the symbol-extraction or brief-trimming code paths.

## Module placement

- Edit (no new files): `skills/survey/scripts/run.py`
  - `_extract_tree_sitter`, `_extract_file_symbols_regex`,
    `_extract_file_symbols`: add an optional `text` parameter.
  - `_compute_error_style`: add an optional `texts` parameter.
  - `_survey`: build a `texts: dict[Path, str]` by reading each sampled file
    once, thread it into the two calls above.
  - `_trim_lines_to_budget`: replace the pop loop with a binary search; add
    `_encoded_len`.
- Edit: `skills/survey/scripts/test_survey.py` - add
  `test_no_sampled_file_is_read_from_disk_twice`.
- Edit: `skills/survey/scripts/test_survey_brief.py` - add
  `test_trim_matches_the_pop_loop_byte_for_byte` and
  `test_trim_encodes_a_logarithmic_number_of_times`.

## Interfaces & contracts

```python
def _extract_tree_sitter(
    f: Path, ts_module: Any, text: str | None = None,
) -> list[tuple[str, str, int]]:
    """When text is None, read f as today (read_text(encoding="utf-8",
    errors="replace"), return [] on OSError). When text is not None, use it
    directly and skip the read."""

def _extract_file_symbols_regex(
    f: Path, text: str | None = None,
) -> list[tuple[str, str, int]]:
    """Same text-or-read rule as above; OSError on the fallback read still
    returns []."""

def _extract_file_symbols(
    f: Path, text: str | None = None,
) -> list[tuple[str, str, int]]:
    """Forwards text unchanged to _extract_tree_sitter and to all three
    _extract_file_symbols_regex call sites: the ts_module-is-None fallback
    (line 156), the tree-sitter-returned-nothing fallback (line 162), and the
    .go merge call (line 168). try_import_tree_sitter() and the existing
    fallback/.go-merge control flow are otherwise unchanged."""

def _compute_error_style(
    layers: dict[str, list[Path]], texts: dict[Path, str] | None = None,
) -> str:
    """Builds the same <=50-file sample as today. For each sampled file f:
    if texts is not None and f in texts, use texts[f]; otherwise read f
    exactly as today (same try/except OSError: continue). Sampling order,
    the 50-file cap, and the result/exception counting are unchanged."""

def _encoded_len(lines: list[str]) -> int:
    """Returns len("\\n".join(lines).encode()). Pure function, no I/O."""

def _trim_lines_to_budget(content: str, max_bytes: int) -> str:
    """Same signature and same contract as today: drop whole trailing lines
    until the joined content fits max_bytes, then drop a trailing empty line
    or a dangling `## ` header, repeating until neither holds. Internals
    change from a linear pop loop to a binary search over the prefix length
    (see Data flow) but the return value is byte-identical to the current
    implementation for every input."""
```

`_survey` (internal change, no signature change):

```python
texts: dict[Path, str] = {}
for layer_name, files in layers.items():
    for f in files:
        if f not in texts:
            try:
                texts[f] = f.read_text(encoding="utf-8", errors="replace")
            except OSError:
                pass  # extractors/compute_error_style fall back to their own read, which will also fail the same way
# then: _extract_file_symbols(f, texts.get(f))
# then: _compute_error_style(layers, texts)
```

A file that fails to read once is simply absent from `texts`; every
consumer's `texts.get(f)` returns `None` for it and the consumer takes its
own read-and-fail-the-same-way path, so the observable behavior for an
unreadable file is unchanged.

## Data flow

Today: `_survey` calls `_extract_file_symbols(f)` once per sampled file
(reads `f`), and separately `_compute_error_style(layers)` re-reads up to 50
of those same files. A `.go` file is read twice more inside
`_extract_file_symbols` itself (the primary extractor's read, then the merge
call to `_extract_file_symbols_regex(f)`).

After this change: `_survey` reads each sampled file at most once into
`texts`, and that string is reused by every consumer that needs it
(`_extract_file_symbols` forwards it through all three of its own
`_extract_file_symbols_regex` call sites - the `ts_module is None` fallback
at line 156, the tree-sitter-returned-nothing fallback at line 162, and the
`.go` merge call at line 168 - plus `_compute_error_style` looking it up by
path). A file not in `texts` (read failure) is read fresh by whichever
extractor needs it, reproducing today's per-call failure handling exactly.

`_trim_lines_to_budget`: today, each loop iteration re-joins and re-encodes
the shrinking line list (`len("\n".join(lines).encode())`), which is what
makes the loop quadratic in the number of lines dropped. The replacement
binary-searches the largest prefix length `k` (`0 <= k <= len(lines)`) such
that `_encoded_len(lines[:k]) <= max_bytes`, using `_encoded_len` as the
monotonic predicate (dropping a line strictly shrinks or holds the encoded
length, so the predicate is monotonic and binary search is valid). Then it
applies the existing trailing-blank/`## `-header cleanup to `lines[:k]`
exactly as today, in a loop (a single cleanup pass can expose a new trailing
blank/header, same as the current code's `while` loop at the cleanup step).

## Reuse inventory

Searched `skills/survey/scripts/run.py` for an existing single-read cache or
memoization helper over file text: no `texts`, `_cache`, `@lru_cache`, or
`functools.cache` use in the file (`rg -n "cache|memo" skills/survey/scripts/run.py`
- 0 hits). Searched for an existing binary-search or bisect-based trim helper:
`rg -n "bisect|binary.search" skills/survey/scripts/run.py` - 0 hits; `bisect`
is stdlib but the search space here (an integer prefix-length over a
monotonic encoded-length predicate, not a sorted value list) doesn't map
onto `bisect.bisect_left`/`bisect_right` directly, so a small manual
`lo, hi` loop is used instead of forcing `bisect` onto a shape it doesn't
fit.
Nothing found to reuse; both changes are new, scoped to this one file.

## Alternatives considered

1. **Smallest-diff: cache via a plain dict built inline in `_survey`, no
   signature changes** - wrap `Path.read_text` with a memoizing helper
   closure and monkeypatch it in at call time. Rejected: it would make the
   "read once" guarantee depend on patching a stdlib method for the
   duration of one call, which is fragile under concurrent test monkeypatching
   (the existing `test_regex_fallback_used_when_tree_sitter_extraction_returns_empty`
   test already monkeypatches `_extract_tree_sitter` directly) and harder for
   a reviewer to verify than an explicit `texts` parameter.
2. **Chosen: optional `text`/`texts` parameters, default `None`, explicit
   `_survey`-built dict** - the PRD's own stated shape. Every existing
   single-argument call site (test or production) keeps working untouched;
   the new behavior is additive and opt-in per call.
3. **Larger: a `FileCache` class wrapping all of `read_text`, `exists`, etc.
   across the whole module** - rejected as unrequested scope: nothing else
   in `run.py` re-reads a file more than once per `_survey` call (scan and
   layer-building are a single pass over the filesystem, not file contents),
   so a general-purpose cache class would add an abstraction with exactly
   one real caller.

For the trim: the PRD's binary-search replacement is already the
smallest-diff option that meets the logarithmic-calls requirement; a
Timsort-style merge or a streaming byte-counter were considered and rejected
as solving a problem (exact byte accounting mid-stream) the binary search
does not have, since `_encoded_len` on a prefix is cheap and exact.

## Risks & edge cases

- **`texts` growing large**: for a repo at the existing scan cap (per PRD
  00030/00079's layer scanning), `texts` holds every sampled file's decoded
  text simultaneously instead of one at a time. This is the PRD's own
  stated and accepted tradeoff (the measured 28.9 MB re-encode is the thing
  being removed, not relocated) - no mitigation needed here, but a future
  change that lowers the sampling cap should re-check this dict's peak size.
- **A `.go` file whose primary read failed**: `texts.get(f)` is `None`, so
  `_extract_file_symbols` calls `_extract_tree_sitter(f, ts_module, None)`
  and `_extract_file_symbols_regex(f, None)`, each doing its own
  `read_text` and hitting the same `OSError`. Both fail the same way, so the
  "empty symbol list for an unreadable file" behavior is preserved without
  special-casing it.
- **Binary search off-by-one**: the loop invariant must be "largest `k` with
  `_encoded_len(lines[:k]) <= max_bytes`" using a half-open `[0, len(lines)]`
  search space; `test_trim_matches_the_pop_loop_byte_for_byte` pins this
  against the original pop loop at four budgets (0, 64, 512, 5120) across
  four content shapes so an off-by-one in either direction fails a test, not
  a future caller.
- **Likely next changes**: (1) a cap on `texts`' total bytes if a future
  layer-count increase makes peak memory a real constraint - this design's
  plain `dict[Path, str]` composes with a future LRU-style bound without
  changing any call site; (2) extending the single-read discipline to a
  future third consumer of file text in `_survey` - the `text`/`texts`
  optional-parameter pattern established here is the one to repeat, not a
  new caching mechanism.

## Test strategy outline

- `test_no_sampled_file_is_read_from_disk_twice` (new, `test_survey.py`):
  monkeypatch `pathlib.Path.read_text` to record `self` per call and
  delegate to the original; build a repo with >=60 `.py` files across two
  layers plus one `.go` file; call `run._survey(repo)`; assert
  `len(calls) == len(set(calls))`. This is the fail-first test: it fails
  against the current `run.py` (which reads sampled files twice via
  `_compute_error_style` and `.go` files three times) and passes after.
- `test_trim_matches_the_pop_loop_byte_for_byte` (new,
  `test_survey_brief.py`): define the current pop loop inline as
  `_reference_trim`, compare its output against
  `run._trim_lines_to_budget` across empty content, content already under
  budget, content cut mid-list, and content whose last surviving line is a
  `## ` header, at budgets 0, 64, 512, 5120 - pins the no-behavior-change
  requirement directly, not via a wall-clock measurement.
- `test_trim_encodes_a_logarithmic_number_of_times` (new,
  `test_survey_brief.py`): monkeypatch `run._encoded_len` with a counting
  wrapper that delegates to the original; trim 600 lines of 40 characters
  each to 5120 bytes; assert the counter is `<= 12` (`ceil(log2(601)) + 2 =
  12`), against the measured 1,052 pop-loop iterations at that size.
- The eight existing `_extract_file_symbols(f)` single-argument call sites
  in `test_survey.py` (lines 127, 163, 192, 231, 265, 285) and the two
  `_compute_error_style(layers)` call sites (lines 337, 374) are left
  untouched; they exercise the `text=None`/`texts=None` fallback path and
  must keep passing unmodified as the regression guard for backward
  compatibility.

## Review log

- non-blocker: binary search always runs ~log2(n) `_encoded_len` calls even when content already fits budget (optimization only, not required).
- question: the `ceil(log2(n+1))+2` call-count bound is asserted, not derived from explicit loop pseudocode; the test will still catch a regression either way.

dispatch 1 (claude): cardinal-sin 0, blocker 1, non-blocker 1, question 1

dispatch 2: codex unavailable (sandbox could not read the review files), Claude fallback
- question: binary search's behavior under a negative `max_bytes` is unspecified (reachable via `_append_footer`'s budget-minus-footer accounting); none of the four pinned test budgets drive it negative.
- non-blocker: `texts` is sized to extraction's full sampled-file set, not `_compute_error_style`'s <=50-file sample; already covered by the Risks section's memory-growth caveat.

dispatch 2 (claude-fallback): cardinal-sin 0, blocker 0, non-blocker 1, question 1
