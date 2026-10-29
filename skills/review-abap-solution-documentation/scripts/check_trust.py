#!/usr/bin/env python3
"""Mechanical trust audit for ABAP solution documentation packages.

Covers D1 (provenance), D2 (internal consistency), D5 (fabrication patterns),
and D6 (temporal integrity) — deterministic checks that compare text against
text, counts against counts. No LLM judgment needed.

Usage:
    python3 check_trust.py <output_dir>
    python3 check_trust.py --selftest

Outputs structured findings in the same format the review skill uses.
Exit code: number of findings with severity >= HIGH (0 = likely trustworthy).
"""
from __future__ import annotations

import json
import re
import sys
import tempfile
from collections import Counter, defaultdict
from datetime import datetime
from pathlib import Path
from typing import NamedTuple

# ─── Types ─────────────────────────────────────────────────────────────────────

class Finding(NamedTuple):
    title: str
    dimension: str
    severity: str  # CRITICAL, HIGH, MEDIUM, LOW, INFO
    location: str
    claim: str
    evidence: str
    remediation: str


# ─── Constants ─────────────────────────────────────────────────────────────────

DOC_FILES = ["README.md", "architecture.md", "quick-start.md",
             "cookbook.md", "reference.md", "quick-reference.md"]

IDENT_RE = re.compile(r"\bZ[A-Z0-9_]{6,}\b")
FETCH_TS_RE = re.compile(
    r'"?\s*Fetched:\s*\S+\s+(\d{4}-\d{2}-\d{2}T?\d{2}:\d{2})', re.I)
ABAP_BLOCK_RE = re.compile(
    r"```(?:abap)?\s*\n(.*?)```", re.DOTALL | re.I)
ABAP_KEYWORDS = re.compile(
    r"\b(CLASS|ENDCLASS|METHOD|ENDMETHOD|SELECT|DATA|TYPES|"
    r"IF|ENDIF|LOOP|ENDLOOP|TRY|ENDTRY|RAISE|CREATE OBJECT)\b", re.I)
COUNT_PATTERNS = [
    (r"(\d+)\s+(?:distinct\s+)?patterns?", "patterns"),
    (r"(\d+)\s+(?:registered\s+)?(?:implementations?|handlers?|objects?)", "objects"),
    (r"(\d+)\s+bugs?", "bugs"),
    (r"(\d+)\s+recipes?", "recipes"),
]
WILDCARD_IDENT_RE = re.compile(r"\bZ[A-Z0-9_]*\*")


# ─── Utilities ─────────────────────────────────────────────────────────────────

def read(path: Path) -> str:
    return path.read_text(encoding="utf-8", errors="replace")


def extract_identifiers(text: str) -> set[str]:
    """Extract all Z-prefixed identifiers (normalized to upper)."""
    return set(IDENT_RE.findall(text.upper()))


def extract_counts(text: str, label: str = "") -> dict[str, list[int]]:
    """Extract numeric claims about patterns/objects/bugs/recipes."""
    counts: dict[str, list[int]] = defaultdict(list)
    for pattern, key in COUNT_PATTERNS:
        for m in re.finditer(pattern, text, re.I):
            counts[key].append(int(m.group(1)))
    return dict(counts)


# ─── D1: Provenance ───────────────────────────────────────────────────────────

def check_d1_identifiers(root: Path, docs: dict[str, str],
                         research_corpus: str) -> list[Finding]:
    """Every Z-identifier in docs must appear in research/."""
    findings = []
    research_idents = extract_identifiers(research_corpus)

    for filename, content in docs.items():
        doc_idents = extract_identifiers(content)
        orphans = doc_idents - research_idents
        if orphans:
            # Group by likely family (shared prefix)
            sample = sorted(orphans)[:5]
            findings.append(Finding(
                title="Identifiers in %s absent from research" % filename,
                dimension="D1",
                severity="HIGH" if len(orphans) >= 3 else "MEDIUM",
                location=filename,
                claim="%d identifier(s) cited" % len(orphans),
                evidence="Not found in ledger, cards, or snippets: %s"
                         % ", ".join(sample),
                remediation="Verify each against the SAP system; if real, the "
                            "explore run missed them; if not, remove from docs"
            ))
    return findings


