#!/usr/bin/env python3
"""Run-integrity self-check for ABAP-solution research and documentation runs.

Usage:
    python3 check_run.py <output_dir>                  # full check (docs run)
    python3 check_run.py --research-only <output_dir>  # research package only
    python3 check_run.py --selftest

--research-only verifies the explore-abap-solution contract: research/notes.md
(census, scope decision, ledger, gates, sweep, status), domain cards, and a
receipted snippet bank. The full check adds the document-abap-solution
contract on top: doc deliverables, banners on INCOMPLETE runs, cited sources
banked, doc identifiers traced to research/, explorer and solution.json.
It cannot check truth against the SAP system -- Phase 6 does that when access
exists. Exit 0 only when every check passes. Paste the output verbatim into
the Validation Report and the final report; never edit files just to turn a
marker green.
"""
from __future__ import annotations

import json
import re
import sys
import tempfile
from pathlib import Path
from typing import Callable

Report = Callable[..., None]

REQUIRED_DOCS = ["README.md", "architecture.md", "quick-start.md",
                 "cookbook.md", "reference.md", "quick-reference.md"]
EXPLORER_HTML = "explorer/dist/explorer.html"
SOLUTION_KEYS = ["meta", "layers", "objects", "edges", "traces", "patterns",
                 "recipes", "wizard", "cheatsheet", "glossary", "gotchas"]
GATE_RE = re.compile(r"GATE:\s*(PASS|INCOMPLETE)", re.I)
STATUS_RE = re.compile(r"^[>\s*_-]*status[*_]*\s*:\s*(.+)$", re.I | re.M)
BANNER_RE = re.compile(r"partial[ -]coverage|partial map", re.I)
PENDING_RE = re.compile(r"^\s*\|.*\bpending\b", re.I | re.M)
REFS_RE = re.compile(r"references\s+loaded\s*:?", re.I)
SCOPE_RE = re.compile(r"scope\s+decision\s*[*_]*\s*:?", re.I)
BUG_HEDGE_RE = re.compile(r"\blikely\b|\bprobably\b|\bpresumably\b", re.I)
CENSUS_RE = re.compile(
    r"CENSUS:\s*raw=(\d+)\s+custom=(\d+)\s+in-scope=(\d+)\s+excluded=(\d+)", re.I)
ABAP_CODE_RE = re.compile(r"ENDMETHOD|ENDCLASS|REDEFINITION")


def read(path: Path) -> str:
    return path.read_text(encoding="utf-8", errors="replace")


def check_deliverables(root: Path, out: Report, research_only: bool) -> None:
    doc_files = [] if research_only else REQUIRED_DOCS + [EXPLORER_HTML]
    for rel in doc_files + ["research/notes.md"]:
        out(rel, (root / rel).is_file(), "missing from disk")
    cards = [p for p in (root / "research").glob("*.md") if p.name != "notes.md"]
    out("research/ object cards", bool(cards), "no research/{domain}.md card files")
    snippets = list((root / "research" / "snippets").glob("*"))
    out("research/snippets/ bank", bool(snippets), "snippet bank empty or missing")


def _ident_pattern(min_len: int) -> "re.Pattern[str]":
    """Custom ABAP identifiers: Z-prefixed, Y-prefixed (must contain an
    underscore, so ordinary Y-words in prose do not match), and
    /NAMESPACE/NAME. The namespace branch is case-sensitive so file paths
    like /usr/bin never match."""
    n = min_len
    return re.compile(
        r"(?<![A-Za-z0-9_/])(?:"
        r"Z[A-Z0-9_]{%d,}"
        r"|Y(?=[A-Z0-9]*_)[A-Z0-9_]{%d,}"
        r"|(?-i:/[A-Z][A-Z0-9_]{1,9}/)[A-Z0-9_]{%d,}"
        r")(?![A-Za-z0-9_])" % (n, n, max(n, 3)), re.I)


