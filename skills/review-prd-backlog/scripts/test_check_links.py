"""Tests for check_links.py (PRD 00081)."""
import json
import subprocess
import sys
from pathlib import Path

import pytest

import check_links


@pytest.fixture(autouse=True)
def _clear_resolve_path_cache():
    check_links.resolve_path.cache_clear()


def make_tree(root: Path) -> Path:
    dl = root / "docs/dev/project-management"
    (dl / "prds/backlog").mkdir(parents=True)
    (dl / "prds/hold").mkdir()
    (dl / "discovery").mkdir()
    (dl / "notes").mkdir()
    (dl / ".trash/2026-01-01").mkdir(parents=True)
    (dl / "prds/backlog/00001-alpha-v1.md").write_text("# alpha\n")
    (dl / "prds/hold/00007-parked-v1.md").write_text("# parked\n")
    (dl / "discovery/00002-beta.md").write_text("# beta\n")
    (dl / "notes/real.md").write_text("# real\n")
    return dl


def scan(root, text, name="doc.md"):
    doc = root / "docs/dev/project-management/notes" / name
    doc.write_text(text)
    findings, errors = check_links.run(root)
    return findings, errors


def test_resolving_references_are_clean(tmp_path):
    make_tree(tmp_path)
    findings, errors = scan(
        tmp_path,
        "see docs/dev/project-management/notes/real.md and PRD 00001-alpha-v1.md, "
        "hold-parked 00007-parked-v1 counts too, discovery 00002-beta.md\n",
    )
    assert findings == [] and errors == []


def test_dangling_path_and_prd_reported_with_line(tmp_path):
    make_tree(tmp_path)
    findings, _ = scan(tmp_path, "gone: docs/dev/project-management/notes/ghost.md\ncite 00099-nope-v1.md\n")
    targets = [f[2] for f in findings]
    assert "docs/dev/project-management/notes/ghost.md" in targets
    assert any(t.startswith("00099-") for t in targets)
    # findings quote the citing line and carry file:line
    f = findings[0]
    assert f[1] == 1 and "ghost" in f[3]


def test_link_ok_waiver_exempts_the_line(tmp_path):
    make_tree(tmp_path)
    findings, _ = scan(
        tmp_path,
        "link-ok: docs/dev/project-management/notes/removed.md was deleted on purpose\n"
        "but docs/dev/project-management/notes/also-gone.md has no waiver\n",
    )
    assert len(findings) == 1
    assert findings[0][2] == "docs/dev/project-management/notes/also-gone.md"


def test_memory_links_resolve_stem_and_frontmatter_name(tmp_path, monkeypatch):
    make_tree(tmp_path)
    mem = tmp_path / "memory"
    mem.mkdir()
    (mem / "file-stem.md").write_text("---\nname: slug-name\n---\nbody\n")
    monkeypatch.setattr(check_links, "project_memory_dir", lambda _root: mem)
    findings, _ = scan(tmp_path, "[[file-stem]] [[slug-name]] [[ghost-memory]]\n")
    assert [f[2] for f in findings] == ["[[ghost-memory]] (no memory)"]


def test_memory_dir_scanned_as_source(tmp_path, monkeypatch):
    make_tree(tmp_path)
    mem = tmp_path / "memory"
    mem.mkdir()
    (mem / "m.md").write_text("cites docs/dev/project-management/notes/vanished.md\n")
    monkeypatch.setattr(check_links, "project_memory_dir", lambda _root: mem)
    findings, _ = check_links.run(tmp_path)
    assert any("vanished" in f[2] for f in findings)


def test_placeholders_skipped(tmp_path):
    make_tree(tmp_path)
    findings, _ = scan(
        tmp_path,
        "patterns docs/dev/project-management/prds/*.md and docs/dev/tmp/NNNNN-x.md and docs/dev/project-management/... skip\n",
    )
    assert findings == []


def test_unreadable_file_is_a_scan_error(tmp_path, deny_access):
    make_tree(tmp_path)
    bad = tmp_path / "docs/dev/project-management/notes/locked.md"
    bad.write_text("secret\n")
    allow = deny_access(bad)
    try:
        findings, errors = check_links.run(tmp_path)
        assert len(errors) == 1 and "locked.md" in errors[0]
    finally:
        allow()