def check_d1_code_blocks(root: Path, docs: dict[str, str],
                         snippets: dict[str, str]) -> list[Finding]:
    """Code blocks citing real objects should match banked snippets."""
    findings = []
    snippet_by_ident: dict[str, str] = {}
    for name, content in snippets.items():
        for ident in IDENT_RE.findall(content.upper()):
            if ident not in snippet_by_ident:
                snippet_by_ident[ident] = content

    for filename, content in docs.items():
        for m in ABAP_BLOCK_RE.finditer(content):
            block = m.group(1)
            if not ABAP_KEYWORDS.search(block):
                continue
            block_idents = IDENT_RE.findall(block.upper())
            for ident in block_idents:
                if ident in snippet_by_ident:
                    # Compare: strip comment-only lines added as annotations
                    banked = snippet_by_ident[ident]
                    # Normalize for comparison: strip leading receipt, whitespace
                    banked_body = "\n".join(
                        ln for ln in banked.splitlines()
                        if not ln.strip().startswith('" Fetched:'))
                    block_stripped = block.strip()
                    # Check if the doc block is a substring of the banked source
                    # (docs often show a portion)
                    if block_stripped and block_stripped not in banked_body:
                        # Check if it's just whitespace/case differences
                        b_norm = re.sub(r"\s+", " ", banked_body.upper())
                        d_norm = re.sub(r"\s+", " ", block_stripped.upper())
                        if d_norm not in b_norm:
                            findings.append(Finding(
                                title="Code block for %s diverges from banked source"
                                      % ident,
                                dimension="D1",
                                severity="HIGH",
                                location="%s (code block)" % filename,
                                claim="Code block names %s" % ident,
                                evidence="Block content does not match snippet; "
                                         "may be tidied/reformatted/fabricated",
                                remediation="Re-paste from research/snippets/ "
                                            "verbatim"
                            ))
                    break  # One check per block is enough
    return findings


# ─── D2: Internal Consistency ─────────────────────────────────────────────────

def check_d2_counts(docs: dict[str, str],
                    notes_text: str) -> tuple[list[Finding], dict[str, dict[str, int | None]]]:
    """Build cross-doc count matrix and flag disagreements."""
    findings = []
    matrix: dict[str, dict[str, int | None]] = defaultdict(dict)

    sources = dict(docs)
    sources["notes.md"] = notes_text

    for source_name, content in sources.items():
        counts = extract_counts(content)
        for metric, values in counts.items():
            # Take the most-cited value (mode) or max
            if values:
                matrix[metric][source_name] = max(set(values), key=values.count)

    for metric, by_source in matrix.items():
        values = [v for v in by_source.values() if v is not None]
        if len(values) >= 2 and len(set(values)) > 1:
            detail = ", ".join("%s=%d" % (s, v) for s, v in by_source.items()
                              if v is not None)
            findings.append(Finding(
                title="%s count inconsistent across docs" % metric.capitalize(),
                dimension="D2",
                severity="MEDIUM",
                location="cross-doc",
                claim="Multiple docs cite '%s' counts" % metric,
                evidence="Disagreement: %s" % detail,
                remediation="Reconcile against research/notes.md as source of truth"
            ))

    return findings, dict(matrix)


def check_d2_naming(docs: dict[str, str],
                    research_corpus: str) -> list[Finding]:
    """Check that each identifier appears in consistent casing across docs."""
    findings = []
    # Collect all occurrences with original casing
    all_occurrences: dict[str, set[str]] = defaultdict(set)

    for filename, content in docs.items():
        for m in re.finditer(r"\bZ[A-Za-z0-9_]{6,}\b", content):
            name = m.group(0)
            all_occurrences[name.upper()].add(name)

    # Also check against research
    for m in re.finditer(r"\bZ[A-Za-z0-9_]{6,}\b", research_corpus):
        name = m.group(0)
        all_occurrences[name.upper()].add(name)

    inconsistent = {k: v for k, v in all_occurrences.items() if len(v) > 1}

    if inconsistent:
        sample = list(inconsistent.items())[:5]
        for upper_name, variants in sample:
            findings.append(Finding(
                title="Naming variant: %s" % " vs ".join(sorted(variants)),
                dimension="D2",
                severity="LOW",
                location="cross-doc",
                claim="Object referenced as multiple casings",
                evidence="Variants found: %s" % ", ".join(sorted(variants)),
                remediation="Normalize to upper-case (%s) throughout" % upper_name
            ))

    return findings


