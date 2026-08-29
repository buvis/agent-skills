"""Tests for sweep.py: scan."""
import os
import subprocess
import time
from pathlib import Path

import sweep
from sweep_test_helpers import _git_status_porcelain, _plant_matches


# -- scan ---------------------------------------------------------------


def test_scan_caps_hits_at_default_cap_and_records_suppressed_count_for_overflow(tmp_path):
    repo = _plant_matches(tmp_path / "repo", "SWEEPMARKER", 25)

    hits, suppressed, _failed = sweep.scan("SWEEPMARKER", "rg", [repo])

    repo_hits = [hit for hit in hits if hit["repo"] == str(repo)]
    assert len(repo_hits) == 20
    assert suppressed[str(repo)] == 5
    for hit in repo_hits:
        assert hit["file"]
        assert hit["line"] == 1
        assert "SWEEPMARKER" in hit["snippet"]


def test_scan_omits_suppressed_entry_for_repo_with_hits_under_cap(tmp_path):
    repo = _plant_matches(tmp_path / "repo", "UNDERMARKER", 3)

    hits, suppressed, _failed = sweep.scan("UNDERMARKER", "rg", [repo])

    repo_hits = [hit for hit in hits if hit["repo"] == str(repo)]
    assert len(repo_hits) == 3
    assert str(repo) not in suppressed
    for hit in repo_hits:
        assert hit["line"] == 1


def test_scan_applies_cap_independently_per_repo(tmp_path):
    repo_a = _plant_matches(tmp_path / "repo_a", "MULTIMARKER", 8)
    repo_b = _plant_matches(tmp_path / "repo_b", "MULTIMARKER", 3)

    hits, suppressed, _failed = sweep.scan("MULTIMARKER", "rg", [repo_a, repo_b], cap=5)

    hits_a = [hit for hit in hits if hit["repo"] == str(repo_a)]
    hits_b = [hit for hit in hits if hit["repo"] == str(repo_b)]
    assert len(hits_a) == 5
    assert len(hits_b) == 3
    assert suppressed[str(repo_a)] == 3
    assert str(repo_b) not in suppressed


def test_scan_hit_lang_field_derived_from_ast_grep_languages_extension_map(tmp_path):
    repo = tmp_path / "repo"
    repo.mkdir()
    (repo / "sample.py").write_text("LANGMARKER python line\n")
    (repo / "sample.txt").write_text("LANGMARKER text line\n")

    hits, _suppressed, _failed = sweep.scan("LANGMARKER", "rg", [repo])

    by_ext = {Path(hit["file"]).suffix: hit["lang"] for hit in hits}
    assert by_ext[".py"] == "python"
    assert by_ext[".txt"] is None


def test_scan_is_read_only_and_leaves_repo_contents_unchanged(tmp_path):
    repo = tmp_path / "repo"
    repo.mkdir()
    tracked = repo / "tracked.txt"
    tracked.write_text("READONLYMARKER content\n")
    subprocess.run(["git", "init", "-q"], cwd=str(repo), check=True, capture_output=True)
    subprocess.run(
        ["git", "-C", str(repo), "add", "tracked.txt"], check=True, capture_output=True
    )
    original_bytes = tracked.read_bytes()
    original_status = _git_status_porcelain(repo)

    sweep.scan("READONLYMARKER", "rg", [repo])

    assert tracked.read_bytes() == original_bytes
    new_status = _git_status_porcelain(repo)
    assert new_status == original_status


def test_scan_supports_astgrep_kind_and_returns_matching_hits(tmp_path):
    repo = tmp_path / "repo"
    repo.mkdir()
    (repo / "sample.py").write_text('print("hi")\n')

    hits, _suppressed, _failed = sweep.scan("print($X)", "astgrep", [repo])

    assert len(hits) >= 1
    hit = hits[0]
    assert hit["repo"] == str(repo)
    assert hit["file"].endswith("sample.py")
    assert hit["line"] == 1
    assert hit["lang"] == "python"
    assert "print" in hit["snippet"]


# -- scan: dash-prefixed patterns --------------------------------------------


