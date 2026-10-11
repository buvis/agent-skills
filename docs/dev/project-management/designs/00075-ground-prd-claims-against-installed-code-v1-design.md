# Design: Ground PRD claims against installed code

## Architecture fit

This PRD adds a new standalone checker (`skills/create-prd/scripts/ground_prd.py`)
in the same layer as `skills/review-prd-backlog/scripts/check_links.py`: a
stdlib-only, `rg`-backed Python script invoked from two SKILL.md workflows,
never imported as a library. It has no runtime dependency on `check_links.py`
(different claim kinds, different exit semantics) but mirrors its shape —
module-level `PATTERN` regexes, a `PLACEHOLDER` filter, a `run(paths, root)`
function returning rows, a `main()` CLI with `--json` — so a reader of one
recognizes the other. It plugs into `create-prd`'s linear gate sequence
(5.5 guess-density -> **5.55 grounding** -> 5.6 model-tier) and into
`review-prd-backlog`'s step 1 mechanical floor (`check_links.py` ->
**ground_prd.py** -> lens D's manual pass), both additive, no existing gate
logic changed.

## Module placement

- **New**: `skills/create-prd/scripts/ground_prd.py` — the checker.
- **New**: `skills/create-prd/scripts/test_ground_prd.py` — contract tests.
- **Edit**: `skills/create-prd/SKILL.md` — insert `### 5.55. Grounding gate`
  between the existing `### 5.5. Guess-density gate` (line 132) and
  `### 5.6. Model-tier gate` (line 136); change 5.5's "proceed to step 5.6"
  hand-off to "proceed to step 5.55"; add the `New symbols:` authoring rule
  to step 3's guess-marking paragraph; add a `Scripts:` line to
  `## Dependencies`.
- **Edit**: `skills/review-prd-backlog/SKILL.md` — add a `Grounding
  resolution` bullet after the `Citation resolution` bullet in step 1
  (same bullet list `check_links.py` already belongs to); extend the
  Dependencies `Scripts:` line.
- **Edit**: `CHANGELOG.md` — two `### Added` entries under `[Unreleased]`.

## Interfaces & contracts

### `extract_claims(text: str) -> list[Claim]`

`Claim = namedtuple("Claim", "kind token line")` — `kind` is one of the
literal strings `"citation"`, `"symbol"`, `"library"`; `token` is the raw
matched text; `line` is the 1-indexed line number in `text`.

Pre-processing before any regex runs:
- Strip the YAML frontmatter block: if `text` starts with `^---\n`, drop
  everything up to and including the next `^---\n` line (same convention as
  every PRD/SKILL.md in this repo).
- Strip fenced code blocks (` ``` ` to ` ``` `, any info-string) by blanking
  their *content* lines (keep the line count stable so reported line numbers
  stay correct — replace each interior line with an empty string, never
  delete it).
- Skip any line containing the literal substring `link-ok:` (matches
  `check_links.py`'s `WAIVER` convention exactly — PRDs already use this
  marker for intentionally-dangling citations, and this checker must not
  double-count the same escape hatch with a different spelling).

Regexes (module-level, compiled once):

```python
CITATION_RE = re.compile(
    r"(?<![\w/])"                           # not preceded by a word char or /
    r"((?:~/|/)?[\w./-]+\.\w+)"              # path with an extension
    r":(\d+(?:-\d+)?(?:,\d+(?:-\d+)?)*)"     # :N or :N-M, comma-joined ranges
)
SYMBOL_RE = re.compile(r"`([A-Za-z_][\w]*(?:(?:::|\.)[A-Za-z_][\w]*)+|[A-Za-z_][\w]{2,})`")
NEW_SYMBOLS_RE = re.compile(r"^\s*(?:[-*]\s*)?New symbols:\s*(.*)$")
EXT_SEGMENTS = {"py", "rs", "md", "toml", "json", "jsonl", "yml", "yaml",
                "sh", "js", "ts", "txt", "lock", "html", "css"}
```

`SYMBOL_RE` only matches inline single-backtick spans (not fenced blocks,
already blanked above). A matched token is **excluded** from becoming a
`symbol` claim, per the PRD's Behavior bullet, when any of:
- its last `::`/`.`-segment is in `EXT_SEGMENTS` (file-extension-shaped,
  e.g. `` `config.yaml` ``),
