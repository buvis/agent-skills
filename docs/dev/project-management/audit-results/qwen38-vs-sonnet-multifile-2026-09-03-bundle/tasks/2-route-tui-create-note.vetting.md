# Task 2 - gems / route TUI create through CommandCreateNote

Stage A prospect 2. Verdict: **eligible**, at the FULL four-file scope. (Stage B
had narrowed this to the `create_note` pair; retry 1 restores the full set - see
"Scope restored".)

Kind: impl+test

Repo: `/Users/bob/git/src/github.com/buvis/gems` (Python)
PRD: `dev/local/prds/done/00054-bim-serve-tui-convergence-v1.md:82`

Commit run: `c084d88c..cb2e1c55` (3 commits: `c084d88c` test, `3c6493fa` feat,
`cb2e1c55` slop prune)
Parent of `<first>` (`c084d88c^`): `2ba5be3a27d7fa5ea2ebfe1b5ff0b12d5839f808`
(verified with `git -C <src> rev-parse c084d88c^`)
Base sha (`HEAD` at vetting time): `7d7f9d8a1fea3160650ee4eab6589d30cb4b6edf`

## Reverifiability

Working tree clean at `<base-sha>`: `git -C <src> status --porcelain` printed
nothing; control `git -C <src> status --porcelain --branch` printed
`## master...origin/master`.

Raw test command:

    uv --directory <tree> run pytest tests/tools/bim/tui/test_create_note.py tests/lib/pybase/test_result.py -q

Run once at `<base-sha>` against the source tree
(`uv --directory /Users/bob/git/src/github.com/buvis/gems run pytest
tests/tools/bim/tui/test_create_note.py tests/lib/pybase/test_result.py -q`):
**exit 0**, `20 passed in 1.66s`. `test_create_note.py` contributes 6 of the 20
and `test_result.py` the other 14; none failed.

## Required files

- `src/tools/bim/tui/create_note.py` (impl)
- `src/lib/buvis/pybase/result.py` (impl) - the `notify_result` helper the task
  adds
- `tests/tools/bim/tui/test_create_note.py` (test) - CHANGED by the task
- `tests/lib/pybase/test_result.py` (test) - CHANGED by the task

Ancillary files: none

`multi_file`: 4 Required files across two source trees (`src/tools/bim`,
`src/lib/buvis/pybase`), 2 `impl` + 2 `test` the task changed.

Which commit touched what (`git -C <src> log --oneline --name-only
c084d88c^..cb2e1c55`, plus `git show --name-only c084d88c` for the first commit
of the run):

    c084d88c  tests/lib/pybase/test_result.py, tests/tools/bim/tui/test_create_note.py
    3c6493fa  src/lib/buvis/pybase/result.py, src/tools/bim/tui/create_note.py
    cb2e1c55  src/tools/bim/tui/create_note.py

## History per Required file

    git -C <src> log --oneline --no-patch cb2e1c55..HEAD -- <each Required path>

All four printed nothing. Controls, because an empty result from a filtered
`git log` is unverified on its own:

- unfiltered, same range: `git -C <src> log --oneline --no-patch cb2e1c55..HEAD
  --max-count=5` prints five commits (`7d7f9d8a`, `0738511b`, `e1c889af`,
  `e8c54185`, `2284890e`), so the range itself is non-empty.
- whole history of the `result.py` pair: `git -C <src> log --oneline --no-patch
  -5 -- src/lib/buvis/pybase/result.py tests/lib/pybase/test_result.py` prints
  `3c6493fa`, `c084d88c`, `4285b6a5`, `9fbf5a34`, `17d86992` - the two newest
  are the task's own commits, so nothing has touched the pair since.
- the `create_note` pair was controlled in the first pass with
  `b919d7ad..HEAD -- src/tools/bim/commands/doc/shared/pipeline.py`, which
  printed two commits.

Verdicts:

- `src/tools/bim/tui/create_note.py`: `empty` -> `whole-file`
- `src/lib/buvis/pybase/result.py`: `empty` -> `whole-file`
- `tests/tools/bim/tui/test_create_note.py`: `empty` -> `whole-file`
- `tests/lib/pybase/test_result.py`: `empty` -> `whole-file`

`clean_history`: all four clean. Because the canonical test copies come from
`<base-sha>` and `<base-sha>` equals the end of the commit run for both test
files, **neither canonical test can bind behaviour a later commit introduced** -
there are no later commits. That is the condition Decision 1 asked to check
before restoring the full set, and it holds.

## Scope restored (retry 1)

Stage B narrowed this candidate to the `create_note` pair because the canonical
`tests/lib/pybase/test_result.py` opens with

    from buvis.pybase.result import CommandResult, _json_safe, notify_result

and pins the fallback message `"Failed"`, neither of which the ledger line
states. Under Decision 1 the prompt now carries an interface-pins block, so
`notify_result`'s signature, its `severity=` keyword contract and the `"Failed"`
literal are stated to the engine, and the binding is no longer unpinnable.
`src/lib/buvis/pybase/result.py` and `tests/lib/pybase/test_result.py` are
therefore Required again, in the reverse patch, and (for the test) in
`.canonical/`.

`_json_safe`, the third name that import line binds, is pre-existing: the task's
diff to `result.py` (`git -C <src> show 3c6493fa -- src/lib/buvis/pybase/result.py`)
is a pure append of `notify_result` plus a `from collections.abc import
Callable` line. The revert leaves `_json_safe` and `CommandResult` in place.

