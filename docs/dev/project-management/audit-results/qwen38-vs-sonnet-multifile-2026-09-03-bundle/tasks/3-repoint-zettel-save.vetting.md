# Task 3 - gems / repoint MarkdownZettelRepository.save to atomic_write_text

Stage A prospect 3. Verdict: **eligible**.

Kind: impl+test

Repo: `/Users/bob/git/src/github.com/buvis/gems` (Python)
PRD: `dev/local/prds/done/00041-atomic-write-foundation-v1.md:40`

Commit run: `a4fa75b1..30b42c3b` (2 commits: `a4fa75b1` test, `30b42c3b` fix)
Parent of `<first>` (`a4fa75b1^`): `fc7df0c30a90d2a14d817ea7771bdc17d4b49fdc`
(verified with `git -C <src> rev-parse a4fa75b1^`)
Base sha (`HEAD` at vetting time): `7d7f9d8a1fea3160650ee4eab6589d30cb4b6edf`

## Reverifiability

Working tree clean at `<base-sha>`: `git -C <src> status --porcelain` printed
nothing; control `git -C <src> status --porcelain --branch` printed
`## master...origin/master`.

Raw test command:

    uv --directory <tree> run pytest tests/lib/zettel/infrastructure/persistence/test_markdown_zettel_repository_writer.py -q

Run once at `<base-sha>` against the source tree: **exit 0**,
`7 passed in 0.06s`.

## Required files

- `src/lib/buvis/pybase/zettel/infrastructure/persistence/markdown_zettel_repository/markdown_zettel_repository.py` (impl)
- `tests/lib/zettel/infrastructure/persistence/test_markdown_zettel_repository_writer.py` (test) - CHANGED by the task

Ancillary files: none

`multi_file`: 2 Required files, 1 `impl` + 1 `test` the task changed.

## History per Required file

    git -C <src> log --oneline --name-only 30b42c3b..HEAD -- <both Required paths>

Output:

    67f777ac fix(zettel): isolate non-mapping parse failures and keep bracketed filenames in the warning
    src/lib/buvis/pybase/zettel/infrastructure/persistence/markdown_zettel_repository/markdown_zettel_repository.py
    757235f1 fix(zettel): surface find_all parse errors across Rust and Python backends
    src/lib/buvis/pybase/zettel/infrastructure/persistence/markdown_zettel_repository/markdown_zettel_repository.py
    b636774e refactor(bim): split sync_note execute into per-branch helpers and drop redundant encoding args
    src/lib/buvis/pybase/zettel/infrastructure/persistence/markdown_zettel_repository/markdown_zettel_repository.py

Verdicts:

- `markdown_zettel_repository.py`: 3 later commits -> **`surgical`**
- `test_markdown_zettel_repository_writer.py`: `empty` -> `whole-file`

### Why markdown_zettel_repository.py needs a surgical revert

The whole-file reverse hunk for `save` no longer matches today's file:
`b636774e ... drop redundant encoding args` rewrote the very line this task
introduced, from

    atomic_write_text(Path(data.file_path), formatted, encoding="utf-8")

to

    atomic_write_text(Path(data.file_path), formatted)

`git apply --check` on the naive reverse patch fails on exactly that hunk
(`patch failed: ...markdown_zettel_repository.py:53`). The other two later
commits (`67f777ac`, `757235f1`) touch `find_all`'s parse-error path only, and
are confirmed clear of `save`.

The hand-written reverse patch restores the pre-task body
`Path(data.file_path).write_text(formatted, encoding="utf-8")` against today's
one-argument call, and drops the module-level
`from buvis.pybase.filesystem import atomic_write_text` import. It keeps
`b636774e`'s and `757235f1`'s work everywhere else in the file.

## Reverse patch

`3-repoint-zettel-save.reverse.patch` = hand-written surgical diff for the impl
file plus

    git -C <src> diff 30b42c3b fc7df0c3 -- tests/lib/zettel/infrastructure/persistence/test_markdown_zettel_repository_writer.py

for the test file.

`git -C /Users/bob/git/src/github.com/buvis/gems apply --check -v <patch>`:
clean, both files.

Pretask: 079ccaedba67c1efa9e947d8f7d5c8a84a8a5af6

Necessity:
- `src/lib/buvis/pybase/zettel/infrastructure/persistence/markdown_zettel_repository/markdown_zettel_repository.py`: exit 1, first failure: `Failed: DID NOT RAISE OSError` (test_save_propagates_atomic_write_failure_and_leaves_file_unchanged)
- `tests/lib/zettel/infrastructure/persistence/test_markdown_zettel_repository_writer.py`: n/a (test file - necessity is enforced at scoring by dropped/own/ablate)

## Pinned interface

The prompt's `Names the acceptance gate binds to` block reads, verbatim:

- none - every name the gate binds to already exists in the tree.
  `atomic_write_text` is already exported from `buvis.pybase.filesystem` and
  implemented in the module `buvis.pybase.filesystem.atomic_write`; the
  regression case patches `os.replace` inside that module, so the write must go
  through it rather than through a hand-rolled temp-file dance.

Why the list is empty. Everything the canonical
`tests/lib/zettel/infrastructure/persistence/test_markdown_zettel_repository_writer.py`
binds to:

Named verbatim in the prompt (ledger line):

- `MarkdownZettelRepository.save`
- `atomic_write_text`

Present in the reverted tree:

- `buvis.pybase.filesystem.atomic_write` (the module the test patches
  `os.replace` on; created by the upstream Phase 0 task, not reverted here) and
  its export `atomic_write_text` from `buvis.pybase.filesystem`
- `buvis.pybase.zettel.domain.entities.zettel.zettel.Zettel`
- `buvis.pybase.zettel.domain.value_objects.zettel_data.ZettelData` and its
  `file_path`
- `buvis.pybase.zettel.infrastructure.formatting.markdown_zettel_formatter.markdown_zettel_formatter.MarkdownZettelFormatter.format`
  (patch target)
- `ValueError` for a missing `file_path` (pre-existing guard)
- `pytest_mock.MockerFixture`

The one behaviour the canonical test adds -
`test_save_propagates_atomic_write_failure_and_leaves_file_unchanged`, which
forces `buvis.pybase.filesystem.atomic_write.os.replace` to raise and requires
the original file to survive - is satisfiable only by calling
`atomic_write_text` from `buvis.pybase.filesystem`, which the ledger line names
explicitly. Nothing here is a name the engine would have to invent.

Canonical test files copied:

- `tests/lib/zettel/infrastructure/persistence/test_markdown_zettel_repository_writer.py`
  -> `3-repoint-zettel-save.canonical/tests/lib/zettel/infrastructure/persistence/test_markdown_zettel_repository_writer.py`

## Notes

- Smallest unit in the set: the impl side is a two-line change (one import, one
  call). Useful as the eval's floor - an engine that fails this one is failing
  on multi-file mechanics, not on difficulty.