def test_cli_exit_codes_and_json(tmp_path):
    make_tree(tmp_path)
    script = Path(check_links.__file__)
    clean = subprocess.run(
        [sys.executable, str(script), "--root", str(tmp_path), "--json"],
        capture_output=True, text=True,
    )
    assert clean.returncode == 0
    assert json.loads(clean.stdout) == {"findings": [], "scan_errors": []}
    (tmp_path / "docs/dev/project-management/notes/doc.md").write_text("docs/dev/project-management/notes/ghost.md\n")
    dirty = subprocess.run(
        [sys.executable, str(script), "--root", str(tmp_path), "--json"],
        capture_output=True, text=True,
    )
    assert dirty.returncode == 1
    payload = json.loads(dirty.stdout)
    assert payload["findings"][0]["target"] == "docs/dev/project-management/notes/ghost.md"
    assert payload["findings"][0]["citing_line"] == "docs/dev/project-management/notes/ghost.md"


def test_resolve_path_reuses_cached_result_after_filesystem_change(tmp_path):
    ref = "docs/dev/project-management/notes/late.md"
    assert check_links.resolve_path(ref, tmp_path) is False
    (tmp_path / "docs/dev/project-management/notes").mkdir(parents=True)
    (tmp_path / "docs/dev/project-management/notes/late.md").write_text("x\n")
    # same (ref, root) pair: cached miss, not a fresh stat
    assert check_links.resolve_path(ref, tmp_path) is False


def test_resolve_path_cache_clear_forces_a_fresh_stat(tmp_path):
    ref = "docs/dev/project-management/notes/late.md"
    (tmp_path / "docs/dev/project-management/notes").mkdir(parents=True)
    assert check_links.resolve_path(ref, tmp_path) is False
    (tmp_path / "docs/dev/project-management/notes/late.md").write_text("x\n")
    check_links.resolve_path.cache_clear()
    assert check_links.resolve_path(ref, tmp_path) is True


def test_resolve_path_call_adds_one_cache_entry(tmp_path):
    check_links.resolve_path("docs/dev/project-management/notes/marker.md", tmp_path)
    assert check_links.resolve_path.cache_info().currsize == 1


def test_a_repeated_reference_is_statted_once(tmp_path, monkeypatch):
    make_tree(tmp_path)
    original_exists = Path.exists
    calls = []

    def wrapper(self, *args, **kwargs):
        calls.append(self)
        return original_exists(self, *args, **kwargs)

    monkeypatch.setattr(Path, "exists", wrapper)
    scan(tmp_path, "cite docs/dev/project-management/notes/real.md\n" * 50)

    real = tmp_path / "docs/dev/project-management/notes/real.md"
    assert calls.count(real) == 1


def empty_memory(tmp_path, monkeypatch, *names):
    mem = tmp_path / "memory"
    mem.mkdir()
    for name in names:
        (mem / f"{name}.md").write_text("body\n")
    monkeypatch.setattr(check_links, "project_memory_dir", lambda _root: mem)


def test_backtick_wrapped_bracket_is_not_a_memory_link(tmp_path, monkeypatch):
    make_tree(tmp_path)
    empty_memory(tmp_path, monkeypatch, "real-mem")
    findings, errors = scan(
        tmp_path,
        "write `[[fake]]` or `[[other-fake]]` for links\n"
        "see [[ghost-memory]] and [[real-mem]]\n"
        "half-wrapped `[[left-only]] and [[right-only]]` still count\n"
        "syntax `[[wrapped]]` sits beside bare [[mixed-ghost]] on one line\n",
    )
    assert errors == []
    assert sorted((f[1], f[2]) for f in findings) == [
        (2, "[[ghost-memory]] (no memory)"),
        (3, "[[left-only]] (no memory)"),
        (3, "[[right-only]] (no memory)"),
        (4, "[[mixed-ghost]] (no memory)"),
    ]


def test_prd_number_inside_uuid_is_not_a_citation(tmp_path):
    make_tree(tmp_path)
    findings, errors = scan(
        tmp_path,
        "codex_thread_id 01a17278-82e1-7811-975b-0c2d3e4f5a6b done\n"
        "dispatch f3b42051-aaaa-bbbb-cccc-dddddddddddd and run_12345-x\n"
        "cite 00099-nope-v1.md and `00098-gone-v1.md` and (00097-lost-v1.md)\n"
        "00096-start-v1.md opens the line, 00001-alpha-v1.md resolves\n"
        "bold **00095-a-v1.md** link [00094-b-v1.md] quote \"00093-c-v1.md\" PRD#00092-d-v1.md\n",
    )
    assert errors == []
    assert sorted((f[1], f[2]) for f in findings) == [
        (3, "00097- (no PRD/discovery file)"),
        (3, "00098- (no PRD/discovery file)"),
        (3, "00099- (no PRD/discovery file)"),
        (4, "00096- (no PRD/discovery file)"),
        (5, "00092- (no PRD/discovery file)"),
        (5, "00093- (no PRD/discovery file)"),
        (5, "00094- (no PRD/discovery file)"),
        (5, "00095- (no PRD/discovery file)"),
    ]


