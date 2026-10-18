## 1: Add runbook-vs-harness drift test

- `run_eval_harness._parser()` subparsers action is located by finding the one `_actions` entry whose `.choices is not None` (argparse's internal `_SubParsersAction`), since the task said to "walk parser._subparsers / the subparsers action's choices dict" but didn't specify the exact attribute name to find that action - this is the standard, only way to get there from a plain `ArgumentParser`.
- Used `._actions` (not `._subparsers`) consistently, matching the task's own phrasing ("each one's `._actions` for `.option_strings`").
