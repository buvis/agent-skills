#!/usr/bin/env python3
"""Validate the structure and consistency of a review-abap-solution-documentation report.

Usage:
    python3 check_review.py <output_dir>
    python3 check_review.py --selftest

Checks that review-report.md exists, has the required sections, finding counts
are consistent, severity is valid, verdict follows the rules, and every finding
has all required fields.

Exit 0 only when every check passes.
"""
from __future__ import annotations

import re
import sys
import tempfile
from pathlib import Path
from typing import Callable

Report = Callable[..., None]

REQUIRED_SECTIONS = [
    "summary",
    "findings",
    "cross-reference matrix",
    "verdict rationale",
]

VALID_SEVERITIES = {"CRITICAL", "HIGH", "MEDIUM", "LOW", "INFO"}
VALID_VERDICTS = {"TRUSTWORTHY", "TRUSTWORTHY WITH CAVEATS", "NOT TRUSTWORTHY"}
VALID_DIMENSIONS = {"D1", "D2", "D3", "D4", "D5", "D6", "D7"}

FINDING_RE = re.compile(r"^###\s+F(\d+):", re.M)
SEVERITY_RE = re.compile(r"\*\*Severity:\*\*\s*(CRITICAL|HIGH|MEDIUM|LOW|INFO)", re.I)
DIMENSION_RE = re.compile(r"\*\*Dimension:\*\*\s*(D[1-7])", re.I)
LOCATION_RE = re.compile(r"\*\*Location:\*\*\s*(.+)", re.I)
CLAIM_RE = re.compile(r"\*\*Claim:\*\*\s*(.+)", re.I)
EVIDENCE_RE = re.compile(r"\*\*Evidence:\*\*\s*(.+)", re.I)
REMEDIATION_RE = re.compile(r"\*\*Remediation:\*\*\s*(.+)", re.I)

VERDICT_RE = re.compile(
    r"Verdict:\s*(TRUSTWORTHY WITH CAVEATS|TRUSTWORTHY|NOT TRUSTWORTHY)", re.I
)
SUMMARY_COUNTS_RE = re.compile(
    r"Findings:\s*(\d+)\s*\("
    r"CRITICAL:\s*(\d+),\s*HIGH:\s*(\d+),\s*MEDIUM:\s*(\d+),\s*LOW:\s*(\d+),\s*INFO:\s*(\d+)\)",
    re.I,
)
SAP_ACCESS_RE = re.compile(r"SAP access:\s*(available|offline)", re.I)
REVIEWER_RE = re.compile(r"Reviewer:\s*(.+)", re.I)


def read(path: Path) -> str:
    return path.read_text(encoding="utf-8", errors="replace")


def check_report_exists(root: Path, out: Report) -> str | None:
    path = root / "review-report.md"
    out("review-report.md exists", path.is_file(), "missing from disk")
    if not path.is_file():
        return None
    return read(path)


def check_header(text: str, out: Report) -> None:
    out("reviewer recorded", bool(REVIEWER_RE.search(text)),
        "no 'Reviewer: <model/client>' line")
    out("SAP access stated", bool(SAP_ACCESS_RE.search(text)),
        "no 'SAP access: available|offline' line")
    out("prior check_run.py recorded",
        bool(re.search(r"check_run\.py.*PASS", text, re.I)),
        "no record of prior check_run.py PASS — entry gate may not have run")


def check_sections(text: str, out: Report) -> None:
    lower = text.lower()
    for section in REQUIRED_SECTIONS:
        out("section: %s" % section, section in lower,
            "required section '%s' not found" % section)


def check_verdict(text: str, out: Report) -> str | None:
    m = VERDICT_RE.search(text)
    out("verdict present", bool(m),
        "no 'Verdict: TRUSTWORTHY|TRUSTWORTHY WITH CAVEATS|NOT TRUSTWORTHY' line")
    if not m:
        return None
    verdict = m.group(1).upper()
    out("verdict is valid", verdict in VALID_VERDICTS,
        "verdict '%s' not in allowed set" % verdict)
    return verdict


