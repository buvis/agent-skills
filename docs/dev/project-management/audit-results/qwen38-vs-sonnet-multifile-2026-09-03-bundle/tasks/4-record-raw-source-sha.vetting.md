# Task 4 - gems / record the raw source sha on promote

Stage A prospect 4, **scope narrowed in stage B** (see "Scope narrowing").
Verdict: **eligible**.

Kind: impl+test

Repo: `/Users/bob/git/src/github.com/buvis/gems` (Python)
PRD: `dev/local/prds/done/00044-bim-doc-claim-dedup-integrity-v1.md:43`

Commit run: `0188270a..b919d7ad` (2 commits: `0188270a` test, `b919d7ad` fix)
Parent of `<first>` (`0188270a^`): `fc87d99f5035fa9247b7d4b24e78c725ef7daa1f`
(verified with `git -C <src> rev-parse 0188270a^`)
Base sha (`HEAD` at vetting time): `7d7f9d8a1fea3160650ee4eab6589d30cb4b6edf`

## Reverifiability

Working tree clean at `<base-sha>`: `git -C <src> status --porcelain` printed
nothing; control `git -C <src> status --porcelain --branch` printed
`## master...origin/master`.

Raw test command:

    uv --directory <tree> run pytest tests/tools/bim/doc/test_promote.py -q

Run once at `<base-sha>` against the source tree: **exit 0**. (It was run as
part of `uv --directory /Users/bob/git/src/github.com/buvis/gems run pytest
tests/tools/bim/doc/test_pipeline.py tests/tools/bim/doc/test_promote.py -q`,
`56 passed in 0.38s`, before the scope was narrowed; no test failed. The whole
`tests/tools/bim/doc` directory also passed, `977 passed`.)

## Required files

- `src/tools/bim/commands/doc/promote/promote.py` (impl)
- `tests/tools/bim/doc/test_promote.py` (test) - CHANGED by the task

Ancillary files: `src/tools/bim/commands/doc/shared/pipeline.py`,
`tests/tools/bim/doc/test_pipeline.py` (both changed by the same commit run;
see "Scope narrowing")

`multi_file`: 2 Required files, 1 `impl` + 1 `test` the task changed.

## History per Required file

    git -C <src> log --oneline --name-only b919d7ad..HEAD -- src/tools/bim/commands/doc/promote/promote.py tests/tools/bim/doc/test_promote.py

Output:

    55678673 refactor(bim): build promote's two processed rows from one literal
    src/tools/bim/commands/doc/promote/promote.py

Verdicts:

- `src/tools/bim/commands/doc/promote/promote.py`: 1 later commit -> **`surgical`**
- `tests/tools/bim/doc/test_promote.py`: `empty` -> `whole-file`

### Why promote.py needs a surgical revert

`55678673 refactor(bim): build promote's two processed rows from one literal`
rebuilt the very block this task added. Today `_finalize` constructs one
`filed_row = ProcessedRow(...)`, records it, then records
`filed_row.model_copy(update={"sha256": ctx.proposal.source.sha256})`. The
task-era shape was two full `ProcessedRow(...)` literals. `git apply --check`
on the naive reverse patch fails on exactly that hunk
(`patch failed: ...promote.py:278`).

The hand-written reverse patch collapses today's `filed_row` + `model_copy`
pair back into the single inline `record_processed(ProcessedRow(...))` call
that stood at `fc87d99f`, i.e. it removes both the second identity row and the
`filed_row` binding `55678673` introduced to build it. Nothing else in
`promote.py` is touched.

## Scope narrowing (stage B decision)

Stage A listed four Required files: `pipeline.py` + `promote.py` and their two
test files.

At that scope the candidate **fails `interface_pinned`** on the `pipeline.py`
half. The canonical `tests/tools/bim/doc/test_pipeline.py` at `<base-sha>`
asserts the dedup row's filename three times as
`f"_triage/{name} (pending review)"` (lines 326, 731, 795). That exact string
format was introduced by a LATER commit
(`f6ecadd1 fix(bim): tell the truth about a document still awaiting triage
review`), not by this task, and appears nowhere in the ledger line or its
acceptance clause. An engine reading the task would write
`canonical_filename=basename` (which is what the task actually shipped) and
fail. `test_pipeline.py` was also split and reworked by four later commits
(`6e9c0e20`, `668a4cdb`, `fac918c0`, `27f37de9`), so its naive reverse hunk
does not apply either.