- it contains `/`, whitespace, or starts with `-`,
- it matches `check_links.py`'s `PLACEHOLDER` regex verbatim (re-imported,
  see Reuse inventory): `` r"[*?<>{}$]|\.\.\.|NNNNN|XXXX|YYYY" ``.

A token surviving those exclusions gets a **provisional** `kind` of
`symbol` from `extract_claims` alone — `extract_claims(text)` has no
`root`/`registry` argument (matching the PRD's pinned `Exports` signature
exactly), so it cannot consult `known_packages` yet. `run()` reclassifies:
immediately after building `known_packages(root, registry)` (Data flow
step 3), it walks every provisional-`symbol` claim and flips `kind` to
`library` when its first `::`/`.`-segment is in that set; every claim still
`symbol` after this pass is a true symbol claim. `resolve_symbols` and
`check_library_claims` therefore run on `run()`'s post-reclassification
partition, never on `extract_claims`'s raw output directly. `Claim.kind` as
returned by `extract_claims` itself is provisional/not-yet-final; this is
intentional and keeps the PRD's `extract_claims(text)` signature
buildable.

A citation's associated symbols: the subset of **that same line's own
already-extracted claims** (the provisional `symbol`/`library` claims
`extract_claims` produced for every backtick span on that line, per the
rules above) whose `line` equals the citation's `line` — not an
independently-defined span collector. This is the "same Markdown line
names a symbol" set `check_citations` tests range-membership against.

### `check_citations(claims: list[Claim], root: Path) -> dict[Claim, str]`

Returns `{claim: status}` for every `kind == "citation"` claim, status one of
`"ok"`, `"missing"`:
- Resolve the citation's path exactly as `check_links.py:resolve_path` does:
  `~`-prefixed and absolute paths resolve via `Path(token).expanduser()`;
  anything else resolves under `root`.
- `missing` when the file does not exist, or any `N`/`M` in the range list
  exceeds the file's line count (`len(path.read_text().splitlines())`).
- Otherwise, if the citing line carried zero qualifying backtick symbols
  (per Interfaces above), status is `ok` (file+range existence only, no
  symbol check — PRD Behavior bullet 2's "a citing line with no backticked
  symbol is checked for file and range existence only").
- Otherwise `ok` only if at least one of those symbols' bare name (last
  `::`/`.`-segment) appears as a substring in the text of **any** line
  inside the cited range (1-indexed, inclusive; a single `N` is range
  `[N, N]`); else `missing`.

### `resolve_symbols(claims: list[Claim], root: Path, declared: set[str]) -> dict[Claim, str]`

Returns `{claim: status}` for every `kind == "symbol"` claim, status one of
`"ok"`, `"unresolved"`, `"declared-new"`:
- `declared-new` when `claim.token` (bare, no backticks) is in `declared` —
  built once per `run()` call across the whole PRD text, before any claim
  is checked, from every line matched by `NEW_SYMBOLS_RE`: split the
  captured text on commas, then **strip each piece of surrounding
  whitespace and backticks** (`piece.strip().strip("\`")`) before adding
  it to `declared`. The strip step is required because this repo's own
  authoring convention backtick-wraps every entry (e.g. this PRD's own
  line 114, `` New symbols: `ground_prd`, `extract_claims`, ... ``) —
  without stripping, `declared` would hold the literal tokens
  `` `ground_prd` `` (backticks attached) and never match the bare
  `claim.token` `ground_prd`, making `declared-new` unreachable for the
  PRD's own worked example and for Phase 0's happy-path acceptance test.
- Otherwise, split `claim.token` on `::`/`.` into segments; for every
  segment of length >= 3, run (via `subprocess.run`, cached per segment+root
  for the process with `functools.cache` — mirrors `check_links.py`'s
  `@functools.cache` on `resolve_path`):
  ```
  rg -F -w -q --no-messages --glob '!docs/dev/**' -- <segment> <root>
  ```
  `ok` only if every such segment's `rg` call exits 0 (segments shorter than
  3 chars are not checked — PRD Behavior: "every segment of length 3 or
  more"); any segment missing (`rg` exits 1) makes the whole claim
  `unresolved`. `rg` exiting 2 (a real error, not "no match") propagates as
  the function's own fatal error — caught by `main()` and turned into exit 2
  with the `rg` stderr on the process's stderr, per the Report/exit Feature.

