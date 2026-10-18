# Assumptions ledger — PRD 00048-trash-untracked-preview-default-v1

## 1: Split trash_dest() out of relocate()

- (Tess) The `<timestamp>` in `.dup<timestamp>` is whole epoch seconds taken at call time, as `relocate()` does today.
- (Tess) Used `tmp_path` as the root for the new tests instead of the git `repo` fixture, because neither function needs git.
- (Tess, strengthening) "Some unrelated file" means a sibling file directly in the dated trash directory.
- (Ivan) This dispatch is task 1 only (the `trash_dest()` extraction); `--apply` and the preview branch are left for task 2.

## 2: Add --apply flag; gate relocate()/note_manifest(); print DRY-RUN marker

- (Tess) In dry-run, "trash" uses the same slash-form path relative to the resolved repo root as apply mode.
- (Tess) The date in the expected trash path is `datetime.date.today().isoformat()`, as `main()` uses today; a run crossing midnight could flake.
- (Tess) "Contains the literal line" means one stderr line is exactly `DRY-RUN (use --apply)`.
- (Tess, strengthening) The marker prints exactly once per run regardless of movable-path count, including zero.
- (Ivan) The marker prints once on every run without `--apply`, even when every path is refused.