def check_findings(text: str, out: Report) -> dict[str, int]:
    """Parse individual findings and validate their structure."""
    findings = list(FINDING_RE.finditer(text))
    out("findings present", bool(findings),
        "no '### F<N>:' headings in the Findings section")

    severity_counts: dict[str, int] = {s: 0 for s in VALID_SEVERITIES}
    numbered_ok = True
    fields_ok = True

    for i, match in enumerate(findings):
        num = int(match.group(1))
        if num != i + 1:
            numbered_ok = False

        # Extract this finding's text (until next finding or end)
        start = match.start()
        end = findings[i + 1].start() if i + 1 < len(findings) else len(text)
        block = text[start:end]

        # Check required fields
        sev_m = SEVERITY_RE.search(block)
        dim_m = DIMENSION_RE.search(block)
        loc_m = LOCATION_RE.search(block)
        claim_m = CLAIM_RE.search(block)
        ev_m = EVIDENCE_RE.search(block)
        rem_m = REMEDIATION_RE.search(block)

        if not all([sev_m, dim_m, loc_m, claim_m, ev_m, rem_m]):
            fields_ok = False

        if sev_m:
            sev = sev_m.group(1).upper()
            if sev in severity_counts:
                severity_counts[sev] += 1

        if dim_m:
            dim = dim_m.group(1).upper()
            if dim not in VALID_DIMENSIONS:
                fields_ok = False

    out("findings sequentially numbered", numbered_ok,
        "findings are not numbered F1, F2, F3... sequentially")
    out("findings have all required fields", fields_ok,
        "one or more findings missing Dimension/Severity/Location/Claim/Evidence/Remediation")

    return severity_counts


def check_counts_consistency(text: str, severity_counts: dict[str, int], out: Report) -> None:
    m = SUMMARY_COUNTS_RE.search(text)
    out("summary counts present", bool(m),
        "no 'Findings: N (CRITICAL: n, HIGH: n, ...)' line in Summary")
    if not m:
        return

    claimed_total = int(m.group(1))
    claimed = {
        "CRITICAL": int(m.group(2)),
        "HIGH": int(m.group(3)),
        "MEDIUM": int(m.group(4)),
        "LOW": int(m.group(5)),
        "INFO": int(m.group(6)),
    }

    actual_total = sum(severity_counts.values())
    out("total finding count matches",
        claimed_total == actual_total,
        "summary says %d findings but %d F<N> headings found"
        % (claimed_total, actual_total))

    claimed_sum = sum(claimed.values())
    out("severity breakdown sums to total",
        claimed_sum == claimed_total,
        "breakdown sums to %d but total says %d" % (claimed_sum, claimed_total))

    for sev in VALID_SEVERITIES:
        out("count %s matches" % sev,
            claimed.get(sev, 0) == severity_counts.get(sev, 0),
            "summary claims %s=%d but found %d in findings"
            % (sev, claimed.get(sev, 0), severity_counts.get(sev, 0)))


def check_verdict_rules(text: str, verdict: str | None,
                        severity_counts: dict[str, int], out: Report) -> None:
    if not verdict:
        return

    crit = severity_counts.get("CRITICAL", 0)
    high = severity_counts.get("HIGH", 0)
    med = severity_counts.get("MEDIUM", 0)

    # Count D5 findings for systematic fabrication check
    d5_count = len(re.findall(r"\*\*Dimension:\*\*\s*D5", text, re.I))

    if verdict == "TRUSTWORTHY":
        out("TRUSTWORTHY verdict justified",
            crit == 0 and high == 0 and med <= 3,
            "TRUSTWORTHY requires 0 CRITICAL, 0 HIGH, ≤3 MEDIUM; "
            "got CRITICAL=%d HIGH=%d MEDIUM=%d" % (crit, high, med))
    elif verdict == "TRUSTWORTHY WITH CAVEATS":
        out("CAVEATS verdict justified",
            crit == 0 and high <= 2,
            "CAVEATS requires 0 CRITICAL, ≤2 HIGH; "
            "got CRITICAL=%d HIGH=%d" % (crit, high))
    elif verdict == "NOT TRUSTWORTHY":
        justified = (crit >= 1 or high >= 3 or d5_count >= 5)
        out("NOT TRUSTWORTHY verdict justified", justified,
            "NOT TRUSTWORTHY requires ≥1 CRITICAL, or ≥3 HIGH, or ≥5 D5 findings; "
            "got CRITICAL=%d HIGH=%d D5=%d" % (crit, high, d5_count))


