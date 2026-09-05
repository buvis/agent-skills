---
name: sweep-fix
description: Use when a fix just landed in this repo and the same bug pattern may exist elsewhere in the portfolio. Sweeps every gita-registered repo for a pattern derived from the fix's diff and reports hits; fixes land only in this repo, after approval.
---

# Sweep Fix

Take a fix that just landed in the current repo, derive a pattern that
captures the underlying bug class, and sweep every gita-registered repo for
the same pattern. Every other repo's hits stay report-only. This skill never
edits outside the current repo, and never runs a git write anywhere.

## Workflow

### 1. Derive (model judgment)

Read the fix commit's diff (`git show <sha>` or `git diff <range>`; an
omitted sha or range defaults to `HEAD`) and decide:

- `kind`: `astgrep` (structural code pattern) or `rg` (text/regex pattern)
- `pattern`: the search pattern for that kind
- `reason`: one line on why this pattern indicates the same bug class
- `control_term`: a term known to be present in the diff, used to prove the
  sweep actually works before trusting an empty result anywhere else

None of this is computed by `sweep.py`. These are judgment calls made here,
from reading the diff, not by any function in the script.

### 2. Sweep (deterministic)

```bash
python3 ~/.agents/skills/sweep-fix/scripts/sweep.py \
  --kind {astgrep,rg} \
  --pattern TEXT \
  --reason TEXT \
  --control-term TEXT \
  --control-repo PATH \
  [--registry PATH] [--cwd PATH] [--cap N] [--out PATH]
```

`--control-repo` is the current repo, where the fix commit lives. `main()`
resolves the scan tool, enumerates every repo in the gita registry, scans
every registered repo, and only when the whole sweep found zero hits checks
that the control term is present in `--control-repo` (aborting loud if it is,
because a pattern that misses a known-present term is broken, and an
unverified empty sweep is not a clean sweep). It then renders the report and
writes it under `dev/local/audit-results/`.

### 3. Report

Read the report file `main()` wrote back (its path is printed on exit).

### 4. Walk (current repo only)

Walk the **current repo's** hit rows with the user, one at a time, for
approval. Apply approved fixes only in the current repo, via `Edit`.

**Read-only outside the current repo:** every other repo's rows stay
report-only. `sweep.py` never edits any file outside the current repo, and
never runs a git write in any repo. Fixes land only in the invoking repo,
and only after the user approves each one.

## Dependencies

- `~/.agents/skills/brief-portfolio/scripts/collect.py`: provenance, not a
  runtime import. `enumerate_repos()` copies its gita registry read shape
  (parsing `~/.config/gita/repos.csv`) rather than importing it, because that
  read is inline in `collect.py`'s `main()`; keep the two in step by hand.
- Claude Code's cartographer-echo hook (a host-local hook, not shipped with
  this skill, so it is not present on every host): its `_resolve_rg()`
  algorithm (cached PATH-then-execpath fallback, for the case where `rg` is
  a shell function rather than a binary) was ported into `resolve_rg()`.
  `sweep.py` never reads, imports, or runs the hook itself, so nothing
  breaks when the hook is absent.
- loupe (a Claude Code plugin) and its ast-grep rule-pack files, which live
  at a plugin-cache path that includes loupe's version number: only the
  shape of a rule block (`id`/`language`/`severity`/`message`/
  `rule: {pattern: ...}`) is reused, by `render_report()` for `astgrep`
  findings. `render_report()` emits that shape itself rather than reading
  loupe's files, so nothing breaks when loupe is absent or on a different
  version.