# ─── D5: Fabrication Patterns ─────────────────────────────────────────────────

def check_d5_wildcards(docs: dict[str, str]) -> list[Finding]:
    """Wildcard patterns in artifact names suggest fabricated sub-packages."""
    findings = []
    for filename, content in docs.items():
        wildcards = WILDCARD_IDENT_RE.findall(content)
        if wildcards:
            findings.append(Finding(
                title="Wildcard in artifact name in %s" % filename,
                dimension="D5",
                severity="MEDIUM",
                location=filename,
                claim="Names with wildcards used: %s" % ", ".join(sorted(set(wildcards))[:3]),
                evidence="A * in a name cell reads as a real artifact; "
                         "check_run.py identifier extractor will flag it",
                remediation="Replace with confirmed parent package name or "
                            "enumerate the specific objects"
            ))
    return findings


def check_d5_family_inflation(docs: dict[str, str],
                              research_idents: set[str]) -> list[Finding]:
    """Detect identifiers that look like they were extrapolated from a naming
    convention (e.g., seeing _H00 and _H01 then inventing _H02-_H05)."""
    findings = []
    doc_idents: set[str] = set()
    for content in docs.values():
        doc_idents.update(extract_identifiers(content))

    # Find identifiers in docs not in research that share a prefix with real ones
    orphans = doc_idents - research_idents
    if not orphans:
        return findings

    # Group orphans by prefix (everything before the last numeric suffix)
    prefix_groups: dict[str, list[str]] = defaultdict(list)
    for ident in orphans:
        prefix = re.sub(r"\d+$", "", ident)
        if prefix and any(r.startswith(prefix) for r in research_idents):
            prefix_groups[prefix].append(ident)

    for prefix, members in prefix_groups.items():
        if len(members) >= 2:
            findings.append(Finding(
                title="Possible family inflation: %s*" % prefix,
                dimension="D5",
                severity="HIGH",
                location="cross-doc",
                claim="%d objects with prefix %s appear in docs"
                      % (len(members), prefix),
                evidence="Not in research: %s (but %s-siblings exist in research)"
                         % (", ".join(sorted(members)[:4]), prefix),
                remediation="Verify each against SAP; if they don't exist, "
                            "remove — this is the classic naming-convention hallucination"
            ))

    return findings


# ─── D6: Temporal Integrity ───────────────────────────────────────────────────

def check_d6_timestamps(root: Path) -> list[Finding]:
    """Check that snippet fetch receipts are from a coherent time window."""
    findings = []
    timestamps: list[tuple[str, datetime]] = []

    snip_dir = root / "research" / "snippets"
    if not snip_dir.is_dir():
        return findings

    for path in snip_dir.glob("*.abap"):
        content = read(path)
        m = FETCH_TS_RE.search(content)
        if m:
            ts_str = m.group(1)
            try:
                # Handle both "2026-07-23T13:02" and "2026-07-23 13:02"
                ts_str = ts_str.replace("T", " ")
                if len(ts_str) == 16:  # YYYY-MM-DD HH:MM
                    ts = datetime.strptime(ts_str, "%Y-%m-%d %H:%M")
                else:
                    ts = datetime.strptime(ts_str[:16], "%Y-%m-%d %H:%M")
                timestamps.append((path.name, ts))
            except ValueError:
                pass

    if len(timestamps) >= 2:
        timestamps.sort(key=lambda x: x[1])
        spread = timestamps[-1][1] - timestamps[0][1]
        hours = spread.total_seconds() / 3600

        if hours > 48:
            findings.append(Finding(
                title="Snippet timestamps span %.0f hours" % hours,
                dimension="D6",
                severity="MEDIUM" if hours < 168 else "HIGH",
                location="research/snippets/",
                claim="All snippets from a single coherent run",
                evidence="Earliest: %s (%s), Latest: %s (%s) — %.0fh spread"
                         % (timestamps[0][0], timestamps[0][1].isoformat(),
                            timestamps[-1][0], timestamps[-1][1].isoformat(),
                            hours),
                remediation="If multi-session, ensure notes.md documents the "
                            "resume; if cobbled from different runs, re-explore"
            ))

    return findings