def test_self_quoted_no_prd_diagnostic_is_not_a_fresh_citation(tmp_path):
    make_tree(tmp_path)
    findings, errors = scan(
        tmp_path,
        "last run said 00057- (no PRD/discovery file) for that doc\n"
        "it also said 00058- (no PRD file) and 00095-gone-v1.md here\n"
        "unrelated: cite 00099-nope-v1.md\n"
        "quoted 00057- (no PRD/discovery file) beside fresh 00094-new-v1.md\n"
        "fresh 00093-gone-v1.md was flagged (no PRD/discovery file) later\n",
    )
    assert errors == []
    assert sorted((f[1], f[2]) for f in findings) == [
        (2, "00058- (no PRD/discovery file)"),
        (2, "00095- (no PRD/discovery file)"),
        (3, "00099- (no PRD/discovery file)"),
        (4, "00094- (no PRD/discovery file)"),
        (5, "00093- (no PRD/discovery file)"),
    ]


def test_observed_evidence_fence_is_opaque(tmp_path, monkeypatch):
    make_tree(tmp_path)
    empty_memory(tmp_path, monkeypatch)
    findings, errors = scan(
        tmp_path,
        "Carry the observed evidence verbatim from the accepted packet:\n"
        "\n"
        "```text\n"
        "[[package]] name = \"x\"\n"
        "id 99999-zz\n"
        "docs/dev/project-management/notes/fenced-ghost.md\n"
        "```\n"
        "prose: [[package]] 99999-zz docs/dev/project-management/notes/fenced-ghost.md\n"
        "```text\n"
        "[[plain-ghost]]\n"
        "```\n",
    )
    assert errors == []
    assert sorted((f[1], f[2]) for f in findings) == [
        (8, "99999- (no PRD/discovery file)"),
        (8, "[[package]] (no memory)"),
        (8, "docs/dev/project-management/notes/fenced-ghost.md"),
        (10, "[[plain-ghost]] (no memory)"),
    ]


def test_evidence_fence_without_a_following_fence_is_not_armed(tmp_path, monkeypatch):
    make_tree(tmp_path)
    empty_memory(tmp_path, monkeypatch)
    findings, errors = scan(
        tmp_path,
        "Carry the observed evidence verbatim from the accepted packet:\n"
        "[[package]]\n"
        "docs/dev/project-management/notes/ghost.md\n"
        "\n"
        "Carry the observed evidence verbatim from the accepted packet:\n"
        "```text\n"
        "[[suppressed-package]]\n"
        "```\n",
    )
    assert errors == []
    # the un-fenced heading's content is still scanned normally (preserved),
    # and a separate, genuinely-closed evidence fence later in the same
    # document still suppresses - the exact-equality check below already
    # pins both: only these two findings exist, so [[suppressed-package]]
    # cannot be among them.
    assert sorted((f[1], f[2]) for f in findings) == [
        (2, "[[package]] (no memory)"),
        (3, "docs/dev/project-management/notes/ghost.md"),
    ]


def test_marker_quoted_in_closed_ordinary_fence_does_not_arm_a_later_heading(tmp_path, monkeypatch):
    """Pins the fix: the pre-fix code armed from the trigger substring found
    inside a closed ordinary fence, then misread that fence's own closing
    delimiter as an evidence-fence open, swallowing the genuine heading and
    findings that followed. A test with no ordinary fence ahead of the
    heading (like the sibling test above) cannot distinguish old from new
    behavior; this one can and does."""
    make_tree(tmp_path)
    empty_memory(tmp_path, monkeypatch)
    findings, errors = scan(
        tmp_path,
        "Example output:\n"
        "```python\n"
        'if "Carry the observed evidence verbatim" in stripped:\n'
        "```\n"
        "Carry the observed evidence verbatim from the accepted packet:\n"
        "[[package]]\n"
        "docs/dev/project-management/notes/ghost.md\n",
    )
    assert errors == []
    assert sorted((f[1], f[2]) for f in findings) == [
        (6, "[[package]] (no memory)"),
        (7, "docs/dev/project-management/notes/ghost.md"),
    ]