## Reverse patch

    git -C <src> diff cb2e1c55 2ba5be3a --output=<abs>/tasks/2-route-tui-create-note.reverse.patch -- src/tools/bim/tui/create_note.py tests/tools/bim/tui/test_create_note.py src/lib/buvis/pybase/result.py tests/lib/pybase/test_result.py

All four files are `whole-file`, so the plain two-point diff is exact; no
hand-written hunk is needed.

`git -C /Users/bob/git/src/github.com/buvis/gems apply --check -v <patch>`:
clean, all four files.

Pretask: 22c9ebb6608169c64c98d241627e795c3300e901

Necessity (re-run, gate feedback retry 1: the template's venv was rebuilt with
`uv --directory <tpl> sync --all-extras --group test`, which installs `anyio`
and registers the `@pytest.mark.anyio` marker; fresh clones `-necessity-5`
(create_note.py) and `-necessity-6` (result.py), the earlier
`-necessity-2/3/4` clones - masked by the venv gap - left in place):
- `src/tools/bim/tui/create_note.py`: exit 1, first failure: `AssertionError: assert 'Created /pri...0902080441.md' == 'Missing requ...nswer: status'` (`TestCreateNoteApp::test_create_with_blank_required_answer_notifies_error_and_stays_open`) - necessity holds.
- `src/lib/buvis/pybase/result.py`: exit 2, first failure: `ImportError: cannot import name 'notify_result' from 'buvis.pybase.result'` (collecting tests/lib/pybase/test_result.py) - necessity holds.
- `tests/tools/bim/tui/test_create_note.py`: n/a (test file - necessity is enforced at scoring by dropped/own/ablate)
- `tests/lib/pybase/test_result.py`: n/a (test file - necessity is enforced at scoring by dropped/own/ablate)

## Pinned interface

The prompt's `Names the acceptance gate binds to` block reads, verbatim:

- `notify_result(result, notify)` - a module-level function in
  `src/lib/buvis/pybase/result.py`, importable as
  `from buvis.pybase.result import notify_result`. Signature
  `notify_result(result: CommandResult, notify: Callable[..., None]) -> None`,
  parameters in that order.
- It calls `notify(message, severity=...)` with `severity` passed as a keyword
  argument, using exactly these severity strings: `"warning"` for every entry
  of `result.warnings`, `"information"` for `result.output` on success,
  `"error"` on failure.
- Order of calls: every warning first, then the success output or the failure
  message.
- On success with an empty `output`, it notifies nothing.
- Failure fallback literal: when `result.success` is false and `result.error`
  is empty, the notified message is exactly `"Failed"`.

Those pins are read off the shipped implementation (`git show 3c6493fa --
src/lib/buvis/pybase/result.py`) and off the canonical test's own `notify`
double, whose signature is `def notify(message: str, *, severity: str =
"information") -> None` and which records `(message, severity)` tuples - hence
the keyword requirement and the exact severity strings. The `"Failed"` fallback
is asserted at `tests/lib/pybase/test_result.py:118` as
`assert calls == [("Failed", "error")]`.

Everything else the two canonical tests bind is already in the reverted tree and
needs no pin:

- module path `bim.commands.create_note.create_note` (the CLI command module)
- `bim.params.create_note.CreateNoteParams` and its fields `zettel_type`,
  `title`, `tags`, `extra_answers`
- `bim.tui.create_note.CreateNoteApp` and its module-level names
  `get_templates`, `get_formatter`, `PrintZettelUseCase`, `get_repo`,
  `get_hook_runner`
- `CreateNoteApp._gather_answers`
- widget ids `#template-select`, `#title-input`, `#tags-input`, `#create-btn`,
  `#cancel-btn`, `#q-priority`
- `buvis.pybase.result.CommandResult` with its `success`, `output`, `error`,
  `warnings` and `metadata` fields, and `_json_safe`
- `buvis.pybase.zettel.domain.templates.Question` (`key`, `prompt`, `required`)
- error string `"Missing required answer: status"` - produced by the
  pre-existing `CommandCreateNote` validation, not by anything this task adds

Canonical test files copied:

- `tests/tools/bim/tui/test_create_note.py` ->
  `2-route-tui-create-note.canonical/tests/tools/bim/tui/test_create_note.py`
- `tests/lib/pybase/test_result.py` ->
  `2-route-tui-create-note.canonical/tests/lib/pybase/test_result.py`

## Notes

- **Risk, not a disqualification:** the canonical test patches
  `bim.commands.create_note.create_note.CommandCreateNote` (the defining
  module) and then asserts `mock_command_cls.call_count == 1`. That patch only
  bites if `bim.tui.create_note` resolves the class at call time - the shipped
  implementation imports it inside the button handler. An engine that writes a
  module-level `from bim.commands.create_note.create_note import
  CommandCreateNote` will fail that one test even though its behaviour is
  correct, because earlier tests in the same file already imported
  `bim.tui.create_note` and cached it in `sys.modules`. This is a test bound to
  an implementation detail, not an unpinned symbol, so it does not trip
  `interface_pinned` - but it will cost a partial score, and the necessity pass
  should record it.
- At the restored scope this is the only task in the set whose Required files
  span two independent source trees (`src/tools/` and `src/lib/`), which is the
  dropped-a-file signal the eval exists to measure.