def custom_idents(text: str, min_len: int) -> list[str]:
    """Upper-cased custom identifiers found in text."""
    return [m.upper() for m in _ident_pattern(min_len).findall(text)]


def has_receipt(text: str) -> bool:
    """The receipt must be on the FIRST line, as the contract states."""
    first = text.lstrip("\ufeff").split("\n", 1)[0]
    return "Fetched:" in first


def check_snippet_receipts(root: Path, out: Report) -> None:
    snip_dir = root / "research" / "snippets"
    abap = list(snip_dir.glob("*.abap"))
    if not abap:
        return  # empty bank already reported by check_deliverables
    unreceipted = [p.name for p in abap if not has_receipt(read(p))]
    out("snippets carry fetch receipts", not unreceipted,
        "banked without a '\" Fetched: <tool> <timestamp>' first-line "
        "receipt (unfetched = memory, not source): " + ", ".join(sorted(unreceipted)[:6]))


def check_blessed_banked(root: Path, notes_text: str, out: Report) -> None:
    """The blessed pattern's exemplar is what the document run's quick-start
    copies verbatim -- so its FULL source must be in the bank. Naming it in the
    evolution section while banking only a sibling variant leaves the copy-this
    centerpiece unbanked, forcing the writer to fabricate or ship a [GAP]."""
    m = re.search(r"blessed[^\n]*?(?:pattern|exemplar)?[^\n]*", notes_text, re.I)
    if not m:
        return  # no blessed pattern declared (e.g. kernel-less) -- nothing to check
    # collect Z-identifiers from the blessed line and the line after it
    tail = notes_text[m.start():]
    window = "".join(tail.splitlines(keepends=True)[:2])
    named = set(custom_idents(window, 4))
    if not named:
        return  # blessed pattern named by pattern-ID only, no object cited here
    bank = " ".join(read(p).upper() for p in (root / "research" / "snippets").glob("*")
                    if p.is_file())
    banked = {n for n in named if n.upper() in bank}
    out("blessed exemplar is banked", bool(banked),
        "the blessed-pattern object(s) %s are named but none appear in the "
        "snippet bank -- the document run's quick-start copies this verbatim; "
        "bank its full source (a sibling variant does not count)"
        % ", ".join(sorted(named)))


