# Task 1 - gems / repoint bim doc callers to pybase.filesystem

Stage A prospect 1. Verdict: **eligible**.

Kind: impl+caller

Repo: `/Users/bob/git/src/github.com/buvis/gems` (Python)
PRD: `dev/local/prds/done/00041-atomic-write-foundation-v1.md:42`

Commit run: `d29dab6f..4d23c02d` (7 commits: `d29dab6f`, `3fd57f22`, `c1d56718`,
`0297744b`, `9acda22c`, `1cc94082`, `4d23c02d`)
Parent of `<first>` (`d29dab6f^`): `84e994cde859bcbeaa0a7b073b4d79fbb8a9286e`
(verified with `git -C <src> rev-parse d29dab6f^`)
Base sha (`HEAD` at vetting time): `7d7f9d8a1fea3160650ee4eab6589d30cb4b6edf`

## Reverifiability

Working tree clean at `<base-sha>`: `git -C <src> status --porcelain` printed
nothing; the control run `git -C <src> status --porcelain --branch` printed
`## master...origin/master`, so the empty result is a real "clean", not a
silent command failure.

Raw test command (the ledger's own acceptance clause, as an `&&`-chain; the
executor runs the segments one at a time, each tree-relative, prefixing the
tree):

    test ! -e src/tools/bim/commands/doc/shared/atomic_write.py && ! rg -q "shared\.atomic_write|shared/atomic_write" src/tools/bim tests/tools/bim && uv run pytest tests/tools/bim/doc -q

Verified segment by segment at `<base-sha>` in the source tree, 2026-09-02:

- segment 1: `ls` on
  `/Users/bob/git/src/github.com/buvis/gems/src/tools/bim/commands/doc/shared/atomic_write.py`
  -> `No such file or directory`, so `test ! -e` **exits 0**.
- segment 2: `rg -n "shared\.atomic_write|shared/atomic_write"` over
  `src/tools/bim` and `tests/tools/bim` printed **nothing**, so `! rg -q`
  **exits 0**. Two controls prove the empty result is real, not a regex
  misfire: the same search for `atomic_write` alone returns `28 matches ... 14
  files contained matches`, and the same alternation with one live branch
  (`shared\.atomic_write|shared\.zettel_writer`) returns 12 files.
- segment 3: `uv --directory /Users/bob/git/src/github.com/buvis/gems run
  pytest tests/tools/bim/doc -q` -> **exit 0**, `977 passed in 1.86s`.

## Required files

- `src/tools/bim/commands/doc/shared/atomic_write.py` (impl) - deleted by the task
- `src/tools/bim/commands/doc/shared/zettel_writer.py` (caller)
- `src/tools/bim/commands/doc/shared/issuers.py` (caller)
- `src/tools/bim/commands/doc/shared/ocr.py` (caller)
- `src/tools/bim/commands/doc/shared/triage.py` (caller)
- `src/tools/bim/commands/doc/shared/pipeline.py` (caller)
- `src/tools/bim/commands/doc/audit/reporter.py` (caller)
- `tests/tools/bim/doc/test_atomic_write.py` (test) - deleted by the task

Ancillary files: none

`multi_file`: 8 Required files, >= 1 `impl` plus >= 1 `caller` the same task
changed. The one `test` file was deleted, not added or changed, so the kind is
`impl+caller` and there are no canonical test copies.

## History per Required file

Command run once for the whole set:

    git -C <src> log --oneline --name-only 4d23c02d..HEAD -- <the 8 Required paths>

Output (only one Required path appears):

    26d2def6 fix(bim): treat a non-text claimed_at as an abandoned claim instead of raising
    src/tools/bim/commands/doc/shared/pipeline.py
    f6ecadd1 fix(bim): tell the truth about a document still awaiting triage review
    src/tools/bim/commands/doc/shared/pipeline.py
    b919d7ad fix(bim): record raw source sha on triage and promote
    src/tools/bim/commands/doc/shared/pipeline.py
    fc87d99f fix(bim): release ingest claim on any exit and reclaim stale claims
    src/tools/bim/commands/doc/shared/pipeline.py
    bdcc8e1a refactor(bim): relocate collision resolver to shared naming module
    src/tools/bim/commands/doc/shared/pipeline.py

