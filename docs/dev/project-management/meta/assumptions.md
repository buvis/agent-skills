# Assumptions ledger — PRD 00048-trash-untracked-preview-default-v1

## 1: Split trash_dest() out of relocate()

- (Tess) The `<timestamp>` in `.dup<timestamp>` is whole epoch seconds taken at call time, as `relocate()` does today.
- (Tess) Used `tmp_path` as the root for the new tests instead of the git `repo` fixture, because neither function needs git.
- (Tess, strengthening) "Some unrelated file" means a sibling file directly in the dated trash directory.
- (Ivan) This dispatch is task 1 only (the `trash_dest()` extraction); `--apply` and the preview branch are left for task 2.