### `check_library_claims(claims: list[Claim], root: Path, registry: Path) -> dict[Claim, str]`

Returns `{claim: status}` for every `kind == "library"` claim, status one of
`"ok"`, `"unverified"`, `"waived"`:
- `waived` when the claim's citing line contains the literal substring
  `(unverified library claim)`.
- Else resolve the claim's first segment (the package name) against
  `known_packages(root, registry)` (built once, memoized on
  `(root, registry)`):
  - **Cargo**: parse `<root>/Cargo.lock` with a line-oriented regex (no
    `tomllib` — stdlib-only but 3.11+, PRD pins 3.10+): for each block,
    `name = "pkg"` on one line and `version = "x.y.z"` within the next 3
    lines of the same `[[package]]` block records `pkg -> "x.y.z"`. Source
    resolution runs the actual glob, not a literal path: `matches =
    sorted(registry.glob(f"*/{pkg}-{version}"))` (the registry's single
    hash-named subdir, e.g. `src/index.crates.io-<hash>/`, is what `*`
    expands against); `source = matches[0] if matches else None`. A crate
    absent from the lock's name map is not a `library` claim at all (see
    below); a crate present in the lock but whose glob returns no match
    maps to `{"version": "x.y.z", "source": None}`, and `source is None`
    is treated identically to "does not exist" by the `unverified` rule
    below.
  - **node**: every directory name under `<root>/node_modules/` maps to
    `{"source": that directory}`.
  - **python**: every directory or `*.py` file (stem, not suffix) under
    `<root>/.venv/lib/python*/site-packages/` maps to `{"source": that
    path}` (glob `python*` once; take the first match — a repo has one venv
    Python version).
  - A package name absent from all three maps to no entry at all (not a
    `library` claim in the first place — `extract_claims` already filtered
    on this same `known_packages` set, so `check_library_claims` only ever
    sees recognized packages).
- `unverified` when the package's `source` path from the map above does not
  exist on disk (locked-but-not-installed Cargo crate, the measured B04/B09
  class), OR exists but any remaining `::`/`.`-segment fails
  `rg -F -w -q -- <segment> <source>`.
- `ok` when the source exists and every remaining segment's `rg` call
  succeeds inside it.

### `run(paths: list[Path], root: Path, registry: Path) -> dict`