def test_scan_finds_a_dash_prefixed_pattern_via_rg(tmp_path):
    # Today the pattern is handed to rg as a bare positional argument, so a
    # leading "-" is parsed as one of rg's own flags instead of being
    # searched for. This must fail against the current code.
    repo = _plant_matches(tmp_path / "repo", "-x", 1)

    hits, _suppressed, _failed = sweep.scan("-x", "rg", [repo])

    repo_hits = [hit for hit in hits if hit["repo"] == str(repo)]
    assert len(repo_hits) == 1
    assert "-x" in repo_hits[0]["snippet"]


# -- scan: one unscannable repo must not lose the others ---------------------


def test_scan_returns_good_repos_hits_when_one_repo_is_unscannable(tmp_path):
    repo_a = _plant_matches(tmp_path / "repo_a", "RESILIENCEMARKER", 1)
    bad_repo = tmp_path / "does-not-exist"
    repo_b = _plant_matches(tmp_path / "repo_b", "RESILIENCEMARKER", 1)

    hits, _suppressed, _failed = sweep.scan(
        "RESILIENCEMARKER", "rg", [repo_a, bad_repo, repo_b]
    )

    hit_repos = {hit["repo"] for hit in hits}
    assert hit_repos == {str(repo_a), str(repo_b)}


def test_scan_surfaces_an_unscannable_repo_instead_of_dropping_it_silently(
    tmp_path,
):
    # Shape assumed: scan() widens its return to a 3-tuple
    # (hits, suppressed, failed), so every existing
    # "hits, suppressed = sweep.scan(...)" call site in this file gains a
    # third, discarded element. `failed` maps str(repo) to a non-empty
    # reason string for repos that could not be scanned at all -- a
    # channel distinct from `suppressed` (which stays cap-overflow-only),
    # so a failed repo can never be misread as "scanned but truncated".
    repo_a = _plant_matches(tmp_path / "repo_a", "FAILSURFACEMARKER", 1)
    bad_repo = tmp_path / "does-not-exist"
    repo_b = _plant_matches(tmp_path / "repo_b", "FAILSURFACEMARKER", 1)

    _hits, suppressed, failed = sweep.scan(
        "FAILSURFACEMARKER", "rg", [repo_a, bad_repo, repo_b]
    )

    assert str(bad_repo) in failed
    assert failed[str(bad_repo)]  # carries a non-empty reason
    assert str(bad_repo) not in suppressed


def test_scan_records_repo_as_failed_when_search_tool_is_unresolvable(
    tmp_path, monkeypatch
):
    # resolve_ast_grep() raises RuntimeError when neither ast-grep nor mise
    # is on PATH. scan() must catch that and record the repo as failed
    # instead of letting the failure escape.
    monkeypatch.setenv("PATH", "/usr/bin:/bin")  # neither ast-grep nor mise here
    repo = tmp_path / "repo"
    repo.mkdir()
    (repo / "sample.py").write_text("print(1)\n")

    hits, _suppressed, failed = sweep.scan("print($X)", "astgrep", [repo])

    assert hits == []
    assert str(repo) in failed
    assert failed[str(repo)]  # carries a non-empty reason


# -- scan: every subprocess call carries a timeout ---------------------------


def test_scan_reports_a_hung_search_as_a_failed_repo_without_blocking(
    tmp_path, monkeypatch
):
    # Shape assumed for the failure channel, consistent with the tests
    # above: scan() returns a 3-tuple (hits, suppressed, failed), and a
    # repo whose search could not complete (here, timed out) is surfaced
    # as a key in `failed`, distinct from `suppressed` (cap-overflow-only).
    # Shape assumed for the time budget itself: scan() gains an optional
    # `timeout` keyword (seconds), mirroring the existing `cap` keyword, so
    # this test can use a small budget instead of waiting on whatever
    # production-sized default the fix picks.
    hung_rg = tmp_path / "rg"
    hung_rg.write_text("#!/bin/sh\nsleep 5\n")
    hung_rg.chmod(0o755)
    monkeypatch.setenv("PATH", f"{tmp_path}{os.pathsep}{os.environ['PATH']}")

    hung_repo = tmp_path / "hung_repo"
    hung_repo.mkdir()

    started = time.monotonic()
    hits, suppressed, failed = sweep.scan(
        "HANGMARKER", "rg", [hung_repo], timeout=0.2
    )
    elapsed = time.monotonic() - started

    assert elapsed < 3  # far short of the fake tool's 5s sleep
    assert hits == []
    assert str(hung_repo) in failed
    assert failed[str(hung_repo)]  # carries a non-empty reason
    assert str(hung_repo) not in suppressed


