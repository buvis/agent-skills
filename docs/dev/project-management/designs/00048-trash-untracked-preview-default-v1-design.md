# Design: Give `trash_untracked` a preview default behind `--apply`

## Architecture fit

`trash_untracked.py` is a standalone CLI helper under `skills/brush/scripts/`,
invoked by the `brush` skill's Phase-2 instructions and copied verbatim into
its report template. It has no module boundary beyond the file itself: a
single `main()` drives veto -> relocate -> manifest. The fix stays inside
this file plus the two doc call sites named in the PRD; no new module or
layer is introduced.

## Module placement

- Edit `skills/brush/scripts/trash_untracked.py`:
  - add `trash_dest(root, rel, date) -> Path` (new function, extracted from
    `relocate()`)
  - edit `relocate()` to call `trash_dest()`
  - add `--apply` to the `argparse` parser in `main()`
  - edit `main()`'s per-path loop to branch on `args.apply`
- Edit `skills/brush/scripts/test_brush_scripts.py`: add
  `test_preview_moves_nothing`, `test_preview_json_matches_the_apply_run`;
  add `--apply` to the `sys.argv` lists of the two existing tests that drive
  `tu.main()` and assert an actual move happened -
  `test_manifest_row_names_the_file_that_was_moved` (around line 195-209) and
  `test_main_reports_one_identity_for_a_moved_path_with_spaces` (around line
  326-350) - since once `--apply` defaults to off, both would otherwise fail
  (no move, no manifest row, file still present).
- Edit `skills/brush/SKILL.md` line 63: append `--apply`
- Edit `skills/brush/references/report-template.md` line 27: append `--apply`

No new files.

## Interfaces & contracts

```python
def trash_dest(root: Path, rel: str, date: str) -> Path:
    """Where `rel` would land under root/docs/dev/tmp/.trash/<date>/.

    Pure path arithmetic, no filesystem mutation other than reading
    `.exists()` to apply the `.dup<ts>` collision suffix - matches today's
    relocate() behaviour exactly, so a dry run and the apply run that follows
    report the same `trash` path as long as no new collision appears between
    the two invocations.
    """
    dest = root / "docs/dev/tmp/.trash" / date / rel
    if dest.exists():
        ts = int(datetime.datetime.now().timestamp())
        dest = dest.with_name(f"{dest.name}.dup{ts}")
    return dest


def relocate(root: Path, rel: str, date: str) -> str:
    """Unchanged contract. Now implemented as:

        dest = trash_dest(root, rel, date)
        dest.parent.mkdir(parents=True, exist_ok=True)
        shutil.move(str(root / rel), str(dest))
        return dest.relative_to(root).as_posix()
    """
```

`main()`'s `argparse` gains:

```python
ap.add_argument("--apply", action="store_true",
                 help="move files to .trash (default: dry-run)")
```

`main()`'s per-path loop, after `veto_reason` passes (`reason is None`):

```python
if args.apply:
    trash_rel = relocate(root, rel, date)
    note_manifest(root, date, args.rule, rel, trash_rel)
else:
    trash_rel = trash_dest(root, rel, date).relative_to(root).as_posix()
moved.append({"path": rel, "trash": trash_rel})
```

(the apply branch goes straight to `relocate()`, which calls `trash_dest()`
internally - no redundant call; the preview branch computes `trash_dest()`
once and skips the mutation.)

After the loop, when `not args.apply`:

```python
print("DRY-RUN (use --apply)", file=sys.stderr)
```

placed right before the existing `print(json.dumps(...))` so stdout order is
unaffected and stays parseable JSON; the marker goes to stderr only.

`SKILL.md:63` becomes:

```
   `python3 ~/.agents/skills/brush/scripts/trash_untracked.py --repo <root> --apply <paths>`
```

`report-template.md:27` becomes:

```
- [ ] BR-3 (trash-scratch) age=12d - `scratch_bench.py`, unreferenced - cmd: `python3 ~/.agents/skills/brush/scripts/trash_untracked.py --repo <root> --rule brush-scratch --apply scratch_bench.py`
```

## Data flow

Unchanged shape: CLI args -> `repo_root()` -> `load_tracked()` -> per-path
`veto_reason()` -> (preview: `trash_dest()` only | apply: `relocate()` +
`note_manifest()`) -> one JSON object on stdout. The only new branch is the
`args.apply` check gating the two side-effecting calls; `trash_dest()` is a
pure read of the destination path for both branches, so `moved[].trash` is
populated identically in both modes except for the rare mid-run collision
case the PRD already excludes (same corpus, two back-to-back runs, no new
file appears at the destination between them).

## Reuse inventory

- `skills/purge-devtmp/scripts/purge_devtmp.py:195-220` - the sibling script's
  existing `--apply` flag and its `DRY-RUN (use --apply)` stderr line are the
  exact precedent this PRD asks to mirror. Read, not imported (different
  module, no shared helper worth extracting for one flag + one print).
- `skills/brush/scripts/test_brush_scripts.py` - `_veto()`/`_git()`/`repo`
  fixture already drive `trash_untracked.py` through
  `monkeypatch.setattr("sys.argv", ...)`; both new tests reuse this fixture
  and pattern directly (see `test_manifest_row_names_the_file_that_was_moved`
  for the closest existing shape).
