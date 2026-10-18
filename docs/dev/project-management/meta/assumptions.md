## 1: Add runbook-vs-harness drift test

- `run_eval_harness._parser()` subparsers action is located by finding the one `_actions` entry whose `.choices is not None` (argparse's internal `_SubParsersAction`), since the task said to "walk parser._subparsers / the subparsers action's choices dict" but didn't specify the exact attribute name to find that action - this is the standard, only way to get there from a plain `ArgumentParser`.
- Used `._actions` (not `._subparsers`) consistently, matching the task's own phrasing ("each one's `._actions` for `.option_strings`").

## 3: [D1] Tail sweep: skills/use-qwen/scripts/test_runbook_matches_harness.py

- Used the `--bound` removal, not `--shape`, as the word-boundary bite proof: removing `--shape` from the usage line still passes because section 7 prose documents `--shape` itself at line 115, which is a legitimate match rather than a masked one.
- Annotated the new `_subparsers_action` helper as `argparse.Action`, which the task did not specify.

## 4: [D1] Tail sweep: prose

- None. Both corrected statements were read off the code first (`eval_harness/evidence.py:162-194` for the seven `inputs_sha256` labels, `eval_harness/attempt.py:109-138` for `vet`'s exit codes and the `ready: false` record), so neither needed a guess.