def check_notes(notes_text: str, out: Report) -> bool:
    """Reports notes.md checks; returns True when the run is INCOMPLETE."""
    gates = [m.group(1).upper() for m in GATE_RE.finditer(notes_text)]
    out("coverage gate report", bool(gates),
        "no 'GATE: PASS|INCOMPLETE' line in notes.md")
    out("pattern gate report", bool(re.search(r"pattern gate", notes_text, re.I)),
        "no pattern-gate report in notes.md")
    out("ledger has no pending rows", not PENDING_RE.search(notes_text),
        "ledger row(s) still 'pending'")
    out("Validation Report section", bool(re.search(r"validation report", notes_text, re.I)),
        "no '## Validation Report' in notes.md -> Phase 6 did not run")
    out("access receipt", bool(re.search(r"access (receipt|probe)", notes_text, re.I)),
        "no access receipt/probe in notes.md (Phase 0)")
    out("References loaded log", bool(REFS_RE.search(notes_text)),
        "no 'References loaded:' line -- record each reference file as "
        "loaded or 'unavailable: <error>'")
    out("runner recorded", bool(re.search(r"runner\s*:", notes_text, re.I)),
        "no 'Runner: <model/client>' line in notes.md Access & Target")
    census = CENSUS_RE.findall(notes_text)
    out("CENSUS line present", bool(census),
        "no 'CENSUS: raw=N custom=C in-scope=S excluded=E' line -- scope was assumed, not measured")
    out("scope decision recorded", bool(SCOPE_RE.search(notes_text)),
        "no 'Scope decision:' line or section -- the Phase-1 checkpoint's answer "
        "(or the unattended default) was never recorded; the boundary is unowned")
    bug_m = re.search(r"^.*bug\s*register.*$", notes_text, re.I | re.M)
    if bug_m:
        section = notes_text[bug_m.end():]
        nxt = re.search(r"^#{1,6}\s", section, re.M)
        section = section[:nxt.start()] if nxt else section
        hedged = [ln.strip()[:60] for ln in section.splitlines()
                  if BUG_HEDGE_RE.search(ln)]
        out("bug register cites evidence, not speculation", not hedged,
            "bug entries hedged with likely/probably/presumably -- a bug "
            "without verbatim offending lines is a guess, not a finding "
            "(re-read the source or move it to the debt list): "
            + "; ".join(hedged[:3]))
    for raw, custom, in_scope, excluded in census:
        out("CENSUS arithmetic closes",
            int(custom) == int(in_scope) + int(excluded),
            "custom=%s but in-scope=%s + excluded=%s -- census hits vanished "
            "without a ledger row" % (custom, in_scope, excluded))
    sweep_ok = False
    sweep_m = re.search(r"^.*sweep\s*log.*$", notes_text, re.I | re.M)
    if sweep_m:
        section = notes_text[sweep_m.end():]
        nxt = re.search(r"^#{1,6}\s", section, re.M)
        section = section[:nxt.start()] if nxt else section
        lines = [ln for ln in section.splitlines() if ln.strip()]
        sweep_ok = len(lines) >= 3 and not re.search(r"pending", " ".join(lines[:2]), re.I)
    out("sweep log", sweep_ok,
        "sweep log missing or empty -- a heading with '(pending)' under it is "
        "not a sweep; log every checked corner, including 'none found'")
    out("gates unqualified", not re.search(r"gate\s*:\s*pass\s*\(", notes_text, re.I),
        "'GATE: PASS (...)' is a qualified pass = a failed condition wearing a "
        "PASS label -- fix the condition or declare INCOMPLETE")
    out("gate consistent with ledger",
        not ("PASS" in gates and PENDING_RE.search(notes_text)),
        "a 'GATE: PASS' sits above ledger rows still 'pending' -- the gate "
        "report is false; the coverage gate cannot pass an unfinished ledger")

    status_word, qualifier = "", ""
    m = STATUS_RE.search(notes_text)
    if m:
        value = m.group(1).strip().strip("*_ ")
        parts = value.split(None, 1)
        status_word = parts[0].upper().strip(".,;:")
        qualifier = parts[1] if len(parts) > 1 else ""
    out("STATUS line present", status_word in ("COMPLETE", "INCOMPLETE"),
        "notes.md needs 'Status: COMPLETE' or 'Status: INCOMPLETE - <why>'")
    if status_word == "COMPLETE":
        out("STATUS unqualified", not qualifier,
            "'COMPLETE %s' is a qualified pass -> write INCOMPLETE" % qualifier[:40])
        out("STATUS matches gate", bool(gates) and "INCOMPLETE" not in gates,
            "status COMPLETE above a 'GATE: INCOMPLETE' report"
            if "INCOMPLETE" in gates else
            "status COMPLETE with NO gate report -- COMPLETE is unproven "
            "without a 'GATE: PASS' line on disk")
    return status_word == "INCOMPLETE" or "INCOMPLETE" in gates


UNLOADED_RE = re.compile(r"not\s+loaded|not\s+read|unavailable|improvis|skipped|pending", re.I)
REF_OUTPUTS = [("exploration-tactics", ["research/notes.md"]),
               ("doc-blueprints", REQUIRED_DOCS),
               ("spa-blueprint", [EXPLORER_HTML])]