# ─── D4 Context: Read Rate + Universal Quantifiers (for LLM) ──────────────────

UNIVERSAL_RE = re.compile(
    r"\b(all|every|each|always|never|no\s+(?:handler|implementation|object|class)s?|"
    r"none\s+of)\b",
    re.I)


def extract_d4_context(notes_text: str,
                       docs: dict[str, str]) -> dict:
    """Extract ledger read rate and universal quantifier locations.
    This is NOT findings — it's context for the LLM's D4 judgment."""

    # ── Read rate from ledger ──
    # Look for ledger table rows: | object | domain | status |
    ledger_rows = re.findall(
        r"^\s*\|[^|]+\|[^|]+\|\s*(\S+)\s*\|", notes_text, re.M)
    # Filter to likely IMPL rows (heuristic: rows with read-deep/read-delta/classify/blocked)
    status_counts: dict[str, int] = Counter()
    for status in ledger_rows:
        # Normalize
        s = status.strip().lower().rstrip("|")
        if s in ("read-deep", "read-delta", "classify", "blocked"):
            status_counts[s] += 1

    total_ledger = sum(status_counts.values())
    read_count = status_counts.get("read-deep", 0) + status_counts.get("read-delta", 0)
    read_rate = (read_count / total_ledger * 100) if total_ledger > 0 else 0

    # ── Universal quantifiers in docs ──
    quantifier_locations: list[tuple[str, int, str]] = []  # (file, line, snippet)
    for filename, content in docs.items():
        for i, line in enumerate(content.splitlines(), 1):
            if UNIVERSAL_RE.search(line):
                # Skip if it's inside a code block (indented 4+ or fenced)
                stripped = line.strip()
                if stripped.startswith(("```", "    ", "\t", '"', "*", "|")):
                    continue
                # Keep only lines that make claims (not headings, not bullets with just the word)
                if len(stripped) > 20:  # Filter out trivial matches
                    snippet = stripped[:80]
                    quantifier_locations.append((filename, i, snippet))

    return {
        "read_rate_pct": round(read_rate, 1),
        "read_count": read_count,
        "total_ledger_rows": total_ledger,
        "status_distribution": dict(status_counts),
        "universal_quantifiers": quantifier_locations,
    }


# ─── Runner ────────────────────────────────────────────────────────────────────

def run_audit(root: Path) -> tuple[list[Finding], dict]:
    """Run all mechanical checks. Returns (findings, metadata)."""
    findings: list[Finding] = []

    # Load research corpus
    research_dir = root / "research"
    research_texts = []
    for p in research_dir.rglob("*"):
        if p.is_file():
            research_texts.append(read(p))
    research_corpus = "\n".join(research_texts)
    research_idents = extract_identifiers(research_corpus)

    # Load docs
    docs: dict[str, str] = {}
    for rel in DOC_FILES:
        path = root / rel
        if path.is_file():
            docs[rel] = read(path)
    # Also check optional docs
    for p in root.glob("*-guide.md"):
        docs[p.name] = read(p)
    if (root / "operations.md").is_file():
        docs["operations.md"] = read(root / "operations.md")

    # Load snippets
    snippets: dict[str, str] = {}
    snip_dir = root / "research" / "snippets"
    if snip_dir.is_dir():
        for p in snip_dir.glob("*"):
            if p.is_file():
                snippets[p.name] = read(p)

    # Load notes
    notes_path = root / "research" / "notes.md"
    notes_text = read(notes_path) if notes_path.is_file() else ""

    # D1: Provenance
    findings.extend(check_d1_identifiers(root, docs, research_corpus))
    findings.extend(check_d1_code_blocks(root, docs, snippets))

    # D2: Consistency
    d2_count_findings, matrix = check_d2_counts(docs, notes_text)
    findings.extend(d2_count_findings)
    findings.extend(check_d2_naming(docs, research_corpus))

    # D5: Fabrication
    findings.extend(check_d5_wildcards(docs))
    findings.extend(check_d5_family_inflation(docs, research_idents))

    # D6: Temporal
    findings.extend(check_d6_timestamps(root))

    # D4 Context (not findings — input for LLM judgment)
    d4_context = extract_d4_context(notes_text, docs)

    metadata = {
        "research_idents_count": len(research_idents),
        "doc_files_checked": len(docs),
        "snippets_checked": len(snippets),
        "matrix": matrix,
        "d4_context": d4_context,
    }

    return findings, metadata