Narrowing to the `promote` pair removes that binding entirely. `pipeline.py`
stays at `<base-sha>`, so the triage-side row keeps working and nothing in the
tree is left inconsistent; the gate drops `test_pipeline.py`. The narrowed unit
is still one ledger line, one commit run, `impl+test`, multi-file. The prompt
still carries the ledger line verbatim, so it still mentions `pipeline.py:627`
even though `pipeline.py` is not in the file list - an engine that edits it
anyway is not penalised, because the gate does not read it.

## Reverse patch

`4-record-raw-source-sha.reverse.patch` = hand-written surgical diff for
`promote.py` plus

    git -C <src> diff b919d7ad fc87d99f -- tests/tools/bim/doc/test_promote.py

for the test file.

`git -C /Users/bob/git/src/github.com/buvis/gems apply --check -v <patch>`:
clean, both files.

Pretask: cada08ac7fd703e95887480ee45a5811e5f8b791

Necessity:
- `src/tools/bim/commands/doc/promote/promote.py`: exit 1, first failure: `assert False is True` (`DedupResult(is_duplicate=False, existing_row=None).is_duplicate` in `test_promote_dedups_raw_source_sha_as_well_as_filed_pdf_sha`) - necessity holds.
- `tests/tools/bim/doc/test_promote.py`: n/a (test file - necessity is enforced at scoring by dropped/own/ablate)

## Pinned interface

The prompt's `Names the acceptance gate binds to` block reads, verbatim:

- none - every name the gate binds to already exists in the tree.
  `ProcessedRow` (with its `sha256`, `canonical_filename`, `issuer_slug`,
  `doc_type`, `processed_at` and `extraction_method` fields), `StateDB.dedup`
  and its `is_duplicate` / `existing_row` result fields, and
  `TriageProposal.source.sha256` are all present and unchanged; the gate
  compares the raw-source row against the filed row with
  `model_dump(exclude={"sha256", "processed_at"})`, so it pins no literal of
  its own.

Why the list is empty. Everything the canonical
`tests/tools/bim/doc/test_promote.py` binds to in the
two tests this task added
(`test_promote_dedups_raw_source_sha_as_well_as_filed_pdf_sha`,
`test_promote_dedups_raw_source_sha_when_ocr_hands_back_the_triage_pdf`):

Named verbatim in the prompt (ledger line):

- `promote.py`
- "the raw source sha", "detected as duplicate", "no second archive copy" - the
  behaviour the two tests assert

Present in the reverted tree:

- `bim.commands.doc.promote.promote.CommandPromote`, `PromoteServices`,
  `PromoteParams`
- `bim.commands.doc.shared.state_db.StateDB.dedup` and its result fields
  `is_duplicate`, `existing_row`
- `bim.commands.doc.shared.state_db.ProcessedRow` and its fields `sha256`,
  `canonical_filename`, `issuer_slug`, `doc_type`, `processed_at`,
  `extraction_method` (compared through `model_dump(exclude=...)`)
- `TriageProposal.source.sha256` - the identity the row has to carry
- `CommandResult.metadata["pdf_path"]`
- `OCRRunner`, `OCRResult`, `ZettelWriter`, `load_registry`, `write_proposal`

The tests deliberately do NOT bind `extraction_method` to a literal, and they
compare the raw row against the filed row with
`model_dump(exclude={"sha256", "processed_at"})`, so whatever value the engine
uses for the filed row is automatically correct for the raw one. There is no
name the engine would have to invent.

Canonical test files copied:

- `tests/tools/bim/doc/test_promote.py` ->
  `4-record-raw-source-sha.canonical/tests/tools/bim/doc/test_promote.py`

## Notes

- The narrowed unit is the harder half of the original ledger line: the raw
  source sha survives OCR replacing the PDF, which is what the two canonical
  tests pin from both the full-OCR branch and the cheap pass-through branch.