```python
{"rows": [{"status": str, "kind": str, "token": str, "prd": str, "line": int,
           "detail": str}, ...],
 "blocking": int, "unverified": int}
```
One row per claim, `prd` = the claim's source file path as given on the CLI
(directory arguments already expanded, see `main()`), `detail` = a short
human string (`"file not found"`, `"line 42 exceeds 30 lines"`,
`"unresolved: segment 'frobnicate' not found"`, `"source not installed"`,
etc. — exact wording is this function's to choose, not pinned by the PRD).
`blocking` counts rows with `status in ("missing", "unresolved")`;
`unverified` counts rows with `status == "unverified"`. Declared-new counting
for the summary line happens in `main()` (status `"declared-new"` is
present in `rows` already).

### `main() -> None` (CLI)

Flags: `--root PATH` (default `.`), `--cargo-registry PATH` (default
`~/.cargo/registry/src`), `--json` (flag), positional `paths` (one or more
files or directories; a directory expands to `sorted(dir.glob("*.md"))`,
non-recursive — matches the PRD's "a directory argument expands to its
`*.md` files", and `review-prd-backlog`'s call sites pass `backlog/` and
`wip/` as flat directories of PRDs, never nested).

Before anything else: `shutil.which("rg") is None` -> print
`"ground_prd: rg not found on PATH"` to stderr, exit 2. Any path argument
that is neither a readable file nor a directory -> print
`"ground_prd: <path>: not found or unreadable"` to stderr, exit 2 (this
check and the `rg` check are the only exit-2 triggers, per the PRD's Report
Feature).

Table mode (default): one line per row,
`f"{status:10} {kind:9} {token:40} {prd}:{line}  {detail}"`, rows sorted by
`(SORT_ORDER[status], prd, line)` where
`SORT_ORDER = {"missing": 0, "unresolved": 1, "unverified": 2, "ok": 3,
"declared-new": 4}` (PRD: "sorted `missing`, `unresolved`, `unverified`,
then the rest"). Trailing summary line:
`f"{blocking} blocking, {unverified} unverified, {declared_new} declared new"`.

JSON mode: `json.dumps({"rows": [...], "blocking": n, "unverified": m},
indent=2)` to stdout — same `rows` shape as `run()`'s return value, `prd`
renamed to `file` in the emitted dict per the PRD's Outputs line
(`"status | kind | token | prd:line | detail"` for the table header, but the
PRD's Report Feature Outputs says `JSON {"rows": [...], "blocking": n,
"unverified": m}` with "the same fields per row" — this design keeps the
table's `prd` key name in both, since the PRD never requires a `file` vs
`prd` rename and consistency avoids a silent second contract; **note for the
planner**: if `plan-tasks` or the gate lens expects a specific JSON key
name, pin it there, no test in this doc depends on the exact key string).

Exit: `0` when no row has `status in ("missing", "unresolved")`, else `1`.
`unverified` rows never change the exit code (PRD, explicit).

## Data flow

1. `main()` parses args, resolves `root`/`registry` to absolute `Path`s,
   expands directory args to `*.md` files.
2. For each file: read text, strip frontmatter + fence content (keeping line
   count), run `extract_claims` to get that file's claims (each claim
   remembers its source file via a wrapper, not stored on `Claim` itself —
   `run()` zips claims with their originating path before building rows).
3. Once per invocation (not per file): build `known_packages(root,
   registry)` and the whole-PRD-corpus `declared` set (scanned across every
   file's text, since a `New symbols:` declaration in PRD A should not need
   to also appear in PRD B when `review-prd-backlog` passes two directories
   — matches the PRD's per-invocation framing, not per-file).
4. **Reclassify**: walk every claim still carrying `extract_claims`'s
   provisional `symbol` kind and flip it to `library` when its first
   `::`/`.`-segment is in `known_packages` (the rule stated in Interfaces &
   contracts). This must run after step 3 (it needs `known_packages`) and
   before step 5 (dispatch needs the final `kind`) — it is not optional and
   not folded into step 3 or step 5, because it is the one step that turns
   a provisional kind into the final kind every later step depends on.
5. Dispatch each claim to `check_citations` / `resolve_symbols` /
   `check_library_claims` by its now-final `kind`; merge the three status
   dicts into one `rows` list.
6. `run()` returns `{"rows", "blocking", "unverified"}`; `main()` renders
   table or JSON and sets the exit code.

Both call sites (`create-prd` step 5.55, `review-prd-backlog` step 1) invoke
this as a subprocess and parse stdout/exit code — no in-process import, same
integration shape `check_links.py` already has with `review-prd-backlog`.

## Reuse inventory

- **`skills/review-prd-backlog/scripts/check_links.py:30`** (`PLACEHOLDER`
  regex) and **`:67-72`** (`resolve_path`, the `~`/absolute/relative
  resolution rule) — reused verbatim by re-declaring the same two patterns
  in `ground_prd.py` (no cross-module import: the two scripts are
  independent CLIs by design, per this PRD's own module list, and
  `check_links.py` has no public API contract to import against — copying a
  10-line regex is cheaper and safer than coupling two gate scripts that
  must each keep working if the other is ever deleted). `functools.cache`
  on the symbol/package `rg` lookups mirrors `check_links.py`'s
  `@functools.cache` on `resolve_path` — same caching idiom, not a shared
  function.
- **`skills/review-prd-backlog/scripts/check_links.py:28`** (`WAIVER =
  "link-ok:"`, substring-on-line skip, used at `:82`) — reused as the
  frontmatter-adjacent
  skip rule for citation/symbol extraction; this PRD's own `(unverified
  library claim)` marker is a distinct, new waiver for library rows only,
  not a rename of this one.
- **Searches tried for an existing Cargo.lock / node_modules / site-packages
  parser** (verb/noun synonyms: `parse`/`read`/`load` x `lock`/`registry`/
  `package`): `rg -n "Cargo.lock|node_modules|site-packages" --glob '*.py'
  skills/` found only `structure_repo.py`, `survey/scripts/run.py`,
  `brush/scripts/collect_facts.py` — all three only *ignore-list* these
  directory names during repo walks (`IGNORE_GAP_DIRS`, probe-directory
  skips); none parses lockfile contents or lists installed packages.
  Nothing found; the Cargo.lock regex parser and the node_modules/
  site-packages directory listers in `check_library_claims` above are new.
- **Searched for an existing PRD-frontmatter-stripping helper** (verb/noun:
  `strip`/`parse` x `frontmatter`/`yaml`): no hits outside `create-prd`'s own
  SKILL.md prose (which documents the convention, not a reusable function).
  Nothing found; the frontmatter-strip in `extract_claims`'s pre-processing
  is new, but it is a four-line regex, not a dependency.

## Alternatives considered

1. **Chosen: one `rg`-backed stdlib script, three independent claim lenses
   sharing one CLI**, as specified. Matches `check_links.py`'s proven shape
   (same repo, same gate family, same reviewers already read that style),
   and keeps citation/symbol/library concerns in separate testable
   functions per the PRD's own `Exports` list.
2. **Smallest-diff alternative: extend `check_links.py` itself** with symbol
   and library lenses instead of a new file. Rejected: `check_links.py`'s
   claim kinds (paths, PRD numbers, memory links) and this PRD's claim kinds
   (citations, symbols, libraries) overlap only in the citation lens, and
   `check_links.py`'s `PATH_RE` is deliberately narrower (`~/.claude/`,
   `/Users/`, `docs/dev/project-management/` prefixes only) than this PRD's
   general `path:N` citation grammar (any extensioned path). Merging would
   either widen `check_links.py`'s scope for its two existing unrelated
   callers (gate bloat) or require a second regex family bolted onto one
   file — the PRD's own Structural Decomposition already calls for a
   separate file, and splitting is the smaller real diff once the two
   scripts' regex families stay distinct.
3. **Rejected: use `tomllib` for Cargo.lock.** `tomllib` is 3.11+; the PRD
   pins 3.10+ compatibility (Structural Decomposition note, Risks: "no
   `tomllib`"). A line-oriented regex over `[[package]]` blocks is adequate
   because `Cargo.lock` is machine-generated and its `name =`/`version =`
   lines never need full TOML semantics (no multi-line strings, no nested
   tables inside a package block).

## Risks & edge cases

- **Likely next change 1**: a fourth claim kind (e.g. "shell command",
  checking that a cited CLI flag exists via `--help` parsing) would slot in
  as a fourth `check_*` function plus a fourth `kind` literal; `run()`'s
  dispatch-by-`kind` pattern already generalizes to N kinds, so this design
  does not box that in.
- **Likely next change 2**: `review-prd-backlog` might want per-PRD exit
  codes instead of one aggregate run across `backlog/`+`wip/`; `run()`
  already takes a `paths` list and each row carries its own `prd` field, so
  a caller can re-group `rows` by `prd` without a script change — only
  `main()`'s current one-shot exit code would need a per-file loop, which is
  additive.
- **Likely next change 3**: an `--ignore` flag to waive specific tokens
  without the inline `(unverified library claim)`/`link-ok:` markers (for
  bulk backlog cleanup). Not designed in; would be a new CLI flag plus a set
  check in `check_library_claims`/`check_citations`, additive.
- **Likely next change 4**: resolve bare `:N-M` continuation citations
  (a second range in the same file as the paragraph's last full citation,
  written with no path — both the PRD and this design doc use this
  shorthand themselves) by tracking the last-seen path per paragraph.
  Not designed in: `CITATION_RE` requires a path with a file extension, so
  a bare continuation is silently never extracted today; adding "current
  file" tracking is a real grammar extension, additive to `extract_claims`
  only.
- **Accepted limitation — duplicate crate versions**: a `Cargo.lock` naming
  the same crate at two versions collapses to one `known_packages` entry
  (whichever `[[package]]` block is parsed last); a claim could resolve
  against the wrong installed version's source tree. Not fixed — the PRD
  gives no per-claim version pin, and this repo has no `Cargo.lock` to
  exercise the case regardless.
- **Accepted limitation — scoped npm packages**: `@scope/bar` is not
  recognized by the `node_modules` directory-name map (the npm-relevant
  name is nested one level under the `@scope` directory, not the top-level
  name). Not fixed — this repo has no `node_modules`, and the PRD's worked
  examples never cite a scoped package.
- **Accepted limitation — site-packages metadata directories**: the PRD's
  own Behavior text (Verify library claims Feature) says "every directory
  or `.py` file under `.venv/lib/python*/site-packages/`" with no
  exclusion for `*.dist-info/`, `*.egg-info/`, or `__pycache__/`, so those
  register as spurious "known packages" too. Inherited verbatim from the
  PRD; flagged here for the planner since fixing it means adding a filter
  the PRD text doesn't mention, not a design choice this doc can make
  unilaterally.
- **Edge case — symbol segment length 1-2**: PRD says "every segment of
  length 3 or more"; a 1-2 char segment (e.g. `` `os.X` ``) is simply never
  checked for that segment, so a claim made entirely of short segments
  trivially resolves `ok`. This is the PRD's own stated rule, not a design
  gap — flagged here so the planner doesn't "fix" it unasked.
- **Edge case — `rg` exit 2 mid-run**: a transient `rg` failure (not "no
  match", a real error — e.g. a target path deleted between glob expansion
  and the subprocess call) must not be silently swallowed as `unresolved`;
  `resolve_symbols`/`check_library_claims` propagate it so `main()` can exit
  2 with the real `rg` stderr, matching the only other exit-2 cause (missing
  `rg` binary) in spirit: a broken check tool fails loud, never passes
  vacuously.
- **Edge case — glob exclusion and this PRD's own designs/ directory**: the
  symbol-resolution `rg` call excludes `docs/dev/**` (`--glob '!docs/dev/**'`)
  so a name that exists only in *this* design doc or in other PRDs does not
  falsely resolve a symbol claim made in a *different* PRD — this also means
  a symbol genuinely first introduced in this design doc (e.g. `ground_prd`
  itself, before the file exists) must be declared `New symbols:` in the
  PRD, which it already is (PRD line 114).

## Test strategy outline

Per `Critical Scenarios` already enumerated in the PRD's own Test Strategy
section (happy path, edge, error cases, each naming its exact test
function) — this design doc does not restate them; `plan-tasks` copies that
section's test names directly into task Acceptance commands. The only
addition this design makes is fixture shape: every test builds its fixture
under `tmp_path` with a `.gitignore` (so `rg`'s default ignore rules don't
accidentally exclude the fixture's own fake registry — `rg -F -w` inside
`check_library_claims`'s registry search must not be defeated by a stray
`.gitignore` in the fixture tree; tests should NOT add one unless a specific
scenario needs it) and separately, where the scenario needs it, a
`Cargo.lock`, a fake registry directory tree, and the PRD markdown file
itself.

## Review log

dispatch 1 (claude): cardinal-sin 0, blocker 2, non-blocker 3, question 2
- Blocker (fixed): the Cargo `source` mapping wrote a literal `Path`
  containing a `*` character instead of actually globbing, which would
  never match a real directory and always report `unverified`. Fixed in
  `check_library_claims`'s Cargo bullet above to glob
  `registry.glob(f"*/{pkg}-{version}")` and take the first match, `None`
  on no match.
- Blocker (fixed): the Reuse inventory cited `check_links.py:82` as the
  `WAIVER` definition; `:82` is the use site inside `scan_file`, the
  definition is `:28` (the PRD itself cites `:28` correctly). Fixed.
- Non-blocker: the `resolve_path` citation span (`:67-72`, decorator
  excluded) disagrees by one line with the PRD's own `:66-71`. Not fixed —
  cosmetic citation-span drift between two documents, not a code defect;
  noted for the planner to pick either span consistently.
- Non-blocker: a `Cargo.lock` listing the same crate at two versions
  collapses to one `known_packages` entry (last-parsed wins), so a claim
  could silently resolve against the wrong installed version. Accepted as
  a documented limitation (added to Risks & edge cases below) — the PRD
  gives no per-claim way to pin a version, and this repo's own `Cargo.lock`
  usage (none; this is a Python repo) makes it untestable here regardless.
- Non-blocker: scoped npm packages (`@scope/bar`) are not recognized by the
  `node_modules` directory-name map, since the npm-relevant name is nested
  one level under the `@scope` directory. Accepted as a documented
  limitation (added to Risks & edge cases below) — this repo has no
  `node_modules` either way, and the PRD's own worked examples use Cargo
  and Python, never a scoped npm package.
- Question: `check_citations`'s bare-last-segment substring match (not a
  full-token, not word-bounded match) is looser than the PRD's prose
  implies. Resolved as intentional: the PRD's own Risks section already
  accepts this exact class of false pass ("`rg -F -w` finds a segment in
  docs or prose, not code... accepted"), and `check_citations` is PRD-
  specified to use plain substring containment within a citation range
  (no `rg` call there at all), consistent with that acceptance. No design
  change.
- Question: bare `:N-M` continuation citations (citing a second range in
  the same file as just named, with no path) never match `CITATION_RE` and
  are silently unchecked — a real blind spot, since this PRD's own prose
  and this design doc's own Reuse inventory both use that shorthand.
  Resolved as out of scope for v1: tracking "current file" across a
  paragraph to resolve bare continuations is a real grammar extension, not
  a bug in the stated design; added as Likely next change 4 in Risks &
  edge cases below rather than building it now.

dispatch 2 (claude-fallback): cardinal-sin 0, blocker 2, non-blocker 1, question 1
- codex-run.sh failed with a sandbox error (`sandbox-exec: sandbox_apply:
  Operation not permitted` on its own file-read tools inside the
  read-only sandbox); degraded to a fresh Claude reviewer per the skill's
  codex-outage fallback.
- Blocker (fixed): `extract_claims(text) -> list[Claim]` (the PRD's own
  pinned signature) has no `root`/`registry` argument, so it cannot decide
  `symbol` vs `library` at extraction time as originally written ("library
  when its first segment is in known_packages" required `root`/`registry`
  the function never receives). Fixed: `extract_claims` now emits a
  provisional `symbol` kind for every surviving backtick token;
  `run()` reclassifies to `library` in its own step 3, after
  `known_packages` is built, before dispatching to
  `resolve_symbols`/`check_library_claims`.
- Blocker (fixed): `declared-new` compared a bare `claim.token` against a
  `declared` set built by splitting `New symbols:` lines without stripping
  backticks, so a real (backtick-wrapped) declaration — including this
  PRD's own line 114 — could never match. Fixed: each split piece is now
  stripped of whitespace and backticks before joining `declared`.
- Non-blocker: `site-packages`'s directory/`.py`-file enumeration also
  registers `*.dist-info/`, `*.egg-info/`, and `__pycache__/` as spurious
  packages. Not fixed in this design — the PRD's own Behavior text names
  no such filter; recorded as an accepted limitation in Risks & edge cases
  below, flagged for the planner since excluding them would mean adding a
  rule the PRD doesn't state.
- Question (resolved): clarified that a citation's "associated symbols"
  are the same-line subset of claims `extract_claims` already produced,
  not an independently re-extracted span set. Interfaces & contracts
  updated to say so explicitly.

dispatch 3 (claude-fallback): cardinal-sin 0, blocker 1, non-blocker 0, question 0
- Run per the skill's rule that dispatch 3 is conditional on dispatch 2
  having found cardinal sins/blockers (it did, both already fixed above);
  codex failed outright again with the same sandbox error
  (`sandbox_apply: Operation not permitted`), degraded to Claude.
- Blocker (fixed): the Data flow section never described the
  reclassification step the Interfaces fix introduced — step 4 jumped
  straight from building `known_packages` to dispatching by `kind`, so a
  reader following Data flow alone (rather than cross-referencing
  Interfaces) would dispatch true library claims to `resolve_symbols`,
  reintroducing dispatch 2's bug procedurally even though Interfaces
  stated the fix. Fixed: Data flow now has an explicit numbered
  reclassify step between building `known_packages` and dispatching by
  kind.
- Verified sound, no change needed: the `declared-new` backtick-stripping
  fix (dispatch 2) correctly resolves the PRD's own backtick-wrapped
  `New symbols:` line (line 114) to bare tokens matching `claim.token`.

result: ok