def format_report(findings: list[Finding], metadata: dict) -> str:
    """Format findings as markdown fragment for inclusion in review-report.md."""
    lines = ["## Mechanical Audit (check_trust.py)", ""]
    lines.append("Checked %d doc files against %d research identifiers, "
                 "%d snippet files."
                 % (metadata["doc_files_checked"],
                    metadata["research_idents_count"],
                    metadata["snippets_checked"]))
    lines.append("")

    if not findings:
        lines.append("**No mechanical findings.** All identifiers trace to "
                     "research, counts are consistent, no fabrication signals.")
        lines.append("")
    else:
        sev_counts = Counter(f.severity for f in findings)
        lines.append("**%d findings:** CRITICAL=%d, HIGH=%d, MEDIUM=%d, LOW=%d, INFO=%d"
                     % (len(findings), sev_counts["CRITICAL"], sev_counts["HIGH"],
                        sev_counts["MEDIUM"], sev_counts["LOW"], sev_counts["INFO"]))
        lines.append("")

        for i, f in enumerate(findings, 1):
            lines.append("### M%d: %s" % (i, f.title))
            lines.append("- **Dimension:** %s" % f.dimension)
            lines.append("- **Severity:** %s" % f.severity)
            lines.append("- **Location:** %s" % f.location)
            lines.append("- **Claim:** %s" % f.claim)
            lines.append("- **Evidence:** %s" % f.evidence)
            lines.append("- **Remediation:** %s" % f.remediation)
            lines.append("")

    # Cross-reference matrix
    matrix = metadata.get("matrix", {})
    if matrix:
        lines.append("### Cross-Reference Matrix")
        sources = set()
        for by_src in matrix.values():
            sources.update(by_src.keys())
        sources = sorted(sources)
        lines.append("| Metric | %s |" % " | ".join(sources))
        lines.append("|--------|%s|" % "|".join("--------" for _ in sources))
        for metric, by_src in sorted(matrix.items()):
            row = [str(by_src.get(s, "-")) for s in sources]
            lines.append("| %s | %s |" % (metric, " | ".join(row)))
        lines.append("")

    # D4 context for LLM
    d4 = metadata.get("d4_context", {})
    if d4.get("total_ledger_rows", 0) > 0 or d4.get("universal_quantifiers"):
        lines.append("### D4 Context (for semantic review)")
        lines.append("")
        if d4.get("total_ledger_rows", 0) > 0:
            lines.append("**Read rate:** %d/%d ledger objects read (%.0f%%)"
                         % (d4["read_count"], d4["total_ledger_rows"],
                            d4["read_rate_pct"]))
            dist = d4.get("status_distribution", {})
            if dist:
                lines.append("**Status distribution:** %s"
                             % ", ".join("%s=%d" % (k, v)
                                        for k, v in sorted(dist.items())))
            lines.append("")
        quants = d4.get("universal_quantifiers", [])
        if quants:
            lines.append("**Universal quantifiers found (%d):**" % len(quants))
            for filename, lineno, snippet in quants[:20]:
                lines.append("- %s:%d — %s" % (filename, lineno, snippet))
            if len(quants) > 20:
                lines.append("- ... and %d more" % (len(quants) - 20))
            lines.append("")

    return "\n".join(lines)