Verdicts:

- `src/tools/bim/commands/doc/shared/atomic_write.py`: `empty` -> `whole-file`
- `src/tools/bim/commands/doc/shared/zettel_writer.py`: `empty` -> `whole-file`
- `src/tools/bim/commands/doc/shared/issuers.py`: `empty` -> `whole-file`
- `src/tools/bim/commands/doc/shared/ocr.py`: `empty` -> `whole-file`
- `src/tools/bim/commands/doc/shared/triage.py`: `empty` -> `whole-file`
- `src/tools/bim/commands/doc/shared/pipeline.py`: 5 later commits -> **`surgical`**
- `src/tools/bim/commands/doc/audit/reporter.py`: `empty` -> `whole-file`
- `tests/tools/bim/doc/test_atomic_write.py`: `empty` -> `whole-file`

`clean_history`: the two files the task DELETED (`atomic_write.py`,
`test_atomic_write.py`) have empty later history, so re-adding them is exact.
The task-ADDED-file trap does not apply here - this task added no file.

### Why pipeline.py needs a surgical revert

`bdcc8e1a refactor(bim): relocate collision resolver to shared naming module`
rewrote the `from bim.commands.doc.shared.naming import ...` line that sits two
lines below the import this task changed, so the whole-file reverse hunk's
context no longer matches. The other four later commits (`26d2def6`,
`f6ecadd1`, `b919d7ad`, `fc87d99f`) all sit in claim/triage logic far from the
import block and are confirmed pure - they never touch the
`atomic_write_text` import or any `atomic_write_text(` call site.

The hand-written reverse hunk for `pipeline.py` is the last hunk of
`1-repoint-bim-doc-callers.reverse.patch`: it drops
`from buvis.pybase.filesystem import atomic_write_text` and restores
`from bim.commands.doc.shared.atomic_write import atomic_write_text`, using
today's `naming` import line as context.

## Reverse patch

`1-repoint-bim-doc-callers.reverse.patch` = the seven `whole-file` files from

    git -C <src> diff 4d23c02d 84e994cd --output=<abs>/tasks/1-repoint-bim-doc-callers.reverse.patch -- <the 7 non-pipeline Required paths>

plus the hand-written `pipeline.py` hunk appended.

`git -C /Users/bob/git/src/github.com/buvis/gems apply --check -v <patch>`:
clean, all 8 files.

Pretask: e0b3b1bf841c455c191ce405491866908ad75fd4

Necessity:
- `src/tools/bim/commands/doc/shared/atomic_write.py`: exit 1, first failure: `test ! -e src/tools/bim/commands/doc/shared/atomic_write.py`
- `src/tools/bim/commands/doc/shared/zettel_writer.py`: exit 1, first failure: `! rg -q "shared\.atomic_write|shared/atomic_write" src/tools/bim tests/tools/bim`
- `src/tools/bim/commands/doc/shared/issuers.py`: exit 1, first failure: `! rg -q "shared\.atomic_write|shared/atomic_write" src/tools/bim tests/tools/bim`
- `src/tools/bim/commands/doc/shared/ocr.py`: exit 1, first failure: `! rg -q "shared\.atomic_write|shared/atomic_write" src/tools/bim tests/tools/bim`
- `src/tools/bim/commands/doc/shared/triage.py`: exit 1, first failure: `! rg -q "shared\.atomic_write|shared/atomic_write" src/tools/bim tests/tools/bim`
- `src/tools/bim/commands/doc/shared/pipeline.py`: exit 1, first failure: `! rg -q "shared\.atomic_write|shared/atomic_write" src/tools/bim tests/tools/bim`
- `src/tools/bim/commands/doc/audit/reporter.py`: exit 1, first failure: `! rg -q "shared\.atomic_write|shared/atomic_write" src/tools/bim tests/tools/bim`
- `tests/tools/bim/doc/test_atomic_write.py`: exit 1, first failure: `! rg -q "shared\.atomic_write|shared/atomic_write" src/tools/bim tests/tools/bim`

