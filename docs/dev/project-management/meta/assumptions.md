## 1: Hoist tool resolution into main, make verify_control raise, guard the registry open

- "stderr is that line" for a missing registry means the stripped stderr equals exactly `registry not found: <path>`, with no `sweep:` prefix. (Tess)
- "printed to stderr as one line" means stripped stderr is exactly one line for every setup-failure test through `main`. (Tess)
- `main` prints the resolver's `RuntimeError` message verbatim, so the fake's text (`Could not resolve rg: not found on PATH`) reaches stderr unchanged. (Tess)
- Every exception type's collapsed text (RuntimeError, TimeoutExpired, OSError) appears in the control-term failure message. (Tess)
- The control-repo pattern-scan stub keys on `Path(cwd).resolve()`, `_run_rg` taking cwd as its second argument. (Tess)
- The CHANGELOG line goes first in the existing Unreleased `### Fixed` list. (Ivan)

## 2: Walk cwd up to its git root in enumerate_repos

- No ancestor of pytest's tmp_path holds `.git`; the "unchanged" and non-repo-cwd tests depend on it. (Tess)
- The real `sweep.BUVIS_BARE` work tree ($HOME) is not an ancestor of tmp_path. (Tess)
- pytest's tmp_path is already symlink-resolved, so `Path(".").absolute()` after chdir equals the tmp_path-built path. (Tess)
- "A cwd not inside any git repo stays as given" still allows making a relative cwd absolute first. (Tess)

## 3: Replace the two YAML helpers with json.dumps

- The two-language rule block holds exactly 2 YAML documents (python and javascript). (Tess)
- The empty string is left out of the round-trip corpus; an empty pattern is not assumed valid. (Tess)
- Task 3 is a user-visible `fix`, not a refactor (see task 3 commit): the old renderer emitted timestamps, `1:30`, `=` and C1 characters bare, so they changed type or failed to load. (orchestrator)
