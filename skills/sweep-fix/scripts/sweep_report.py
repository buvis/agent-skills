"""Render the plain-text report of a sweep."""
from pathlib import Path

from sweep_rule_pack import _render_astgrep_rule_block

DEADLINE_REASON = "sweep deadline expired"


def _render_hits_section(hits, kind):
    lines = [f"Hits ({len(hits)}):"]
    for hit in hits:
        lines.append(f"- {hit['repo']} {hit['file']}:{hit['line']}: {hit['snippet']}")
    lines.append("")

    if kind == "astgrep":
        uncovered_exts = sorted({Path(hit["file"]).suffix or hit["file"] for hit in hits if hit["lang"] is None})
        if uncovered_exts:
            lines.append(f"Uncovered languages (no ast-grep lang mapping): {', '.join(uncovered_exts)}")
            lines.append("")

    return lines


def _render_suppressed_section(suppressed):
    lines = []
    if suppressed:
        lines.append("Suppressed:")
        for repo, count in suppressed.items():
            lines.append(f"- {repo}: {count} more hits suppressed (cap reached)")
        lines.append("")
    return lines


def _render_partial_section(failed):
    partial_count = sum(1 for reason in failed.values() if reason == DEADLINE_REASON)
    if not partial_count:
        return []
    return [f"Partial: {partial_count} repos not scanned (sweep deadline expired)", ""]


def _render_failed_section(failed):
    lines = []
    if failed:
        lines.append("Failed:")
        for repo, reason in failed.items():
            collapsed_reason = " ".join(reason.split())
            lines.append(f"- {repo}: could not be scanned ({collapsed_reason})")
        lines.append("")
    return lines


def _render_gaps_section(gaps):
    lines = [f"Gaps ({len(gaps)}):"]
    for gap in gaps:
        lines.append(f"- {gap}")
    lines.append("")
    return lines


def render_report(derivation, hits, gaps, suppressed, failed):
    """Render a plain-text sweep report from scan results.

    Pure string formatting: no subprocess calls, no file I/O. `derivation`
    carries `kind`, `pattern`, `reason`, `control_term` describing the sweep
    that was run. `failed` maps `str(repo)` to a reason string for repos
    that could not be scanned at all, distinct from `suppressed` (repos that
    were scanned but had hits truncated at the cap). When `kind` is
    "astgrep", appends an ast-grep rule-pack YAML block (one document per
    distinct language seen in `hits`, joined with `---`) that can be saved
    to a `.yml` file and run unedited with `ast-grep scan --rule`.
    """
    lines = [
        f"Kind: {derivation['kind']}",
        f"Pattern: {derivation['pattern']}",
        f"Reason: {derivation['reason']}",
        "",
    ]
    lines.extend(_render_hits_section(hits, derivation["kind"]))
    lines.extend(_render_suppressed_section(suppressed))
    lines.extend(_render_partial_section(failed))
    lines.extend(_render_failed_section(failed))
    lines.extend(_render_gaps_section(gaps))
    lines.extend(_render_astgrep_rule_block(derivation, hits))

    lines.append("How to proceed:")
    lines.append(
        "Review each hit above. Fixes land only in the repo this sweep was "
        "invoked from. Every other repo's hits stay report-only rows. Apply "
        "a fix only after the operator approves it. Rerun this sweep after "
        "making changes to confirm the fix landed."
    )

    return "\n".join(lines)