def test_unclosed_evidence_fence_falls_back_to_normal_scanning(tmp_path):
    make_tree(tmp_path)
    findings, errors = scan(
        tmp_path,
        "preamble\n"
        "Carry the observed evidence verbatim from the accepted packet:\n"
        "```text\n"
        "docs/dev/project-management/notes/ghost.md\n",
    )
    assert [(f[1], f[2]) for f in findings] == [(4, "docs/dev/project-management/notes/ghost.md")]
    assert len(errors) == 1
    assert "evidence fence opened at line 3 never closed" in errors[0]


def test_unclosed_evidence_fence_error_names_the_fence_line_not_the_heading(tmp_path):
    make_tree(tmp_path)
    findings, errors = scan(
        tmp_path,
        "preamble\n"
        "Carry the observed evidence verbatim from the accepted packet:\n"
        "\n"
        "```text\n"
        "docs/dev/project-management/notes/ghost.md\n",
    )
    assert [(f[1], f[2]) for f in findings] == [(5, "docs/dev/project-management/notes/ghost.md")]
    assert len(errors) == 1
    assert "evidence fence opened at line 4 never closed" in errors[0]
    assert "line 3" not in errors[0]


def test_only_the_evidence_heading_arms_the_fence(tmp_path):
    make_tree(tmp_path)
    findings, errors = scan(
        tmp_path,
        "Example output:\n"
        "```text\n"
        "docs/dev/project-management/notes/colon-ghost.md\n"
        "```\n"
        "Carry the observed evidence verbatim from the accepted packet.\n"
        "```text\n"
        "docs/dev/project-management/notes/quiet-ghost.md\n"
        "```\n",
    )
    assert errors == []
    assert [(f[1], f[2]) for f in findings] == [(3, "docs/dev/project-management/notes/colon-ghost.md")]


def test_marker_quoted_inside_code_fence_does_not_arm(tmp_path):
    make_tree(tmp_path)
    findings, errors = scan(
        tmp_path,
        "```python\n"
        'if "Carry the observed evidence verbatim" in stripped:\n'
        "    pass\n"
        "```\n"
        "docs/dev/project-management/notes/after-ghost.md\n",
    )
    assert errors == []
    assert [(f[1], f[2]) for f in findings] == [
        (5, "docs/dev/project-management/notes/after-ghost.md"),
    ]


def test_repeated_marker_inside_evidence_fence_does_not_leak_armed_state(tmp_path, monkeypatch):
    make_tree(tmp_path)
    empty_memory(tmp_path, monkeypatch)
    findings, errors = scan(
        tmp_path,
        "Carry the observed evidence verbatim from the accepted packet:\n"
        "```text\n"
        "Carry the observed evidence verbatim from the accepted packet:\n"
        "[[hidden-in-fence]]\n"
        "```\n"
        "```text\n"
        "[[plain-ghost]]\n"
        "```\n",
    )
    assert errors == []
    assert [(f[1], f[2]) for f in findings] == [
        (7, "[[plain-ghost]] (no memory)"),
    ]


def test_evidence_fence_opacity_starts_at_the_fence_not_the_heading(tmp_path):
    make_tree(tmp_path)
    findings, errors = scan(
        tmp_path,
        "Carry the observed evidence verbatim from 00091-heading-v1.md:\n"
        "prose between cites docs/dev/project-management/notes/between-ghost.md\n"
        "```text\n"
        "docs/dev/project-management/notes/fenced-ghost.md\n"
        "```\n",
    )
    assert errors == []
    assert sorted((f[1], f[2]) for f in findings) == [
        (1, "00091- (no PRD/discovery file)"),
        (2, "docs/dev/project-management/notes/between-ghost.md"),
    ]


def test_nested_language_tagged_fence_does_not_close_outer_evidence_fence(tmp_path, monkeypatch):
    make_tree(tmp_path)
    empty_memory(tmp_path, monkeypatch)
    findings, errors = scan(
        tmp_path,
        "Carry the observed evidence verbatim from the accepted packet:\n"
        "```text\n"
        "```python\n"
        "[[nested-ghost]]\n"
        "```\n"
        "docs/dev/project-management/notes/nested-ghost.md\n"
        "```\n",
    )
    assert errors == []
    assert findings == []


def test_four_backtick_evidence_fence_not_closed_by_inner_three_backtick_fence(tmp_path, monkeypatch):
    make_tree(tmp_path)
    empty_memory(tmp_path, monkeypatch)
    findings, errors = scan(
        tmp_path,
        "Carry the observed evidence verbatim from the accepted packet:\n"
        "````text\n"
        "```python\n"
        "[[inner-ghost]]\n"
        "```\n"
        "docs/dev/project-management/notes/four-tick-ghost.md\n"
        "````\n",
    )
    assert errors == []
    assert findings == []