## Pinned interface

The prompt's `Names the acceptance gate binds to` block reads, verbatim:

- none - every name the gate binds to already exists in the tree. The
  replacement functions `atomic_write_text(path, text)` and
  `atomic_write_bytes(path, data)` are already exported from
  `buvis.pybase.filesystem`; the gate reads no name this task has to invent.

Why the list is empty. The names the gate touches are all either in the ledger
line the prompt carries verbatim - `atomic_write`, `buvis.pybase.filesystem`,
`doc/shared/atomic_write.py`, `src/tools/bim` - or already in the reverted
tree: `atomic_write_text` and `atomic_write_bytes` live in
`src/lib/buvis/pybase/filesystem/`, created by the Phase 0 task that is
upstream of this one and not reverted, and 12 other call sites under
`src/tools/bim` already import them (`rg atomic_write` returns 28 matches
across 14 files). The engine reads them rather than inventing them.

Canonical test files copied: none (kind is `impl+caller`).

## Notes

Gate strength, the three properties the `&&`-chain has to have:

**(a) It exits 0 at `<base-sha>`.** Verified segment by segment above; all
three exit 0.

**(b) It exits non-zero on the pre-task tree.** Reasoning from the reverse
patch: the patch re-creates
`src/tools/bim/commands/doc/shared/atomic_write.py` (it is a whole-file revert
of a file this task DELETED, so the reverse hunk is a pure file creation).
Segment 1 is `test ! -e` on exactly that path, so it exits 1 the moment the
patch lands, and the chain stops there. The pre-task tree therefore cannot pass
the gate no matter what the rest of the tree looks like. Segment 2 fails
independently for the same tree: the reverse patch restores
`from bim.commands.doc.shared.atomic_write import atomic_write_text` in six
callers and in the old `tests/tools/bim/doc/test_atomic_write.py`, and every
one of those lines matches `shared\.atomic_write`.

The bare `uv run pytest tests/tools/bim/doc -q` that stood here before did NOT
have this property - it passes on the pre-task tree too, because the revert
restores the old module *and* the old test that covered it. That is the check
Decision 2 replaces.

**(c) Reverting any ONE Required file alone still fails some segment.** Per
file:

- `src/tools/bim/commands/doc/shared/atomic_write.py` - re-created by its own
  reverse hunk, so segment 1 fails.
- `tests/tools/bim/doc/test_atomic_write.py` - re-created; it imports
  `bim.commands.doc.shared.atomic_write`, which does not exist while the module
  stays deleted, so segment 2 matches it AND segment 3 fails at collection with
  a `ModuleNotFoundError`.
- the six callers (`zettel_writer.py`, `issuers.py`, `ocr.py`, `triage.py`,
  `pipeline.py`, `audit/reporter.py`) - each reverse hunk swaps
  `from buvis.pybase.filesystem import atomic_write_*` back to
  `from bim.commands.doc.shared.atomic_write import atomic_write_*`. Segment 2
  matches that line, and segment 3 fails too because the module is gone. Each
  of the six is imported by the doc suite - `rg -c` over the six matching test
  files returns `test_zettel_writer.py:1`, `test_issuers.py:6`,
  `test_ocr.py:56`, `test_triage.py:2`, `test_pipeline.py:8`,
  `test_audit_reporter.py:1` - so the collection error is unavoidable rather
  than incidental.

Each of the 8 Required files is therefore individually load-bearing, which is
what the next task's `necessity` pass measures.

- This is the only `impl+caller` unit in the whole surveyed pool, so the
  composition floor (`>= 1 impl+caller`) depends on it.