- nothing found for a shared "destination path" helper elsewhere in the repo;
  greps tried: `rg -n "trash_dest|dest.*trash" skills`, `rg -n "DRY-RUN" skills`
  (only the purge-devtmp hit above), `rg -n "def relocate" skills`.

## Alternatives considered

1. **Smallest-diff version: inline the destination computation twice**
   (compute `dest` identically in both the preview branch and inside
   `relocate()`, no shared helper). Rejected: the PRD's acceptance criterion
   that preview and apply report byte-identical `trash` values is exactly
   the kind of duplication that drifts when one copy is edited later; a
   single `trash_dest()` makes drift impossible instead of merely unlikely.
2. **Separate `--dry-run` flag instead of `--apply`** (preview is the
   explicit opt-in). Rejected: the PRD requires preview-by-default to match
   the sibling script and to close the agoke finding that every invocation
   moves files on the first call; an opt-in dry-run leaves today's unsafe
   default unchanged.
3. **Chosen: `trash_dest()` extracted once, `--apply` gates the two
   mutating calls, preview reuses the same loop.** One new function, one new
   flag, no new control-flow shape - the design above. The extra size over
   option 1 buys the identity guarantee the acceptance criteria require.

## Risks & edge cases

- A caller outside this repo that does not add `--apply` silently gets
  preview-only behaviour instead of moves - the PRD already names this as a
  human follow-up, not something this change can detect from inside the repo.
- Mid-run collision: if a file is created at the computed `trash_dest()`
  path between a preview run and the following apply run, the two runs'
  `trash` values can legitimately differ (the `.dup<ts>` suffix is
  timestamp-based). Not a regression - `relocate()` already carried this
  behaviour - but worth a comment at `trash_dest()` since the PRD's "same
  corpus, run twice" acceptance test assumes no such collision.
- Intra-run collision is also preview-blind: in apply mode each loop
  iteration actually moves a file, so a second path in the same invocation
  landing on the same destination sees `dest.exists() == True` and gets the
  `.dup<ts>` suffix; in preview mode nothing is written, so two colliding
  paths in one preview invocation both compute the identical destination
  with no suffix. The "preview JSON matches the apply run" guarantee is
  scoped to corpora with no duplicate destinations within a single run.
- Likely next changes after this PRD: (1) PRD 00044 (on hold) also touches
  this file - whoever resumes it should rebase onto the `trash_dest()` split
  rather than re-duplicating the path arithmetic; (2) a future `--apply`
  default flip (inverting the flag's polarity) would only need to touch the
  `action="store_true"` default and the two doc call sites, since the gate
  is centralized on `args.apply`.

## Test strategy outline

- `test_preview_moves_nothing`: age a file past `--min-age-days`, run
  `main()` without `--apply`, assert the file still exists, `.trash/` was
  never created, and stdout's `moved` has exactly one entry for it.
- `test_preview_json_matches_the_apply_run`: run the same corpus through
  `main()` twice (once without `--apply`, once with), parse both stdouts,
  assert equality, and assert `manifest.tsv` exists only after the second
  (apply) run.
- Existing `test_relocate_writes_manifest_row` must keep passing unedited
  after `relocate()` is rewritten to call `trash_dest()` - it is the PRD's
  own regression guard on that refactor (Task 1's acceptance check).
- Existing `test_manifest_row_names_the_file_that_was_moved` and
  `test_main_reports_one_identity_for_a_moved_path_with_spaces` need
  `--apply` added to their `sys.argv` lists, since both assert an actual
  move happened and would otherwise fail once preview is the default.
- Full suite (`uv run pytest -q`) as the final gate (Task 5).

## Review log

- non-blocker: `trash_dest()` would be computed twice on the apply path if
  called unconditionally before branching on `args.apply`; fixed by only
  calling it directly in the preview branch (apply goes straight to
  `relocate()`, which calls it internally).
- non-blocker: an earlier draft's pseudocode carried a stray `tu.` prefix
  and an explanatory comment that didn't belong in a single-module script;
  removed.
- question: in preview mode the `moved[].trash` value is a predicted path
  that is never created, reported under the same `"trash"` key the apply
  run uses for an actual path. Intentional per the PRD's "same JSON shape"
  requirement; the stderr `DRY-RUN (use --apply)` marker is the documented
  signal that the path is predictive, not actual.
- question: `test_preview_json_matches_the_apply_run` relies on the preview
  run never touching the corpus's mtimes so the second (apply) run's
  `--min-age-days` check still passes - true because preview makes no
  filesystem writes, but worth stating explicitly in the test itself when
  it is written.
- question (dispatch 3): the "DRY-RUN" stderr marker has no test asserting on
  its content - not a defect, optional follow-up.
- question (dispatch 3): mid-run and intra-run `.dup<ts>` collision caveats
  are documented in Risks & edge cases but untested - accepted limitation,
  explicitly out of this PRD's scope.
- dispatch 1 (claude): cardinal-sin 0, blocker 0, non-blocker 2, question 2
- dispatch 2 (claude-fallback): cardinal-sin 0, blocker 1, non-blocker 0, question 1
- dispatch 3 (claude-fallback): cardinal-sin 0, blocker 0, non-blocker 0, question 2