def check_references(root: Path, notes_text: str, out: Report) -> None:
    """A reference marked not-loaded while its phase's output exists on disk
    means that output was improvised without its blueprint. The honest paths
    are loading the reference or going INCOMPLETE -- not producing anyway."""
    m = REFS_RE.search(notes_text)
    if not m:
        return  # missing line already reported by check_notes
    seg = notes_text[m.start():]
    nxt = re.search(r"\n#{1,6}\s", seg)
    line = (seg[:nxt.start()] if nxt else seg).lower()
    positions = sorted((line.find(ref), ref) for ref, _ in REF_OUTPUTS
                       if line.find(ref) >= 0)
    for i, (pos, ref) in enumerate(positions):
        window = line[pos:positions[i + 1][0] if i + 1 < len(positions) else len(line)]
        if not UNLOADED_RE.search(window):
            continue
        produced = [rel for rel in dict(REF_OUTPUTS)[ref] if (root / rel).is_file()]
        out("%s loaded before its output" % ref, not produced,
            "References line marks %s as not loaded, yet %s exists -- output "
            "improvised without its blueprint; load the reference and "
            "regenerate, or record why and declare INCOMPLETE"
            % (ref, ", ".join(produced[:3])))


def check_banners(root: Path, out: Report) -> None:
    docs = list(REQUIRED_DOCS) + [EXPLORER_HTML]
    docs += [p.name for p in root.glob("*-guide.md")]
    if (root / "operations.md").is_file():
        docs.append("operations.md")
    for rel in docs:
        path = root / rel
        if not path.is_file():
            continue  # absence already reported by check_deliverables
        out("banner in " + rel, bool(BANNER_RE.search(read(path))),
            "INCOMPLETE run but no partial-coverage banner")


def check_source_citations(root: Path, out: Report) -> None:
    """Every object a doc cites as 'Source:' must appear in the snippet bank --
    an unbanked citation cannot be provenance-diffed, which is where memory-
    paraphrase (invented constants, mutated signatures) hides."""
    snip_dir = root / "research" / "snippets"
    bank = " ".join(read(p).upper() for p in snip_dir.glob("*") if p.is_file())
    missing: set[str] = set()
    for rel in REQUIRED_DOCS + [p.name for p in root.glob("*-guide.md")]:
        path = root / rel
        if not path.is_file():
            continue
        for m in re.finditer(r"Source:([^\n]*)", read(path), re.I):
            for ident in custom_idents(m.group(1), 2):
                if ident.upper() not in bank:
                    missing.add(ident.upper())
    out("cited sources are banked", not missing,
        "Source-cited objects with no snippet in the bank (nothing to "
        "provenance-diff against): " + ", ".join(sorted(missing)[:8]))


def check_doc_identifiers(root: Path, out: Report) -> None:
    """Every custom identifier the inventory docs name must appear somewhere in
    research/ (ledger, cards, snippets). An identifier with no research trace is
    invented inventory -- the failure mode where a writer fabricates whole
    object families under a real census count. System-side existence still
    needs Phase 6 with access; this catches the ledger-side half mechanically."""
    corpus = " ".join(read(p).upper() for p in (root / "research").rglob("*")
                      if p.is_file())
    if not corpus.strip():
        return  # research/ absence already reported
    missing: set[str] = set()
    for rel in ["README.md", "architecture.md", "reference.md"]:
        path = root / rel
        if not path.is_file():
            continue
        for ident in set(custom_idents(read(path), 6)):
            if ident not in corpus:
                missing.add(ident)
    out("doc identifiers trace to research", not missing,
        "%d identifiers in README/architecture/reference appear nowhere in "
        "research/ (ledger, cards, snippets) -- invented inventory: %s"
        % (len(missing), ", ".join(sorted(missing)[:8])))


