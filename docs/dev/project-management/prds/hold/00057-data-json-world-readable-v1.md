---
default_model: opus
model_tier_rationale: two platform-native protection paths (POSIX modes, Windows ACLs) with an exact contract for temporary and final files; the test author must verify ACLs headlessly on both CI hosts
design: run
consensus_engine: shadow
---

# data.json is world-readable while it carries whatever a failed command printed

## Problem

`run()` in `skills/brief-portfolio/scripts/collect.py` copies the first 300
characters of a failed subprocess's stderr into the error string, which is
written to `~/.local/share/agents/portfolio-brief/data.json` with the default
mode 644, printed as a WARN, and rendered on the Work tab, the Todo tab and
RepoDetail. If `gh` or `git` ever echoes a token (a remote URL with embedded
credentials, a misconfigured auth message), it is persisted in a
world-readable file. Source: agoge run
`dev/local/audit-results/agoge-2026-09-05.md`, finding 4 (MEDIUM, security
lane, status mocked: gh shim, suspected in production); decision 2026-09-05:
write `data.json` owner-only. Redacting the text and dropping stderr were
both declined, so the page and the WARN lines keep showing the full first 300
characters. Decision 2026-09-13 (backlog review B01): protect on both
platforms natively, because the native Windows CI job
(`.github/workflows/ci.yml:59-60`) runs this suite and `chmod` does not move
mode bits there (`tests/test_conftest_fixtures.py:18,249-255`).

```
Shim stderr HTTP 401: bad credentials (token ghp_MARKER): data.json line 11
"meta: gh api: HTTP 401: bad credentials (token ghp_MARKER)", page Work
Could not check external PRs: ... ghp_MARKER), Todo <span class="why">,
RepoDetail <li class="mono">.
```

## Solution

Add one helper `protect_owner_only(path)` to `collect.py` and call it on every
snapshot file at the moment it is created, before it is published by rename:

- POSIX (`os.name == "posix"`): `os.chmod(path, 0o600)` for a file,
  `0o700` for a directory. `write_snapshot` (`collect.py:447-465`) creates
  `data.json.tmp` and `data-prev.json.tmp` through
  `os.open(path, os.O_WRONLY | os.O_CREAT | os.O_TRUNC, 0o600)` so the
  temporary file is never readable by others, not even between write and
  rename; the helper is still called on it so the mode is exact under any umask.
- Windows (`os.name == "nt"`): run
  `icacls <path> /inheritance:r /grant:r <USERNAME>:F` (directory: `<USERNAME>:(OI)(CI)F`)
  with `subprocess.run(..., check=True, capture_output=True)`, where
  `<USERNAME>` is `os.environ["USERNAME"]`. `icacls` ships with Windows; no
  new dependency.
- `tmp_file.replace(data_file)` and `prev_tmp.replace(...)` keep the
  protection of the temporary file, so `data.json` and `data-prev.json` are
  owner-only after every run, including a run that rotates a 644 `data.json`
  left by an older version: the old bytes are copied into a freshly protected
  temporary file, never published as-is.
- `main()` (`collect.py:506-507`) creates the out directory owner-only when it
  is absent (`mkdir(parents=True)` then `protect_owner_only(outdir)`); an
  existing directory's protection is left alone, by decision.
- A protection failure (`OSError`, or `CalledProcessError` from `icacls`)
  unlinks the temporary file, leaves the published files untouched, and
  propagates; `main()` prints `cannot protect <path>: <reason>` to stderr and
  exits 1. An unprotected snapshot is never published.
- Nothing else changes: the page, the digest and the WARN lines are
  unaffected by decision. `history.jsonl` and `commits-digest.md` are out of
  scope: they carry no subprocess stderr.

## Requirements

### Must have

- After every `main()` run, `data.json` and, when rotation happened,
  `data-prev.json` are owner-only: POSIX `stat.S_IMODE(st_mode) == 0o600`;
  Windows `icacls <path>` lists exactly one access entry, for the current
  user, with `(F)`, and no inherited entry.
- The temporary files `data.json.tmp` and `data-prev.json.tmp` are owner-only
  at the instant `Path.replace` publishes them.
- An out directory created by the run is owner-only (POSIX `0o700`; Windows
  one `(OI)(CI)(F)` entry for the current user). An existing directory's
  protection is unchanged.
- A protection failure exits 1 with `cannot protect` on stderr, leaves no
  `.tmp` file behind, and leaves an existing `data.json` byte-identical.
- All assertions run on both CI hosts through one helper
  `assert_owner_only(path)` in the test module that branches on `os.name`;
  no test is skipped by platform.

### Nice to have

- none

## Implementation

### Module: collect.py

- **Location**: `skills/brief-portfolio/scripts/`
- **Responsibility**: Create every snapshot file owner-only and publish only protected files.
- **Exports**: `protect_owner_only(path)`, `write_snapshot()`, `main()`, unchanged CLI

### Module: test_collect_history.py

- **Location**: `skills/brief-portfolio/scripts/`
- **Responsibility**: Pin the protection on both platforms.
- **Exports**: `assert_owner_only(path)`, pytest cases

### Dependencies

- collect.py: No dependencies (foundation)
- test_collect_history.py: Depends on [collect.py]

## Tasks

### Phase 0: Foundation

- [ ] Add `protect_owner_only` and create the snapshot temporaries and the out directory through it - Acceptance: `test_fresh_out_dir_and_data_json_are_owner_only` runs `main()` against a fake registry with `collect.run` stubbed (the pattern of the existing end-to-end `main()` tests) with an absent out directory and asserts `assert_owner_only` on the directory and on `data.json`; `test_rotation_publishes_both_snapshots_owner_only` pre-creates the out directory and a `data.json` 5 hours old (the `write_data_json_fixture` pattern), widens it to `0o644` on POSIX or grants `Everyone:R` through `icacls` on Windows, runs `main()`, and asserts `assert_owner_only` on `data.json` and `data-prev.json` and that the directory's protection is unchanged; `test_snapshot_temporaries_are_owner_only_before_publication` patches `Path.replace` (mirroring the existing `data-prev.json.tmp` test at `test_collect_history.py:100-125`, which patches `Path.write_text` the same way) to run `assert_owner_only` on the source before delegating, and asserts it ran for both temporaries; each watched red against the old code first; `uv run pytest skills/brief-portfolio/scripts -q` reports 0 failing.
- [ ] Fail loud on a protection failure - Acceptance: `test_protection_failure_exits_one_and_publishes_nothing` patches `collect.protect_owner_only` to raise `OSError("denied")`, runs `main()` with an existing `data.json`, and asserts exit 1, `cannot protect` on stderr, no `*.tmp` under the out directory, and `data.json` bytes unchanged; watched red first; `uv run pytest skills/brief-portfolio/scripts -q` reports 0 failing.

### Phase 1: Core

- none

## Success Criteria

- The four new tests pass on the Linux and the native Windows CI jobs with no
  platform skip; the existing rotation tests pass unchanged.
- Optional operational check after the next real run, not a completion gate:
  `stat -f %Lp ~/.local/share/agents/portfolio-brief/data.json` prints 600 on
  macOS, or `icacls` lists only the current user on Windows.
