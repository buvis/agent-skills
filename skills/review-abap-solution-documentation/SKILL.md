---
name: review-abap-solution-documentation
description: Use when auditing an ABAP solution documentation package for hallucinations, internal inconsistencies, and evidence gaps that undermine trustworthiness. Triggers on "review abap solution documentation", "audit abap docs".
---

# Review ABAP Solution Documentation

Adversarial audit of a completed `explore-abap-solution` + `document-abap-solution` package. Surfaces hallucinations, internal inconsistencies, unsupported claims, and anything else that undermines trustworthiness — before a developer builds from the docs.

**This skill treats the entire package as untrusted.** Every claim is guilty until proven by evidence in `research/`. The audit produces a structured findings report. Fixes happen in a subsequent explore/document re-run.

## Dependencies

- **Input:** a directory with both `research/` and documentation deliverables. The full-mode validator at `../document-abap-solution/scripts/check_run.py` must have passed. Resolve it from this skill's directory, not the shell's current directory. If the sibling skill is missing, report the missing dependency and stop.
- **Python 3.12+** for `scripts/check_trust.py` (mechanical audit) and `scripts/check_review.py` (report validator).
- **SAP read access** (OPTIONAL). When an authorized SAP reader is available, D7 spot-checks run. When unavailable, the review is offline-only and says so.

## Architecture: Script + Judgment

The review is split by what needs comprehension vs what is text comparison:

| Layer | Covers | How |
|-------|--------|-----|
| `scripts/check_trust.py` | D1 (provenance), D2 (consistency), D5 (fabrication), D6 (temporal) | Deterministic Python — run FIRST |
| This skill (LLM) | D3 (completeness), D4 (confidence calibration), D7 (SAP spot-checks) | Reading comprehension + optional SAP access |

Run `check_trust.py` first. Its output (markdown findings) is the starting point — the LLM adds semantic findings the script can't detect, then assembles the combined report.

## Execution

1. **Entry gate:** verify input directory has `research/notes.md` + `README.md`. Run the sibling documentation skill's `scripts/check_run.py <dir>` — any FAIL → stop. Do not use the exploration skill's older full-mode format.
2. **Mechanical audit:** run `python3 <skill_dir>/scripts/check_trust.py <dir>`. Capture the output (markdown fragment with M1, M2, ... findings). This covers D1, D2, D5, D6.
3. **Read the package:** notes.md (census, ledger, patterns, bugs), all doc files, snippet bank listing. Probe the configured SAP reader without changing any objects.
4. **Semantic audit:** evaluate D3, D4, D7 (see below). These require reading comprehension.
5. **Assemble report:** merge mechanical + semantic findings into `review-report.md`, renumbering as F1, F2, ... Apply verdict rules. Run `check_review.py` to validate.

No pauses. The entry gate passes or rejects; the audit runs to completion.

## D3: Completeness — "Are there gaps disguised as coverage?"

Check each:
- Every IMPL in the ledger has at least one recipe (or is a documented stub/dead object).
- The blessed exemplar in §6 is banked in FULL (definition + implementation, not a method excerpt).
- Every cookbook recipe embeds a COMPLETE code unit — no `...` mid-body, no `<!-- snip -->`, no elided branches. Scan for truncation markers.
- The quick-start copy-this exemplar is clean (not in the bug register — a newcomer should not copy buggy code).
- reference.md covers every ledgered object with at least a one-line signature.

## D4: Confidence Calibration — "Are claims scoped to their evidence?"

This is the hardest dimension. The failure mode: a model that read 7 of 12 objects writes "all handlers use X" — the claim is broader than the evidence base.

**How to detect overgeneralization from the ledger:**

1. **Count the evidence base.** Extract the ledger from notes.md. Count rows with status `read-deep` or `read-delta` vs total IMPL rows. This is the READ RATE.
2. **Find universal claims.** Scan all docs for quantifiers: "all", "every", "always", "each", "never", "none", "no handler". Each is a candidate.
3. **For each universal claim, ask:** does the read rate cover the ENTIRE population the claim addresses? Examples:
   - "All 12 handlers use `error_response()`" — were all 12 read? If only 7 were read-deep, this claim extends beyond its evidence by 5 objects.
   - "No implementation uses direct DB access" — were ALL implementations read deep enough to verify this absence?
   - "The framework always validates input" — does "always" mean "in every handler" or "in the base class"? If base class, one deep-read proves it. If handlers, need all.