def check_explorer(root: Path, out: Report) -> None:
    path = root / EXPLORER_HTML
    if not path.is_file():
        return  # absence already reported
    html = read(path)
    out("canonical stylesheet embedded", "abapx-style v" in html,
        "no 'abapx-style' marker in explorer.html -- embed assets/explorer.css verbatim")
    if ABAP_CODE_RE.search(html):
        out("code blocks preserve linebreaks", "<pre" in html,
            "ABAP code present but no <pre> element -- HTML collapses the "
            "linebreaks; render code in <pre> (canonical stylesheet styles it)")


def check_solution_json(root: Path, out: Report) -> None:
    """Validate the solution data inlined in explorer.html as
    <script type="application/json" id="solution-data">."""
    path = root / EXPLORER_HTML
    if not path.is_file():
        return  # absence already reported
    html = read(path)
    m = re.search(
        r'<script[^>]*type="application/json"[^>]*id="solution-data"[^>]*>(.*?)</script>',
        html, re.DOTALL)
    if not m:
        out("solution data inlined", False,
            "no <script type=\"application/json\" id=\"solution-data\"> in explorer.html "
            "-- the solution data must be INLINED, not loaded via fetch/XHR "
            "(file:// protocol blocks external requests)")
        return
    raw = m.group(1).strip()
    if not raw or raw == '{"_placeholder": true}' or len(raw) < 50:
        out("solution data inlined", False,
            "solution-data script tag contains a placeholder or is empty -- "
            "inline the actual JSON data, not a stub that fetches externally")
        return
    out("solution data inlined", True)
    try:
        data = json.loads(raw)
    except ValueError as err:
        out("solution data parses", False, str(err))
        return
    missing = [k for k in SOLUTION_KEYS if k not in data]
    out("solution.json contract keys", not missing, "missing: " + ", ".join(missing))
    objs = data.get("objects")
    out("solution.json objects[] non-empty", isinstance(objs, list) and bool(objs),
        "an explorer without objects[] is a brochure")
    cookbook = root / "cookbook.md"
    recipes = data.get("recipes")
    if cookbook.is_file() and isinstance(recipes, list):
        defined = {m.group(1) for m in re.finditer(r"^#{2,3}\s*R(\d+)\b", read(cookbook), re.M)}
        if defined:  # only when the cookbook uses R-numbered headings
            out("explorer recipes cover the cookbook",
                len(recipes) >= len(defined),
                "solution.json has %d recipes, cookbook defines %d -- the explorer's "
                "recipe set IS the cookbook's set, not a subset" % (len(recipes), len(defined)))


def run_checks(root: Path, research_only: bool = False) -> list[tuple[str, bool, str]]:
    results: list[tuple[str, bool, str]] = []

    def out(name: str, ok: bool, detail: str = "") -> None:
        results.append((name, bool(ok), detail))

    check_deliverables(root, out, research_only)
    notes = root / "research" / "notes.md"
    incomplete = False
    if notes.is_file():
        notes_text = read(notes)
        incomplete = check_notes(notes_text, out)
        check_references(root, notes_text, out)
        check_blessed_banked(root, notes_text, out)
    check_snippet_receipts(root, out)
    if research_only:
        return results
    if incomplete:
        check_banners(root, out)
    check_source_citations(root, out)
    check_doc_identifiers(root, out)
    check_explorer(root, out)
    check_solution_json(root, out)
    return results


PASSING_NOTES = """Status: COMPLETE

References loaded: exploration-tactics (Phase 0), doc-blueprints (Phase 4), spa-blueprint (Phase 5)
Runner: test-model via test-client
CENSUS: raw=10 custom=2 in-scope=1 excluded=1
Scope decision: whole solution (user, T00)

## Access Receipt
Object: ZCL_X | first lines recorded

## Ledger
| ZCL_X | core | read-deep |

## Sweep Log
checked local classes: none found
checked dynamic dispatch: registry-driven, one attach loop
checked macros and transformations: none found

## Gate Reports
Coverage Gate: visited 1/1. GATE: PASS
Pattern Gate: 1 pattern covers 1 implementation. Snippets banked: P1: 1.

## Validation Report
identifiers 5/5 resolved
"""