# ─── Self-test ─────────────────────────────────────────────────────────────────

def selftest() -> int:
    """Build test fixtures and verify checks fire correctly."""

    # ── Clean fixture: should produce zero findings ──
    with tempfile.TemporaryDirectory() as td:
        root = Path(td)
        (root / "research" / "snippets").mkdir(parents=True)
        (root / "research" / "notes.md").write_text(
            "Status: COMPLETE\nCENSUS: raw=5 custom=2 in-scope=2 excluded=0\n"
            "The solution has 2 patterns and 2 objects.\n",
            encoding="utf-8")
        (root / "research" / "core.md").write_text(
            "### ZCL_EXAMPLE_BASE\nKey logic\n### ZCL_EXAMPLE_IMPL\nKey logic\n",
            encoding="utf-8")
        (root / "research" / "snippets" / "base.abap").write_text(
            '" Fetched: tool 2026-07-23T10:00 DEV — ZCL_EXAMPLE_BASE\n'
            "CLASS ZCL_EXAMPLE_BASE DEFINITION.\nENDCLASS.\n",
            encoding="utf-8")
        (root / "research" / "snippets" / "impl.abap").write_text(
            '" Fetched: tool 2026-07-23T10:05 DEV — ZCL_EXAMPLE_IMPL\n'
            "CLASS ZCL_EXAMPLE_IMPL DEFINITION.\nENDCLASS.\n",
            encoding="utf-8")
        (root / "README.md").write_text(
            "# Solution\n2 patterns, 2 objects.\n"
            "Uses ZCL_EXAMPLE_BASE and ZCL_EXAMPLE_IMPL.\n",
            encoding="utf-8")
        (root / "architecture.md").write_text(
            "2 patterns. Objects: ZCL_EXAMPLE_BASE, ZCL_EXAMPLE_IMPL.\n",
            encoding="utf-8")
        (root / "cookbook.md").write_text("2 recipes.\n", encoding="utf-8")
        (root / "reference.md").write_text(
            "ZCL_EXAMPLE_BASE\nZCL_EXAMPLE_IMPL\n", encoding="utf-8")
        (root / "quick-start.md").write_text("Copy ZCL_EXAMPLE_IMPL.\n",
                                             encoding="utf-8")
        (root / "quick-reference.md").write_text("ref\n", encoding="utf-8")

        findings, _ = run_audit(root)
        assert not findings, "clean fixture should produce 0 findings, got: %s" % [
            (f.dimension, f.title) for f in findings]

    # ── Orphan identifier (D1) ──
    with tempfile.TemporaryDirectory() as td:
        root = Path(td)
        (root / "research" / "snippets").mkdir(parents=True)
        (root / "research" / "notes.md").write_text("Status: COMPLETE\n",
                                                    encoding="utf-8")
        (root / "research" / "core.md").write_text("### ZCL_REAL_OBJECT\n",
                                                   encoding="utf-8")
        (root / "README.md").write_text(
            "Uses ZCL_REAL_OBJECT and ZCL_INVENTED_FAKE.\n", encoding="utf-8")

        findings, _ = run_audit(root)
        d1 = [f for f in findings if f.dimension == "D1"]
        assert d1, "expected D1 finding for orphan identifier"
        assert "ZCL_INVENTED_FAKE" in d1[0].evidence

    # ── Family inflation (D5) ──
    with tempfile.TemporaryDirectory() as td:
        root = Path(td)
        (root / "research" / "snippets").mkdir(parents=True)
        (root / "research" / "notes.md").write_text("Status: COMPLETE\n",
                                                    encoding="utf-8")
        (root / "research" / "core.md").write_text(
            "### ZCL_HANDLER_H00\n### ZCL_HANDLER_H01\n", encoding="utf-8")
        (root / "reference.md").write_text(
            "ZCL_HANDLER_H00\nZCL_HANDLER_H01\n"
            "ZCL_HANDLER_H02\nZCL_HANDLER_H03\n"
            "ZCL_HANDLER_H04\n",
            encoding="utf-8")

        findings, _ = run_audit(root)
        d5 = [f for f in findings if f.dimension == "D5"]
        assert d5, "expected D5 finding for family inflation"
        assert "ZCL_HANDLER_H" in d5[0].title or "ZCL_HANDLER_H" in d5[0].evidence

    # ── Timestamp spread (D6) ──
    with tempfile.TemporaryDirectory() as td:
        root = Path(td)
        (root / "research" / "snippets").mkdir(parents=True)
        (root / "research" / "notes.md").write_text("Status: COMPLETE\n",
                                                    encoding="utf-8")
        (root / "research" / "snippets" / "a.abap").write_text(
            '" Fetched: tool 2026-01-01T10:00 DEV — ZCL_OLD\ncode\n',
            encoding="utf-8")
        (root / "research" / "snippets" / "b.abap").write_text(
            '" Fetched: tool 2026-06-15T10:00 DEV — ZCL_NEW\ncode\n',
            encoding="utf-8")

        findings, _ = run_audit(root)
        d6 = [f for f in findings if f.dimension == "D6"]
        assert d6, "expected D6 finding for large timestamp spread"
        assert "hours" in d6[0].title.lower()

    # ── Wildcard in names (D5) ──
    with tempfile.TemporaryDirectory() as td:
        root = Path(td)
        (root / "research" / "snippets").mkdir(parents=True)
        (root / "research" / "notes.md").write_text("Status: COMPLETE\n",
                                                    encoding="utf-8")
        (root / "architecture.md").write_text(
            "Package ZEXAMPLE_APP_TOOLS_* contains all handlers.\n",
            encoding="utf-8")

        findings, _ = run_audit(root)
        d5 = [f for f in findings if f.dimension == "D5"]
        assert any("wildcard" in f.title.lower() for f in d5), \
            "expected D5 wildcard finding"

    # ── Naming inconsistency (D2) ──
    with tempfile.TemporaryDirectory() as td:
        root = Path(td)
        (root / "research" / "snippets").mkdir(parents=True)
        (root / "research" / "notes.md").write_text("Status: COMPLETE\n",
                                                    encoding="utf-8")
        (root / "research" / "core.md").write_text("### ZCL_MY_HANDLER\n",
                                                   encoding="utf-8")
        (root / "README.md").write_text("Uses ZCL_MY_HANDLER.\n",
                                       encoding="utf-8")
        (root / "architecture.md").write_text("Uses ZCL_My_Handler.\n",
                                             encoding="utf-8")

        findings, _ = run_audit(root)
        d2 = [f for f in findings if f.dimension == "D2"]
        assert any("naming" in f.title.lower() or "variant" in f.title.lower()
                   for f in d2), "expected D2 naming finding"

    # ── Count inconsistency (D2) ──
    with tempfile.TemporaryDirectory() as td:
        root = Path(td)
        (root / "research" / "snippets").mkdir(parents=True)
        (root / "research" / "notes.md").write_text(
            "Status: COMPLETE\n4 patterns found.\n", encoding="utf-8")
        (root / "README.md").write_text("3 patterns in the solution.\n",
                                       encoding="utf-8")
        (root / "architecture.md").write_text("4 patterns.\n",
                                             encoding="utf-8")

        findings, _ = run_audit(root)
        d2 = [f for f in findings if f.dimension == "D2" and "count" in f.title.lower()]
        assert d2, "expected D2 count inconsistency finding"

    print("selftest OK")
    return 0


# ─── Main ──────────────────────────────────────────────────────────────────────

def main(argv: list[str]) -> int:
    args = argv[1:]
    if len(args) != 1:
        print(__doc__)
        return 2
    if args[0] == "--selftest":
        return selftest()
    root = Path(args[0])
    if not root.is_dir():
        print("not a directory: %s" % root, file=sys.stderr)
        return 2

    findings, metadata = run_audit(root)
    report = format_report(findings, metadata)
    print(report)

    # Exit code = count of HIGH+ findings
    high_plus = sum(1 for f in findings if f.severity in ("CRITICAL", "HIGH"))
    return min(high_plus, 125)  # cap at 125 (convention)


if __name__ == "__main__":
    sys.exit(main(sys.argv))
