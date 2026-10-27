---
design: skip
default_model: sonnet
model_tier_rationale: staged-path parser change requiring rename and unusual-filename regression coverage
---

# glean check-staged crashes on non-ASCII filenames

Source: agoge report `dev/local/audit-results/agoge-2026-10-26.md`, finding 3,
accepted option A on 2026-10-26. Also covers finding 8 of the 2026-10-25 report.
The reports are local audit artifacts and are not shipped in the public repository.

## Problem

Glean parses line-separated staged numstat output as literal filenames. Git quotes
non-ASCII filenames, so the subsequent staged-blob lookup uses a nonexistent path
and fails with a traceback. Operators staging such filenames cannot complete the
dotfiles safety check, and path-based never verdicts and secret mappings do not
receive the actual filename.

## Solution

Use `git diff --cached --numstat -z --diff-filter=ACMR` and parse its NUL-separated
records, including the distinct rename record layout. Preserve exact destination
filenames for staged-blob reads, ledger checks, secret mappings, and reported paths.

## Requirements

### Must have

- Check a staged non-ASCII filename without a traceback.
- Preserve filenames containing tabs, newlines, or quotes rather than splitting
  or unquoting them as line-separated display text.
- Handle staged renames and copies correctly, checking the destination blob.
- Keep ledger never verdicts, plaintext secret mappings, credential screening,
  encrypted-blob handling, and staged-file counts correct.
- Preserve existing exit behavior: unsafe content is refused, safe content succeeds.

### Nice to have

- None.

## Implementation

```text
skills/glean/scripts/
├── glean.py       # parse NUL-separated numstat records in the staged check
└── test_glean.py  # non-ASCII, unusual-filename, and rename regressions
```

### Module: staged file check

- **Location**: `skills/glean/scripts/glean.py`
- **Maps-to-capability**: safely check staged files using their actual filenames.
- **Responsibility**: parse staged changes and read the correct index blobs.
- **Exports**: `cmd_check_staged`, `git`, `matches`, `mapped_secrets`.

#### Feature: preserve staged filename identity

- **Inputs**: NUL-separated numstat output, ledger entries, and secret mappings.
- **Outputs**: existing staged-check JSON with accurate paths and refusal reasons.
- **Behavior**: decode record boundaries independently of filename characters;
  select the destination path for rename and copy records before reading the index.

### Module: staged filename tests

- **Location**: `skills/glean/scripts/test_glean.py`
- **Maps-to-capability**: prove filename spelling cannot break or bypass the check.
- **Responsibility**: exercise unusual filenames and actual staged rename records.
- **Exports**: none.

### Dependencies

- Staged file check: existing Git wrapper and screening rules (foundation).
- Staged filename tests: depend on the check and temporary bare-repository fixtures.
- Ledger and secret-mapping checks consume the parsed destination path (integration).

## Tasks

### Phase 0: Foundation

- [ ] Add failing tests for a non-ASCII staged file, then change the numstat
  invocation and parser to NUL-separated records. Add regressions for a safe
  non-ASCII filename, a credential-bearing file, a ledger never verdict, a
  plaintext secret mapping, unusual filename characters, and staged renames.
  Assert exact reported filenames, correct staged counts, and expected exit
  results without tracebacks. Account for platform filename restrictions in tests.
  Acceptance: `uv run pytest skills/glean/scripts/test_glean.py` passes; the
  non-ASCII regression fails against the prior code. Verify rename handling with
  real Git output rather than an invented record format.
  The unmerged branch `agoge/authored-tests-2026-10-26` holds a strict-xfail
  regression for this finding. Implement independently if absent; if present,
  convert it to a normal regression without merging unrelated branch changes.

Exit criteria: `uv run pytest`,
`uv run python3 skills/create-skill/scripts/validate_skill.py skills/glean`,
and `braid --check` pass.

## Success Criteria

- Non-ASCII filenames no longer cause staged-blob lookup failures.
- Path-based protections and credential screening work on the real staged path.
- Rename records do not become extra staged files or lookups of nonexistent paths.

### Test Strategy

Carry the observed evidence verbatim from the accepted packet:

```text
Staged `.café` holding `x=ghp_abcdefghijklmnopqrst` in a scratch bare repo. numstat printed `1  0  ".caf\303\251rc"`; `check-staged` -> `subprocess.CalledProcessError: Command '[... 'show', ':".caf\\303\\251rc"']' returned non-zero exit status 128`, exit 1.
```

Use temporary homes and bare repositories for all Git and secret-mapping fixtures.

### Risks

NUL-separated rename records differ from ordinary records; treating every NUL
field as an independent file would miscount changes or check the old path.
Both this PRD and PRD 00090 edit glean and its tests; preserve the missing-ledger
guard and its regression coverage when implementing this parser change.