def check_mechanical_audit(text: str, out: Report) -> None:
    """Verify that check_trust.py output is embedded in the report."""
    has_section = bool(re.search(
        r"mechanical audit.*check_trust", text, re.I))
    out("mechanical audit (check_trust.py) section present", has_section,
        "no 'Mechanical Audit (check_trust.py)' section — the deterministic "
        "audit must run first and its output must be embedded in the report")
    if not has_section:
        return
    # Extract the section content
    m = re.search(r"mechanical audit.*?check_trust.*?\n(.*?)(?=\n##\s|\Z)",
                  text, re.I | re.DOTALL)
    if m:
        section = m.group(1)
        # Must have either M-numbered findings or an explicit "0 findings" / "No mechanical findings"
        has_findings = bool(re.search(r"###\s+M\d+:", section))
        has_zero = bool(re.search(r"(0 findings|no mechanical findings)", section, re.I))
        out("mechanical audit has results", has_findings or has_zero,
            "mechanical audit section exists but has no M<N> findings and no "
            "'No mechanical findings' line — check_trust.py output may not "
            "have been pasted")


def run_checks(root: Path) -> list[tuple[str, bool, str]]:
    results: list[tuple[str, bool, str]] = []

    def out(name: str, ok: bool, detail: str = "") -> None:
        results.append((name, bool(ok), detail))

    text = check_report_exists(root, out)
    if text is None:
        return results

    check_header(text, out)
    check_sections(text, out)
    check_mechanical_audit(text, out)
    verdict = check_verdict(text, out)
    severity_counts = check_findings(text, out)
    check_counts_consistency(text, severity_counts, out)
    check_verdict_rules(text, verdict, severity_counts, out)

    return results


# ─── Self-test ─────────────────────────────────────────────────────────────────

PASSING_REPORT = """\
# Documentation Review Report

Review run: 2026-07-24T13:00:00
Reviewer: claude-opus-4 via kiro-cli
Package: ./onboarding-test
SAP access: offline only
Prior check_run.py: PASS (28 checks)

## Summary
Findings: 2 (CRITICAL: 0, HIGH: 0, MEDIUM: 1, LOW: 1, INFO: 0)
Verdict: TRUSTWORTHY

## Findings

### F1: Pattern count mismatch between README and cookbook
- **Dimension:** D2
- **Severity:** MEDIUM
- **Location:** README.md:L42
- **Claim:** "The solution implements 3 distinct patterns"
- **Evidence:** cookbook.md defines 4 recipes with 4 distinct pattern headings
- **Remediation:** Update README pattern count to 4, or merge the two GET variants into one pattern

### F2: Object name casing inconsistency
- **Dimension:** D2
- **Severity:** LOW
- **Location:** architecture.md:L88
- **Claim:** "ZCL_Example_Handler" (mixed case)
- **Evidence:** All other docs and research use "ZCL_EXAMPLE_HANDLER" (upper case)
- **Remediation:** Normalize to ZCL_EXAMPLE_HANDLER throughout architecture.md

## Cross-Reference Matrix
| Metric | README | architecture | cookbook | SPA | notes.md |
|--------|--------|-------------|---------|-----|----------|
| Patterns | 3 | 4 | 4 | 4 | 4 |
| Objects | 24 | 24 | - | 24 | 24 |
| Bugs | 7 | - | - | 7 | 7 |

## Mechanical Audit (check_trust.py)
Checked 6 doc files against 24 research identifiers, 12 snippet files.
**No mechanical findings.** All identifiers trace to research, counts are consistent, no fabrication signals.

## Verdict Rationale
Zero CRITICAL and HIGH findings. The single MEDIUM (count mismatch) is cosmetic
and does not risk broken implementations. Package is trustworthy for developer use.
"""


