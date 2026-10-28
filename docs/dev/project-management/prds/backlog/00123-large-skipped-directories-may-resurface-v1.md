---
design: run
default_model: sonnet
model_tier_rationale: unverified behavior requires faithful reproduction before a compatible ledger fingerprint design
---

# Large skipped directories may resurface on every Glean scan

Source: agoge report `dev/local/audit-results/agoge-2026-10-26.md`, finding 34,
accepted option A on 2026-10-29. The report is a local audit artifact and is not
shipped in the public repository. Status remains unverified: resurfacing was
inferred from code rather than reproduced end to end.

## Problem

Glean omits content hashes for directories above its file cap. The audit suspects
that a saved volatile skip or machine verdict then compares against a missing
scan fingerprint and repeatedly resurfaces an unchanged directory. If real,
operators must repeat the same decision for large untracked directories.

## Solution

First reproduce the actual scan-and-record flow under an isolated home. Only if
the defect is confirmed, persist a cheap large-directory fingerprint based on
file count and latest modification time, and use it consistently for volatile
comparison. If the defect does not reproduce, document the result and skip the
speculative implementation rather than forcing a ledger-format change.

## Requirements

### Must have

- Reproduce with a directory exceeding 200 files, real scan output, and the
  supported ledger-recording flow in a temporary home/bare repository.
- Do not fabricate a content hash solely to force the suspected mismatch.
- Record whether a recent unchanged skip/machine entry actually resurfaces;
  unconfirmed reproduction means no fingerprint implementation.
- If confirmed, provide count/latest-mtime fingerprints for large directories
  and keep unchanged recent verdicts settled across repeated scans.
- Preserve resurfacing when the supported fingerprint changes or the 180-day
  decision age expires, and preserve content hashes for smaller eligible inputs.
- Keep existing ledger entries readable and update documented volatile-entry
  requirements alongside validation; do not masquerade metadata as a content hash.
- Preserve never verdicts, staged-secret checks, and capped-prescreen warnings.

### Nice to have

- None.

## Implementation

```text
skills/glean/
├── SKILL.md              # document supported volatile fingerprints if changed
└── scripts/
    ├── glean.py          # conditional large-directory fingerprint support
    └── test_glean.py     # faithful reproduction and conditional regressions
```

Design prerequisite: establish the reproduction before selecting a ledger
representation. Resolve backward compatibility and exact comparison rules from
current schema consumers. No user input is required to stop on a failed premise.

### Module: scan and ledger fingerprints

- **Location**: `skills/glean/scripts/glean.py`
- **Maps-to-capability**: preserve volatile decisions for unchanged large directories.
- **Responsibility**: produce, validate, and compare the supported fingerprint consistently.
- **Exports**: `describe`, `load_ledgers`, `cmd_scan`.

#### Feature: retain a large-directory decision

- **Inputs**: directory metadata, saved volatile verdict, and decision age.
- **Outputs**: a settled unchanged verdict or justified resurfacing.
- **Behavior**: after confirmation, compare a count/latest-mtime fingerprint for
  large directories while preserving existing small-input hash and expiry behavior.

### Module: reproduction and regression tests

- **Location**: `skills/glean/scripts/test_glean.py`
- **Maps-to-capability**: confirm the suspected user-visible behavior before fixing it.
- **Responsibility**: use actual scan-produced fields and repeated isolated scans.
- **Exports**: none.

### Module: ledger instructions

- **Location**: `skills/glean/SKILL.md`
- **Maps-to-capability**: let users record the supported large-directory fingerprint.
- **Responsibility**: update schema/recording instructions only if implementation is justified.
- **Exports**: none.

### Dependencies

- Reproduction: foundation and prerequisite for any schema or behavior change.
- Fingerprint implementation and instructions: depend on confirmed reproduction.
- Existing ledger validation and resurfacing rules constrain compatibility.

## Tasks

### Phase 0: Reproduction

- [ ] Reproduce with a scratch home and bare repo using a large untracked
  directory, a recent skip/machine decision, and real scanner output. Compare
  repeated unchanged scans. Acceptance: record the exact flow and observed
  outcome; if the claimed defect cannot be confirmed, skip Phase 1 and record
  why without changing production behavior or pretending the audit was verified.

### Phase 1: Conditional implementation

- [ ] Depends on Phase 0 confirming the defect. Add count/latest-mtime fingerprint
  support, compatible ledger validation, and recording instructions. Test repeated
  unchanged scans, a supported metadata change, expiry, both volatile verdicts,
  older ledger records, and existing small-directory hash behavior.
  Acceptance: `uv run pytest skills/glean/scripts/test_glean.py` passes, and the
  confirmed repeated-resurfacing regression fails against pre-change code.

Exit criteria when implementation occurs: `uv run pytest`,
`uv run python3 skills/create-skill/scripts/validate_skill.py skills/glean`,
and `braid --check` pass. If unconfirmed, a documented reproduction result and
skipped speculative fix are the completion result.

## Success Criteria

- The suspected behavior receives a faithful end-to-end determination.
- If confirmed, unchanged large-directory decisions persist with documented weaker
  fingerprints and existing expiry/protection behavior remains intact.
- If unconfirmed, no speculative ledger-format change is made.

### Test Strategy

Carry the report's evidence verbatim, retaining its unverified status:

```text
Not run end to end.
```

The audit measured zero sha256 reads for a 10,000-file directory; repeated
resurfacing was inferred. This absence of reproduction is why Phase 0 is mandatory.

### Risks

Count/latest-mtime is weaker than a content hash and can miss changes that preserve
both metadata values. Ledger changes must remain compatible with PRD 00112's
validation and existing protections. The defect may not be real; confirmation
is a hard prerequisite, not a reason to invent a new failure case.