def selftest() -> int:
    with tempfile.TemporaryDirectory() as td:
        root = Path(td)
        (root / "explorer" / "dist").mkdir(parents=True)
        (root / "research" / "snippets").mkdir(parents=True)
        for rel in REQUIRED_DOCS:
            (root / rel).write_text("doc", encoding="utf-8")
        (root / "cookbook.md").write_text("## R1\nSource: ZCL_X\ncode", encoding="utf-8")
        (root / EXPLORER_HTML).write_text(
            '<html><style>/* abapx-style v1 */</style>'
            '<script type="application/json" id="solution-data">'
            + json.dumps({k: [{"x": 1}] for k in SOLUTION_KEYS})
            + '</script>', encoding="utf-8")
        (root / "research" / "snippets" / "p1-x.abap").write_text(
            '" Fetched: test-tool 2026-01-01 T00 - ZCL_X\nCLASS ZCL_X.', encoding="utf-8")
        (root / "research" / "core.md").write_text("### ZCL_X", encoding="utf-8")
        (root / "research" / "notes.md").write_text(PASSING_NOTES, encoding="utf-8")
        fails = [r for r in run_checks(root) if not r[1]]
        assert not fails, "clean fixture should pass, got: %s" % fails

        (root / "research" / "notes.md").write_text(
            "**Status:** COMPLETE (scope-limited)\n\n| ZCL_Y | domain | pending |\n",
            encoding="utf-8")
        failed = {r[0] for r in run_checks(root) if not r[1]}
        for expected in ("coverage gate report", "STATUS unqualified",
                         "STATUS matches gate", "scope decision recorded",
                         "ledger has no pending rows", "Validation Report section",
                         "References loaded log", "CENSUS line present"):
            assert expected in failed, "expected FAIL: %s (got %s)" % (expected, failed)

        (root / "research" / "notes.md").write_text(
            PASSING_NOTES.replace(
                "References loaded: exploration-tactics (Phase 0), "
                "doc-blueprints (Phase 4), spa-blueprint (Phase 5)",
                "References loaded: exploration-tactics (Phase 0), doc-blueprints "
                "(not loaded -- improvised), spa-blueprint (unavailable: glob failed)"),
            encoding="utf-8")
        failed = {r[0] for r in run_checks(root) if not r[1]}
        for expected in ("doc-blueprints loaded before its output",
                         "spa-blueprint loaded before its output"):
            assert expected in failed, "expected FAIL: %s (got %s)" % (expected, failed)
        assert "exploration-tactics loaded before its output" not in failed, failed

        (root / "research" / "notes.md").write_text(PASSING_NOTES, encoding="utf-8")
        (root / "reference.md").write_text(
            "| ZCL_TOTALLY_INVENTED_H00 | CLAS | fabricated family |",
            encoding="utf-8")
        failed = {r[0] for r in run_checks(root) if not r[1]}
        assert "doc identifiers trace to research" in failed, failed
        (root / "reference.md").write_text("doc", encoding="utf-8")

        (root / "research" / "notes.md").write_text(
            PASSING_NOTES.replace("Coverage Gate: visited 1/1. GATE: PASS",
                                  "Coverage Gate: GATE: PASS (registry degraded)")
            + "\n| ZCL_Y | domain | pending |\n", encoding="utf-8")
        failed = {r[0] for r in run_checks(root) if not r[1]}
        for expected in ("gates unqualified", "gate consistent with ledger"):
            assert expected in failed, "expected FAIL: %s (got %s)" % (expected, failed)

        (root / "research" / "notes.md").write_text(
            PASSING_NOTES + "\n## Bug Register\n"
            "| B1 | ZCL_X | HIGH | likely copies the wrong logic |\n",
            encoding="utf-8")
        failed = {r[0] for r in run_checks(root) if not r[1]}
        assert "bug register cites evidence, not speculation" in failed, failed

        # blessed exemplar named but not banked (only a sibling variant is)
        (root / "research" / "notes.md").write_text(
            PASSING_NOTES + "\nBlessed pattern for new handlers: P3, "
            "exemplar ZCL_BLESSED_H00.\n", encoding="utf-8")
        failed = {r[0] for r in run_checks(root) if not r[1]}
        assert "blessed exemplar is banked" in failed, failed
        # ...and passes once that object is in the bank
        (root / "research" / "snippets" / "blessed.abap").write_text(
            '" Fetched: t 2026-01-01 - ZCL_BLESSED_H00\nCLASS ZCL_BLESSED_H00.',
            encoding="utf-8")
        passed = {r[0] for r in run_checks(root) if r[1]}
        assert "blessed exemplar is banked" in passed, passed
        (root / "research" / "snippets" / "blessed.abap").unlink()

        # receipt must be on the FIRST line, not buried below the code
        late = root / "research" / "snippets" / "late.abap"
        late.write_text('CLASS ZCL_X.\n" Fetched: t 2026-01-01 - ZCL_X\n', encoding="utf-8")
        failed = {r[0] for r in run_checks(root) if not r[1]}
        assert "snippets carry fetch receipts" in failed, failed
        late.unlink()

        # Y-prefixed and /NAMESPACE/ identifiers are covered, paths are not
        for invented in ("YCL_INVENTED_ONE", "/EXAMPLE/INVENTED_CLASS"):
            (root / "reference.md").write_text(
                "| %s | CLAS | fabricated |" % invented, encoding="utf-8")
            failed = {r[0] for r in run_checks(root) if not r[1]}
            assert "doc identifiers trace to research" in failed, (invented, failed)
        (root / "reference.md").write_text("see /usr/local/bin/tool", encoding="utf-8")
        failed = {r[0] for r in run_checks(root) if not r[1]}
        assert "doc identifiers trace to research" not in failed, failed
        (root / "reference.md").write_text("doc", encoding="utf-8")

    with tempfile.TemporaryDirectory() as td:
        root = Path(td)  # research-only package: no docs, no explorer
        (root / "research" / "snippets").mkdir(parents=True)
        (root / "research" / "snippets" / "p1-x.abap").write_text(
            '" Fetched: test-tool 2026-01-01 T00 - ZCL_X\nCLASS ZCL_X.', encoding="utf-8")
        (root / "research" / "core.md").write_text("### ZCL_X", encoding="utf-8")
        (root / "research" / "notes.md").write_text(PASSING_NOTES, encoding="utf-8")
        fails = [r for r in run_checks(root, research_only=True) if not r[1]]
        assert not fails, "research-only fixture should pass, got: %s" % fails
        full_fails = {r[0] for r in run_checks(root) if not r[1]}
        assert "README.md" in full_fails and EXPLORER_HTML in full_fails, full_fails
    print("selftest OK")
    return 0


def main(argv: list[str]) -> int:
    args = argv[1:]
    research_only = "--research-only" in args
    args = [a for a in args if a != "--research-only"]
    if len(args) != 1:
        print(__doc__)
        return 2
    if args[0] == "--selftest":
        return selftest()
    root = Path(args[0])
    if not root.is_dir():
        print("not a directory: %s" % root)
        return 2
    results = run_checks(root, research_only)
    print("SELF-CHECK%s %s" % (" (research-only)" if research_only else "", root))
    fails = 0
    for name, ok, detail in results:
        if ok:
            print("  PASS  %s" % name)
        else:
            fails += 1
            print("  FAIL  %s -- %s" % (name, detail))
    print("%d checks, %d FAIL -> %s"
          % (len(results), fails, "OK" if fails == 0 else "NOT DELIVERABLE"))
    return 1 if fails else 0


if __name__ == "__main__":
    sys.exit(main(sys.argv))