def selftest() -> int:
    with tempfile.TemporaryDirectory() as td:
        root = Path(td)
        (root / "review-report.md").write_text(PASSING_REPORT, encoding="utf-8")
        fails = [r for r in run_checks(root) if not r[1]]
        assert not fails, "clean fixture should pass, got: %s" % fails

        # Missing report
        (root / "review-report.md").unlink()
        failed = {r[0] for r in run_checks(root) if not r[1]}
        assert "review-report.md exists" in failed, failed

        # Missing fields in finding
        no_fields = PASSING_REPORT.replace(
            "- **Dimension:** D2\n- **Severity:** MEDIUM\n"
            "- **Location:** README.md:L42\n"
            "- **Claim:** \"The solution implements 3 distinct patterns\"\n"
            "- **Evidence:** cookbook.md defines 4 recipes with 4 distinct pattern headings\n"
            "- **Remediation:** Update README pattern count to 4, "
            "or merge the two GET variants into one pattern",
            "Some prose without structured fields"
        )
        (root / "review-report.md").write_text(no_fields, encoding="utf-8")
        failed = {r[0] for r in run_checks(root) if not r[1]}
        assert "findings have all required fields" in failed, failed

        # ── Verdict-rule edge case 1: 2 HIGH + TRUSTWORTHY → should FAIL ──
        two_high = """\
# Documentation Review Report

Review run: 2026-08-01T10:00:00
Reviewer: test-model via test
Package: ./test
SAP access: offline only
Prior check_run.py: PASS (20 checks)

## Summary
Findings: 2 (CRITICAL: 0, HIGH: 2, MEDIUM: 0, LOW: 0, INFO: 0)
Verdict: TRUSTWORTHY

## Findings

### F1: Universal claim without full evidence
- **Dimension:** D4
- **Severity:** HIGH
- **Location:** architecture.md:L50
- **Claim:** "All handlers use error_response()"
- **Evidence:** Only 7 of 12 handlers were read-deep
- **Remediation:** Qualify as "7 of 12 read handlers use..."

### F2: Relationship claim unsupported
- **Dimension:** D4
- **Severity:** HIGH
- **Location:** architecture.md:L120
- **Claim:** "Dispatcher routes to ZCL_HANDLER via config"
- **Evidence:** No snippet shows the dispatch call
- **Remediation:** Bank dispatcher source showing the routing

## Cross-Reference Matrix
| Metric | README | notes.md |
|--------|--------|----------|
| Patterns | 3 | 3 |

## Verdict Rationale
The findings are minor.
"""
        (root / "review-report.md").write_text(two_high, encoding="utf-8")
        failed = {r[0] for r in run_checks(root) if not r[1]}
        assert "TRUSTWORTHY verdict justified" in failed, \
            "2 HIGH + TRUSTWORTHY should fail verdict rule, got: %s" % failed

        # ── Verdict-rule edge case 2: 1 CRITICAL + NOT TRUSTWORTHY → should PASS ──
        one_critical_not_trustworthy = """\
# Documentation Review Report

Review run: 2026-08-01T10:00:00
Reviewer: test-model via test
Package: ./test
SAP access: offline only
Prior check_run.py: PASS (20 checks)

## Summary
Findings: 1 (CRITICAL: 1, HIGH: 0, MEDIUM: 0, LOW: 0, INFO: 0)
Verdict: NOT TRUSTWORTHY

## Findings

### F1: Fabricated method signature in quick-start
- **Dimension:** D5
- **Severity:** CRITICAL
- **Location:** quick-start.md:L30
- **Claim:** "METHOD get_data IMPORTING iv_id TYPE string"
- **Evidence:** Banked snippet shows "METHOD get_data IMPORTING iv_key TYPE i"
- **Remediation:** Re-paste from research/snippets/ verbatim

## Cross-Reference Matrix
| Metric | README | notes.md |
|--------|--------|----------|
| Objects | 10 | 10 |

## Mechanical Audit (check_trust.py)
Checked 6 doc files against 10 research identifiers, 5 snippet files.

### M1: Fabricated method signature
- **Dimension:** D1
- **Severity:** HIGH
- **Location:** quick-start.md
- **Claim:** Code block for ZCL_X
- **Evidence:** Block diverges from banked source
- **Remediation:** Re-paste

## Verdict Rationale
A CRITICAL fabrication in the copy-this code means developers will build broken implementations.
"""
        (root / "review-report.md").write_text(one_critical_not_trustworthy, encoding="utf-8")
        fails = [r for r in run_checks(root) if not r[1]]
        assert not fails, \
            "1 CRITICAL + NOT TRUSTWORTHY should pass all checks, got: %s" % fails

        # ── Verdict-rule edge case 3: 5 D5 findings + TRUSTWORTHY → should FAIL ──
        five_d5_trustworthy = """\
# Documentation Review Report

Review run: 2026-08-01T10:00:00
Reviewer: test-model via test
Package: ./test
SAP access: offline only
Prior check_run.py: PASS (20 checks)

## Summary
Findings: 5 (CRITICAL: 0, HIGH: 0, MEDIUM: 5, LOW: 0, INFO: 0)
Verdict: TRUSTWORTHY

## Findings

### F1: Invented sub-package ZEXAMPLE_APP_SUB1
- **Dimension:** D5
- **Severity:** MEDIUM
- **Location:** reference.md:L10
- **Claim:** "Package ZEXAMPLE_APP_SUB1"
- **Evidence:** Not in research
- **Remediation:** Remove

### F2: Invented sub-package ZEXAMPLE_APP_SUB2
- **Dimension:** D5
- **Severity:** MEDIUM
- **Location:** reference.md:L11
- **Claim:** "Package ZEXAMPLE_APP_SUB2"
- **Evidence:** Not in research
- **Remediation:** Remove

### F3: Invented sub-package ZEXAMPLE_APP_SUB3
- **Dimension:** D5
- **Severity:** MEDIUM
- **Location:** reference.md:L12
- **Claim:** "Package ZEXAMPLE_APP_SUB3"
- **Evidence:** Not in research
- **Remediation:** Remove

### F4: Invented handler ZCL_HANDLER_H05
- **Dimension:** D5
- **Severity:** MEDIUM
- **Location:** reference.md:L20
- **Claim:** "ZCL_HANDLER_H05"
- **Evidence:** Not in ledger — naming convention extrapolation
- **Remediation:** Remove

### F5: Invented handler ZCL_HANDLER_H06
- **Dimension:** D5
- **Severity:** MEDIUM
- **Location:** reference.md:L21
- **Claim:** "ZCL_HANDLER_H06"
- **Evidence:** Not in ledger
- **Remediation:** Remove

## Cross-Reference Matrix
| Metric | README | notes.md |
|--------|--------|----------|
| Objects | 10 | 10 |

## Verdict Rationale
Just naming issues.
"""
        (root / "review-report.md").write_text(five_d5_trustworthy, encoding="utf-8")
        failed = {r[0] for r in run_checks(root) if not r[1]}
        # 5 MEDIUM > 3 → TRUSTWORTHY not justified
        assert "TRUSTWORTHY verdict justified" in failed, \
            "5 MEDIUM D5 + TRUSTWORTHY should fail (>3 MEDIUM), got: %s" % failed

        # ── Verdict-rule edge case 4: 3 HIGH + NOT TRUSTWORTHY → should PASS ──
        three_high_not_trustworthy = """\
# Documentation Review Report

Review run: 2026-08-01T10:00:00
Reviewer: test-model via test
Package: ./test
SAP access: offline only
Prior check_run.py: PASS (20 checks)

## Summary
Findings: 3 (CRITICAL: 0, HIGH: 3, MEDIUM: 0, LOW: 0, INFO: 0)
Verdict: NOT TRUSTWORTHY

## Findings

### F1: Claim unsupported
- **Dimension:** D4
- **Severity:** HIGH
- **Location:** architecture.md:L10
- **Claim:** "All use X"
- **Evidence:** Only 3 of 10 read
- **Remediation:** Qualify

### F2: Another unsupported claim
- **Dimension:** D4
- **Severity:** HIGH
- **Location:** architecture.md:L20
- **Claim:** "Never uses Y"
- **Evidence:** 4 not read
- **Remediation:** Qualify

### F3: Relationship fabricated
- **Dimension:** D1
- **Severity:** HIGH
- **Location:** architecture.md:L30
- **Claim:** "A calls B"
- **Evidence:** No snippet shows this
- **Remediation:** Verify or remove

## Cross-Reference Matrix
| Metric | README | notes.md |
|--------|--------|----------|
| Objects | 10 | 10 |

## Mechanical Audit (check_trust.py)
Checked 6 doc files against 10 research identifiers, 5 snippet files.
**No mechanical findings.** All identifiers trace to research, counts are consistent, no fabrication signals.

## Verdict Rationale
3 HIGH findings = systematic unsupported claims.
"""
        (root / "review-report.md").write_text(three_high_not_trustworthy, encoding="utf-8")
        fails = [r for r in run_checks(root) if not r[1]]
        assert not fails, \
            "3 HIGH + NOT TRUSTWORTHY should pass, got: %s" % fails

    print("selftest OK")
    return 0


def main(argv: list[str]) -> int:
    args = argv[1:]
    if len(args) != 1:
        print(__doc__)
        return 2
    if args[0] == "--selftest":
        return selftest()
    root = Path(args[0])
    if not root.is_dir():
        print("not a directory: %s" % root)
        return 2
    results = run_checks(root)
    print("REVIEW-CHECK %s" % root)
    fails = 0
    for name, ok, detail in results:
        if ok:
            print("  PASS  %s" % name)
        else:
            fails += 1
            print("  FAIL  %s -- %s" % (name, detail))
    print("%d checks, %d FAIL -> %s"
          % (len(results), fails, "OK" if fails == 0 else "REPORT INCOMPLETE"))
    return 1 if fails else 0


if __name__ == "__main__":
    sys.exit(main(sys.argv))