4. **Scope-narrowing is not a finding.** "Of the 7 handlers read deeply, all use X" is correctly calibrated. The issue is when a qualified observation becomes an unqualified universal somewhere downstream (architecture → README → quick-reference, each level drops the qualifier).
5. **Absence claims require full-population evidence.** "The framework cannot do X" or "no handler supports Y" is an absence claim. Validating absence requires checking every member. From partial coverage, the honest statement is "none of the N read handlers showed X" — not "the framework doesn't support X."
6. **Check confidence propagation across docs.** A finding in notes.md §6 might say "3 of 5 handlers use pattern P" — check whether architecture.md or cookbook.md restated this as "handlers use pattern P" (dropping the fraction). Each such escalation is a finding.

**Severity:** claims over >90% read-rate are LOW (likely true, just technically unsupported). Claims over 50-90% read-rate are MEDIUM. Claims where <50% of the population was read are HIGH — the claim is speculation.

## D7: SAP Spot-Checks (when access available)

Report D7 as not run when no authorized SAP reader is available. Otherwise:

1. **Random sample (5 objects):** stratified from the ledger (1 CORE, 2 IMPL, 1 INFRA, 1 other). Fetch first 30 lines. Compare against the card's "Key logic" bullets — is the card accurate?
2. **Trace verification:** pick the primary lifecycle trace from architecture.md. Follow step 1→2→3 in live source (read the dispatcher, confirm it routes to the named handler, confirm that handler calls what step 3 says).
3. **Registry reconciliation:** SELECT the primary registry table. Compare row count to the census `in-scope` number. Flag any registered object not in the ledger.
4. **Blessed exemplar freshness:** fetch the blessed exemplar's current source. Diff against the banked snippet. If they differ, the docs are stale (the solution was modified since the explore run).

## Report Format

Output: `<dir>/review-report.md`

```
# Documentation Review Report

Review run: <timestamp>
Reviewer: <model/client>
Package: <directory>
SAP access: available | offline only
Prior check_run.py: PASS (<N> checks)
Mechanical audit (check_trust.py): <N> findings (<breakdown>)

## Summary
Findings: <total> (CRITICAL: <n>, HIGH: <n>, MEDIUM: <n>, LOW: <n>, INFO: <n>)
Verdict: TRUSTWORTHY | TRUSTWORTHY WITH CAVEATS | NOT TRUSTWORTHY

## Findings

### F1: <title>
- **Dimension:** D1-D7
- **Severity:** CRITICAL | HIGH | MEDIUM | LOW | INFO
- **Location:** <file>:<line or section>
- **Claim:** "<what the doc says>"
- **Evidence:** "<what research shows>" | "NO EVIDENCE FOUND"
- **Remediation:** <specific fix instruction>

### F2: ...

## Cross-Reference Matrix
<from check_trust.py output>

## Spot-Check Results (if SAP access)
<per-object comparison>

## Verdict Rationale
<why the verdict was chosen>
```

## Severity Scale

| Severity | Meaning | Example |
|----------|---------|---------|
| CRITICAL | Developer building from this doc will produce broken code | Fabricated method signature copied into implementation |
| HIGH | A factual claim is demonstrably wrong or unsupported | "All handlers use T3" but 4 of 12 were never read |
| MEDIUM | Internal inconsistency that confuses but doesn't break | README says 3 patterns, cookbook has 4 recipes |
| LOW | Minor accuracy issue unlikely to cause harm | Object name cased differently across docs |
| INFO | Observation, not a defect | Snippet bank covers 85% of patterns |

## Verdict Rules

- **TRUSTWORTHY:** zero CRITICAL, zero HIGH, ≤3 MEDIUM.
- **TRUSTWORTHY WITH CAVEATS:** zero CRITICAL, ≤2 HIGH, MEDIUM findings listed.
- **NOT TRUSTWORTHY:** any CRITICAL, or ≥3 HIGH, or ≥5 D5 findings (systematic fabrication).

## Reporting

Final message: verdict line, finding counts by severity, top 3 findings (title + severity + one-line). Then: "Full report: `<dir>/review-report.md`."
