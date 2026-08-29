"""Tests for sweep.py (resolve_rg, resolve_ast_grep)."""
import ast
import os
from pathlib import Path
import re
import shutil
import subprocess
import sys
import time

import pytest
import yaml  # test-only round-trip parser; sweep.py itself must stay stdlib-only

import sweep


@pytest.fixture(autouse=True)
def _clear_resolver_caches():
    sweep.resolve_rg.cache_clear()
    sweep.resolve_ast_grep.cache_clear()
    yield
    sweep.resolve_rg.cache_clear()
    sweep.resolve_ast_grep.cache_clear()


# -- resolve_rg -----------------------------------------------------------


def test_bare_rg_invocation_fails_in_this_environment():
    # Documents the premise the resolver exists to work around: "rg" is a
    # shell function here, not a PATH binary, so a naive bare-name
    # subprocess call is not viable.
    with pytest.raises(FileNotFoundError):
        subprocess.run(["rg", "--version"], capture_output=True)


def test_resolve_rg_finds_a_real_rg_binary_on_path(tmp_path, monkeypatch):
    fake_rg = tmp_path / "rg"
    fake_rg.write_text("#!/bin/sh\necho fake-rg\n")
    fake_rg.chmod(0o755)
    monkeypatch.setenv("PATH", f"{tmp_path}{os.pathsep}{os.environ['PATH']}")

    result = sweep.resolve_rg()

    assert result == str(fake_rg)


def test_resolve_rg_result_is_cached_across_calls(tmp_path, monkeypatch):
    original_path = os.environ["PATH"]
    fake_rg = tmp_path / "rg"
    fake_rg.write_text("#!/bin/sh\necho fake-rg\n")
    fake_rg.chmod(0o755)
    monkeypatch.setenv("PATH", f"{tmp_path}{os.pathsep}{original_path}")

    first = sweep.resolve_rg()
    assert first == str(fake_rg)

    # Restore PATH so the fake binary is no longer reachable; an uncached
    # call would now resolve differently (fallback path or SystemExit).
    monkeypatch.setenv("PATH", original_path)
    second = sweep.resolve_rg()

    assert second == first


def test_resolve_rg_returns_a_working_path_when_absent_from_path():
    # In this real environment shutil.which("rg") is None (rg is a shell
    # function), so this exercises the actual claude-binary fallback.
    path = sweep.resolve_rg()

    assert isinstance(path, str)

    result = subprocess.run(
        ["rg", "--version"], executable=path, capture_output=True, text=True
    )

    assert result.returncode == 0
    assert "ripgrep" in result.stdout.lower()


def test_resolve_rg_exits_naming_both_candidates_when_neither_resolves(
    tmp_path, monkeypatch
):
    monkeypatch.setenv("PATH", "/usr/bin:/bin")  # no rg here
    monkeypatch.delenv("CLAUDE_CODE_EXECPATH", raising=False)
    monkeypatch.setenv("HOME", str(tmp_path))  # no ~/.local/bin/claude here

    with pytest.raises(RuntimeError) as exc_info:
        sweep.resolve_rg()

    combined = str(exc_info.value).lower()
    assert "rg" in combined
    assert "claude" in combined


# -- resolve_ast_grep -------------------------------------------------------


def test_resolve_ast_grep_matches_mise_which_output():
    expected = subprocess.run(
        ["mise", "which", "ast-grep"], capture_output=True, text=True, check=True
    ).stdout.strip()

    assert sweep.resolve_ast_grep() == expected


def test_resolve_ast_grep_falls_back_to_mise_when_absent_from_path(monkeypatch):
    mise_path = shutil.which("mise")
    assert mise_path is not None, "mise must be on PATH for this test to be meaningful"
    mise_dir = os.path.dirname(mise_path)
    expected = subprocess.run(
        ["mise", "which", "ast-grep"], capture_output=True, text=True, check=True
    ).stdout.strip()

    monkeypatch.setenv("PATH", f"{mise_dir}{os.pathsep}/usr/bin{os.pathsep}/bin")

    result = sweep.resolve_ast_grep()

    assert result == expected


def test_resolve_ast_grep_result_is_cached_across_calls(monkeypatch):
    mise_path = shutil.which("mise")
    assert mise_path is not None, "mise must be on PATH for this test to be meaningful"
    mise_dir = os.path.dirname(mise_path)

    monkeypatch.setenv("PATH", f"{mise_dir}{os.pathsep}/usr/bin{os.pathsep}/bin")
    first = sweep.resolve_ast_grep()

    # A PATH with neither ast-grep nor mise reachable; an uncached call
    # would now raise SystemExit instead of matching `first`.
    monkeypatch.setenv("PATH", "/usr/bin:/bin")
    second = sweep.resolve_ast_grep()

    assert second == first


def test_resolve_ast_grep_exits_naming_both_attempts_when_neither_resolves(
    monkeypatch,
):
    monkeypatch.setenv("PATH", "/usr/bin:/bin")  # neither ast-grep nor mise here

    with pytest.raises(RuntimeError) as exc_info:
        sweep.resolve_ast_grep()

    combined = str(exc_info.value).lower()
    assert "ast-grep" in combined
    assert "mise" in combined


# -- enumerate_repos --------------------------------------------------------


def _make_repo(root):
    """Create a directory with a `.git` marker so it passes the repo check."""
    (root / ".git").mkdir(parents=True)
    return root


def _write_registry(path, rows):
    lines = "\n".join(rows)
    path.write_text(lines + "\n" if lines else "")


def _init_git_repo_with_tracked_files(root, tracked, untracked=()):
    root.mkdir(parents=True, exist_ok=True)
    subprocess.run(["git", "init", "-q"], cwd=str(root), check=True, capture_output=True)
    for rel in tracked:
        file_path = root / rel
        file_path.parent.mkdir(parents=True, exist_ok=True)
        file_path.write_text("content\n")
    subprocess.run(
        ["git", "-C", str(root), "add", *tracked], check=True, capture_output=True
    )
    for rel in untracked:
        file_path = root / rel
        file_path.parent.mkdir(parents=True, exist_ok=True)
        file_path.write_text("untracked\n")
    return root


def test_enumerate_repos_includes_registered_repos_with_git_dir(tmp_path, monkeypatch):
    empty_portfolio_root = tmp_path / "empty_portfolio_root"
    empty_portfolio_root.mkdir()
    monkeypatch.setattr(sweep, "PORTFOLIO_ROOT", empty_portfolio_root)

    registered = _make_repo(tmp_path / "org" / "repo-a")
    registry = tmp_path / "repos.csv"
    _write_registry(registry, [str(registered)])
    cwd = tmp_path / "cwd_dir"
    cwd.mkdir()

    repos, _gaps = sweep.enumerate_repos(registry, cwd)

    assert registered in repos


def test_enumerate_repos_excludes_registered_paths_without_git_dir(tmp_path, monkeypatch):
    empty_portfolio_root = tmp_path / "empty_portfolio_root"
    empty_portfolio_root.mkdir()
    monkeypatch.setattr(sweep, "PORTFOLIO_ROOT", empty_portfolio_root)

    stale = tmp_path / "org" / "removed-repo"
    stale.mkdir(parents=True)  # exists on disk but has no .git
    registry = tmp_path / "repos.csv"
    _write_registry(registry, [str(stale)])
    cwd = tmp_path / "cwd_dir"
    cwd.mkdir()

    repos, _gaps = sweep.enumerate_repos(registry, cwd)

    assert stale not in repos


def test_enumerate_repos_skips_blank_csv_rows(tmp_path, monkeypatch):
    empty_portfolio_root = tmp_path / "empty_portfolio_root"
    empty_portfolio_root.mkdir()
    monkeypatch.setattr(sweep, "PORTFOLIO_ROOT", empty_portfolio_root)

    repo_a = _make_repo(tmp_path / "org" / "repo-a")
    repo_b = _make_repo(tmp_path / "org" / "repo-b")
    registry = tmp_path / "repos.csv"
    _write_registry(registry, [str(repo_a), "", str(repo_b)])
    cwd = tmp_path / "cwd_dir"
    cwd.mkdir()

    repos, _gaps = sweep.enumerate_repos(registry, cwd)

    assert repo_a in repos
    assert repo_b in repos
    assert Path("") not in repos


def test_enumerate_repos_appends_cwd_when_absent_from_registry(tmp_path, monkeypatch):
    empty_portfolio_root = tmp_path / "empty_portfolio_root"
    empty_portfolio_root.mkdir()
    monkeypatch.setattr(sweep, "PORTFOLIO_ROOT", empty_portfolio_root)

    registry = tmp_path / "repos.csv"
    _write_registry(registry, [])
    cwd = tmp_path / "unregistered-cwd"
    cwd.mkdir()  # not a git repo, and not listed in the registry

    repos, _gaps = sweep.enumerate_repos(registry, cwd)

    assert cwd in repos


def test_enumerate_repos_does_not_duplicate_cwd_already_registered(tmp_path, monkeypatch):
    empty_portfolio_root = tmp_path / "empty_portfolio_root"
    empty_portfolio_root.mkdir()
    monkeypatch.setattr(sweep, "PORTFOLIO_ROOT", empty_portfolio_root)

    cwd = _make_repo(tmp_path / "org" / "current-repo")
    registry = tmp_path / "repos.csv"
    _write_registry(registry, [str(cwd)])

    repos, _gaps = sweep.enumerate_repos(registry, cwd)

    assert repos.count(cwd) == 1


def test_enumerate_repos_never_writes_to_registry_path(tmp_path, monkeypatch):
    empty_portfolio_root = tmp_path / "empty_portfolio_root"
    empty_portfolio_root.mkdir()
    monkeypatch.setattr(sweep, "PORTFOLIO_ROOT", empty_portfolio_root)

    registered = _make_repo(tmp_path / "org" / "repo-a")
    registry = tmp_path / "repos.csv"
    _write_registry(registry, [str(registered)])
    original_bytes = registry.read_bytes()
    cwd = tmp_path / "unregistered-cwd"
    cwd.mkdir()

    sweep.enumerate_repos(registry, cwd)

    assert registry.read_bytes() == original_bytes


def test_enumerate_repos_reports_ondisk_repo_missing_from_registry_as_gap(
    tmp_path, monkeypatch
):
    portfolio_root = tmp_path / "portfolio"
    monkeypatch.setattr(sweep, "PORTFOLIO_ROOT", portfolio_root)

    registered = _make_repo(portfolio_root / "org" / "registered-repo")
    unregistered = _make_repo(portfolio_root / "org" / "unregistered-repo")
    registry = tmp_path / "repos.csv"
    _write_registry(registry, [str(registered)])
    cwd = tmp_path / "cwd_dir"
    cwd.mkdir()

    _repos, gaps = sweep.enumerate_repos(registry, cwd)

    assert gaps == [str(unregistered)]


def test_enumerate_repos_excludes_ondisk_dir_without_git_from_gaps(tmp_path, monkeypatch):
    portfolio_root = tmp_path / "portfolio"
    monkeypatch.setattr(sweep, "PORTFOLIO_ROOT", portfolio_root)

    not_a_repo = portfolio_root / "org" / "not-a-repo"
    not_a_repo.mkdir(parents=True)
    registry = tmp_path / "repos.csv"
    _write_registry(registry, [])
    cwd = tmp_path / "cwd_dir"
    cwd.mkdir()

    _repos, gaps = sweep.enumerate_repos(registry, cwd)

    assert gaps == []


def test_enumerate_repos_excludes_repos_deeper_than_two_levels_from_gaps(
    tmp_path, monkeypatch
):
    portfolio_root = tmp_path / "portfolio"
    monkeypatch.setattr(sweep, "PORTFOLIO_ROOT", portfolio_root)

    _make_repo(portfolio_root / "org" / "sub" / "deep-repo")
    registry = tmp_path / "repos.csv"
    _write_registry(registry, [])
    cwd = tmp_path / "cwd_dir"
    cwd.mkdir()

    _repos, gaps = sweep.enumerate_repos(registry, cwd)

    assert gaps == []


def _setup_buvis_bare_fixture(tmp_path, monkeypatch, tracked, untracked=()):
    """Build a fixture ~/.buvis-style bare repo: a real git repo with the
    given tracked/untracked files, wired up as sweep.BUVIS_BARE, plus an
    empty registry and an empty PORTFOLIO_ROOT so gap detection stays out
    of scope. Returns (fixture_home, registry)."""
    empty_portfolio_root = tmp_path / "empty_portfolio_root"
    empty_portfolio_root.mkdir()
    monkeypatch.setattr(sweep, "PORTFOLIO_ROOT", empty_portfolio_root)

    fixture_home = tmp_path / "fixture_home"
    _init_git_repo_with_tracked_files(fixture_home, tracked, untracked=untracked)
    monkeypatch.setattr(
        sweep,
        "BUVIS_BARE",
        {"git_dir": fixture_home / ".git", "work_tree": fixture_home},
    )
    registry = tmp_path / "repos.csv"
    _write_registry(registry, [])

    return fixture_home, registry


def test_enumerate_repos_bare_output_lets_scan_find_every_tracked_file(
    tmp_path, monkeypatch
):
    fixture_home, registry = _setup_buvis_bare_fixture(
        tmp_path, monkeypatch, ["a.txt", "sub/b.txt"]
    )
    (fixture_home / "a.txt").write_text("BAREBALLOTMARKER content\n")
    (fixture_home / "sub" / "b.txt").write_text("BAREBALLOTMARKER content\n")

    repos, _gaps = sweep.enumerate_repos(registry, fixture_home)
    assert repos  # the bare repo's tracked files must not come back empty

    hits, _suppressed, _failed = sweep.scan("BAREBALLOTMARKER", "rg", repos)

    matched_files = {Path(hit["file"]).name for hit in hits}
    assert matched_files == {"a.txt", "b.txt"}


def test_scan_excludes_untracked_file_from_buvis_bare_search_scope(
    tmp_path, monkeypatch
):
    fixture_home, registry = _setup_buvis_bare_fixture(
        tmp_path,
        monkeypatch,
        ["tracked.txt"],
        untracked=["scratch.tmp"],
    )
    (fixture_home / "tracked.txt").write_text("UNTRACKEDGUARDMARKER content\n")
    (fixture_home / "scratch.tmp").write_text("UNTRACKEDGUARDMARKER content\n")

    repos, _gaps = sweep.enumerate_repos(registry, fixture_home)
    hits, _suppressed, _failed = sweep.scan("UNTRACKEDGUARDMARKER", "rg", repos)

    matched_files = {Path(hit["file"]).name for hit in hits}
    assert "tracked.txt" in matched_files
    assert "scratch.tmp" not in matched_files


def test_enumerate_repos_scopes_registered_work_tree_row_to_tracked_files_only(
    tmp_path, monkeypatch
):
    fixture_home, registry = _setup_buvis_bare_fixture(
        tmp_path,
        monkeypatch,
        ["tracked.txt"],
        untracked=["secret.env"],
    )
    (fixture_home / "tracked.txt").write_text("REGISTEREDWORKTREEMARKER content\n")
    (fixture_home / "secret.env").write_text("REGISTEREDWORKTREEMARKER content\n")
    _write_registry(registry, [str(fixture_home)])
    cwd = tmp_path / "cwd_dir"
    cwd.mkdir()  # process cwd is elsewhere, not the registered work tree

    repos, _gaps = sweep.enumerate_repos(registry, cwd)

    bare_entries = [
        repo for repo in repos if isinstance(repo, dict) and repo["cwd"] == fixture_home
    ]
    assert len(bare_entries) == 1  # never lands twice, and never as a raw Path
    assert fixture_home not in [repo for repo in repos if not isinstance(repo, dict)]

    hits, _suppressed, _failed = sweep.scan("REGISTEREDWORKTREEMARKER", "rg", repos)

    matched_files = {Path(hit["file"]).name for hit in hits}
    assert "tracked.txt" in matched_files
    assert "secret.env" not in matched_files


def test_enumerate_repos_includes_both_bare_entry_and_unrelated_cwd_when_work_tree_registered(
    tmp_path, monkeypatch
):
    fixture_home, registry = _setup_buvis_bare_fixture(
        tmp_path, monkeypatch, ["tracked.txt"]
    )
    _write_registry(registry, [str(fixture_home)])
    cwd = tmp_path / "unrelated-cwd"
    cwd.mkdir()  # not the work tree, and not itself registered

    repos, _gaps = sweep.enumerate_repos(registry, cwd)

    bare_entries = [
        repo for repo in repos if isinstance(repo, dict) and repo["cwd"] == fixture_home
    ]
    assert len(bare_entries) == 1
    assert cwd in repos


def test_enumerate_repos_finds_buvis_bare_tracked_files_regardless_of_process_cwd(
    tmp_path, monkeypatch
):
    fixture_home, registry = _setup_buvis_bare_fixture(
        tmp_path, monkeypatch, ["top.txt", "sub/nested.txt"]
    )
    (fixture_home / "top.txt").write_text("CWDINDEPENDENTMARKER content\n")
    (fixture_home / "sub" / "nested.txt").write_text("CWDINDEPENDENTMARKER content\n")

    monkeypatch.chdir(fixture_home / "sub")  # process cwd is a subdirectory of the work tree

    repos, _gaps = sweep.enumerate_repos(registry, fixture_home)
    assert repos  # must not silently come back empty when cwd is inside the work tree

    hits, _suppressed, _failed = sweep.scan("CWDINDEPENDENTMARKER", "rg", repos)

    matched_files = {Path(hit["file"]).name for hit in hits}
    assert "top.txt" in matched_files  # root-level file, hidden by cwd's prefix under the bug


def test_scan_caps_buvis_bare_repo_as_a_single_repo_not_per_tracked_file(
    tmp_path, monkeypatch
):
    tracked = [f"file_{i}.txt" for i in range(5)]
    fixture_home, registry = _setup_buvis_bare_fixture(tmp_path, monkeypatch, tracked)
    for rel in tracked:
        (fixture_home / rel).write_text("BARECAPMARKER line\n")

    repos, _gaps = sweep.enumerate_repos(registry, fixture_home)
    hits, suppressed, _failed = sweep.scan("BARECAPMARKER", "rg", repos, cap=3)

    assert len(hits) == 3
    assert len(suppressed) == 1
    assert sum(suppressed.values()) == 2
    assert len({hit["repo"] for hit in hits}) == 1


def test_scan_bare_entry_with_no_tracked_files_finds_no_hits_and_does_not_walk_cwd(
    tmp_path, monkeypatch
):
    fixture_home, registry = _setup_buvis_bare_fixture(
        tmp_path, monkeypatch, [], untracked=["scratch.tmp"]
    )
    (fixture_home / "scratch.tmp").write_text("EMPTYINDEXMARKER content\n")

    repos, _gaps = sweep.enumerate_repos(registry, fixture_home)
    hits, _suppressed, _failed = sweep.scan("EMPTYINDEXMARKER", "rg", repos)

    assert hits == []


# -- scan ---------------------------------------------------------------


def _plant_matches(repo, pattern, count, ext=".txt"):
    """Create `repo` with `count` files, each containing one line matching `pattern`."""
    repo.mkdir(parents=True, exist_ok=True)
    for i in range(count):
        (repo / f"match_{i:03d}{ext}").write_text(f"{pattern} line {i}\n")
    return repo


def _git_status_porcelain(repo):
    return subprocess.run(
        ["git", "-C", str(repo), "status", "--porcelain"],
        capture_output=True,
        text=True,
        check=True,
    ).stdout


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


# -- verify_control -------------------------------------------------------


def test_verify_control_returns_none_when_pattern_finds_hits_in_control_repo(tmp_path):
    control_repo = tmp_path / "control"
    control_repo.mkdir()
    (control_repo / "file.txt").write_text("CONTROLMARKER line\n")

    result = sweep.verify_control(
        "CONTROLMARKER", "rg", control_repo, "irrelevant-term"
    )

    assert result is None


def test_verify_control_returns_none_when_pattern_and_control_term_both_absent(
    tmp_path,
):
    control_repo = tmp_path / "control"
    control_repo.mkdir()
    (control_repo / "file.txt").write_text("unrelated content\n")

    result = sweep.verify_control(
        "NOTPRESENTPATTERN", "rg", control_repo, "NOTPRESENTTERM"
    )

    assert result is None


def test_verify_control_raises_unverified_when_pattern_misses_but_control_term_present(
    tmp_path, capsys
):
    control_repo = tmp_path / "control"
    control_repo.mkdir()
    (control_repo / "file.txt").write_text("CONTROLTERM appears here\n")

    with pytest.raises(SystemExit) as exc_info:
        sweep.verify_control("NOTPRESENTPATTERN", "rg", control_repo, "CONTROLTERM")

    assert exc_info.value.code == 1
    message = capsys.readouterr().err
    assert "unverified" in message
    assert "CONTROLTERM" in message
    assert str(control_repo) in message


def test_verify_control_raises_unverified_for_broken_backslash_pipe_alternation(
    tmp_path, capsys
):
    # The classic Rust-regex trap: `\|` is a literal pipe, not "OR", so this
    # pattern never matches "foo" alone even though the author meant
    # "foo OR bar".
    control_repo = tmp_path / "control"
    control_repo.mkdir()
    (control_repo / "file.txt").write_text("foo appears alone, no pipe here\n")

    with pytest.raises(SystemExit) as exc_info:
        sweep.verify_control("foo\\|bar", "rg", control_repo, "foo")

    assert exc_info.value.code == 1
    message = capsys.readouterr().err
    assert "unverified" in message
    assert "foo" in message
    assert str(control_repo) in message


def test_verify_control_warns_to_stderr_when_fallback_check_cannot_run(
    tmp_path, capsys
):
    # control_repo does not exist, so the `_run_rg` fallback call itself
    # cannot run. That must not be silently reported as "verified, no
    # issue" -- it must warn, naming the failure and the control repo.
    control_repo = tmp_path / "does-not-exist"

    result = sweep.verify_control(
        "NOTPRESENTPATTERN", "rg", control_repo, "NOTPRESENTTERM"
    )

    assert result is None
    message = capsys.readouterr().err
    assert str(control_repo) in message


# -- render_report -----------------------------------------------------


def _extract_rule_pack_blocks(report):
    """Pull fenced code blocks that look like an ast-grep rule-pack (contain
    both a `rule:` and a `pattern:` YAML key) out of a rendered report."""
    fenced = re.findall(r"```[^\n]*\n(.*?)```", report, re.DOTALL)
    return [block for block in fenced if "rule:" in block and "pattern:" in block]


def test_render_report_gaps_header_states_zero_count_for_empty_gaps():
    derivation = {"kind": "rg", "pattern": "X", "reason": "y", "control_term": "z"}

    report = sweep.render_report(derivation, [], [], {}, {})

    assert "Gaps (0):" in report


def test_render_report_gaps_header_states_actual_count_for_nonempty_gaps():
    derivation = {"kind": "rg", "pattern": "X", "reason": "y", "control_term": "z"}
    gaps = [
        "/portfolio/org/gap-one",
        "/portfolio/org/gap-two",
        "/portfolio/org/gap-three",
    ]

    report = sweep.render_report(derivation, [], gaps, {}, {})

    assert "Gaps (3):" in report
    for gap in gaps:
        assert gap in report


def test_render_report_includes_repo_file_and_line_for_every_hit():
    derivation = {"kind": "rg", "pattern": "X", "reason": "y", "control_term": "z"}
    hits = [
        {
            "repo": "/repo/alpha",
            "file": "src/mod.py",
            "line": 10,
            "snippet": "x = 1",
            "lang": "python",
        },
        {
            "repo": "/repo/beta",
            "file": "lib/util.rs",
            "line": 22,
            "snippet": "y = 2",
            "lang": "rust",
        },
    ]

    report = sweep.render_report(derivation, hits, [], {}, {})

    for hit in hits:
        assert hit["repo"] in report
        assert hit["file"] in report
        assert str(hit["line"]) in report


def test_render_report_states_uncovered_languages_when_a_hit_has_no_lang():
    derivation = {"kind": "astgrep", "pattern": "X", "reason": "y", "control_term": "z"}
    hits = [
        {
            "repo": "/repo/alpha",
            "file": "notes.md",
            "line": 3,
            "snippet": "X here",
            "lang": None,
        },
        {
            "repo": "/repo/alpha",
            "file": "src/mod.py",
            "line": 10,
            "snippet": "x = 1",
            "lang": "python",
        },
    ]

    report = sweep.render_report(derivation, hits, [], {}, {})

    assert "uncovered" in report.lower()
    assert ".md" in report


def test_render_report_omits_uncovered_languages_line_when_every_hit_has_a_lang():
    derivation = {"kind": "astgrep", "pattern": "X", "reason": "y", "control_term": "z"}
    hits = [
        {
            "repo": "/repo/alpha",
            "file": "src/mod.py",
            "line": 10,
            "snippet": "x = 1",
            "lang": "python",
        },
        {
            "repo": "/repo/beta",
            "file": "lib/util.rs",
            "line": 22,
            "snippet": "y = 2",
            "lang": "rust",
        },
    ]

    report = sweep.render_report(derivation, hits, [], {}, {})

    assert "uncovered" not in report.lower()


def test_render_report_omits_uncovered_languages_line_for_rg_kind_sweep_with_unmapped_lang_hit():
    # rg is a plain textual search: no ast-grep rule is ever derived or
    # attempted, so a hit in a file with no ast-grep language (lang=None)
    # is not "uncovered" by anything. The uncovered-languages line exists
    # to warn that an astgrep sweep was quietly partial; it must not fire
    # for a mode that never had ast-grep coverage to begin with.
    derivation = {"kind": "rg", "pattern": "X", "reason": "y", "control_term": "z"}
    hits = [
        {
            "repo": "/repo/alpha",
            "file": "notes.md",
            "line": 3,
            "snippet": "X here",
            "lang": None,
        },
    ]

    report = sweep.render_report(derivation, hits, [], {}, {})

    assert "uncovered" not in report.lower()


def test_render_report_shows_suppressed_count_for_every_repo_present():
    derivation = {"kind": "rg", "pattern": "X", "reason": "y", "control_term": "z"}
    suppressed = {"/repo/alpha": 37, "/repo/beta": 141}

    report = sweep.render_report(derivation, [], [], suppressed, {})

    for repo, count in suppressed.items():
        assert repo in report
        assert str(count) in report


def test_render_report_never_raises_for_all_empty_input():
    derivation = {
        "kind": "rg",
        "pattern": "EMPTYCASE",
        "reason": "no matches",
        "control_term": "z",
    }

    report = sweep.render_report(derivation, [], [], {}, {})

    assert isinstance(report, str)
    assert report.strip() != ""
    assert "Gaps (0):" in report
    assert derivation["pattern"] in report
    assert derivation["kind"] in report


def test_render_report_ends_with_nonempty_how_to_proceed_block_after_all_sections():
    derivation = {
        "kind": "rg",
        "pattern": "ZQMARKER",
        "reason": "flag legacy calls",
        "control_term": "ZQCTRL",
    }
    hits = [
        {
            "repo": "/repo/zed",
            "file": "path/to/file.py",
            "line": 99,
            "snippet": "ZQMARKER here",
            "lang": "python",
        }
    ]
    gaps = ["/repo/missing-gap"]
    suppressed = {"/repo/zed": 44}

    report = sweep.render_report(derivation, hits, gaps, suppressed, {})

    candidates = [
        (derivation["pattern"], report.rfind(derivation["pattern"])),
        (derivation["reason"], report.rfind(derivation["reason"])),
        (hits[0]["file"], report.rfind(hits[0]["file"])),
        (str(hits[0]["line"]), report.rfind(str(hits[0]["line"]))),
        (gaps[0], report.rfind(gaps[0])),
        (str(suppressed["/repo/zed"]), report.rfind(str(suppressed["/repo/zed"]))),
    ]
    assert all(pos != -1 for _text, pos in candidates), "expected content missing from report"
    tail_start = max(pos + len(text) for text, pos in candidates)
    tail = report[tail_start:]

    assert len(tail.strip()) > 0


def test_render_report_is_deterministic_for_same_inputs():
    derivation = {
        "kind": "rg",
        "pattern": "DETMARKER",
        "reason": "check determinism",
        "control_term": "z",
    }
    hits = [
        {
            "repo": "/repo/det",
            "file": "a.py",
            "line": 5,
            "snippet": "DETMARKER x",
            "lang": "python",
        }
    ]
    gaps = ["/repo/det-gap"]
    suppressed = {"/repo/det": 9}

    first = sweep.render_report(dict(derivation), list(hits), list(gaps), dict(suppressed), {})
    second = sweep.render_report(dict(derivation), list(hits), list(gaps), dict(suppressed), {})

    assert first == second


def test_render_report_rg_kind_emits_no_ast_grep_rule_block():
    derivation = {
        "kind": "rg",
        "pattern": "NOASTGREP",
        "reason": "y",
        "control_term": "z",
    }
    hits = [
        {
            "repo": "/repo/x",
            "file": "a.py",
            "line": 1,
            "snippet": "NOASTGREP here",
            "lang": "python",
        }
    ]

    report = sweep.render_report(derivation, hits, [], {}, {})

    assert not _extract_rule_pack_blocks(report)
    assert "severity: warning" not in report


def _build_astgrep_rule_report(tmp_path):
    repo = tmp_path / "repo"
    repo.mkdir()
    (repo / "sample.py").write_text("processInput(42)\n")
    (repo / "sample.js").write_text("processInput(42);\n")

    derivation = {
        "kind": "astgrep",
        "pattern": "processInput($X)",
        "reason": "flag legacy handler calls",
        "control_term": "processInput",
    }
    hits = [
        {
            "repo": str(repo),
            "file": "sample.py",
            "line": 1,
            "snippet": "processInput(42)",
            "lang": "python",
        },
        {
            "repo": str(repo),
            "file": "sample.js",
            "line": 1,
            "snippet": "processInput(42);",
            "lang": "javascript",
        },
    ]

    report = sweep.render_report(derivation, hits, [], {}, {})

    blocks = _extract_rule_pack_blocks(report)
    assert blocks, "expected an ast-grep rule-pack block in the report"
    rule_text = "\n---\n".join(blocks) if len(blocks) > 1 else blocks[0]
    return repo, rule_text


def test_render_report_astgrep_rule_block_contains_expected_fields(tmp_path):
    _repo, rule_text = _build_astgrep_rule_report(tmp_path)

    assert "id:" in rule_text
    assert "language: python" in rule_text
    assert "language: javascript" in rule_text
    assert "severity: warning" in rule_text
    assert "message:" in rule_text
    assert "pattern: processInput($X)" in rule_text


def test_render_report_astgrep_rule_block_runs_unedited_and_finds_planted_matches(
    tmp_path,
):
    repo, rule_text = _build_astgrep_rule_report(tmp_path)

    rule_file = tmp_path / "extracted-rule.yml"
    rule_file.write_text(rule_text)

    result = subprocess.run(
        [sweep.resolve_ast_grep(), "scan", "--rule", str(rule_file), str(repo)],
        capture_output=True,
        text=True,
    )

    assert result.returncode == 0
    assert "sample.py" in result.stdout
    assert "sample.js" in result.stdout


def test_render_report_performs_no_subprocess_or_file_io(monkeypatch):
    def _forbidden(*_args, **_kwargs):
        raise AssertionError("render_report must not perform I/O")

    monkeypatch.setattr(sweep.subprocess, "run", _forbidden)
    monkeypatch.setattr(Path, "write_text", _forbidden)
    monkeypatch.setattr(Path, "read_text", _forbidden)
    monkeypatch.setattr("builtins.open", _forbidden)

    derivation = {
        "kind": "astgrep",
        "pattern": "IOMARKER($X)",
        "reason": "y",
        "control_term": "z",
    }
    hits = [
        {
            "repo": "/repo/io",
            "file": "a.py",
            "line": 1,
            "snippet": "IOMARKER(1)",
            "lang": "python",
        }
    ]
    gaps = ["/repo/io-gap"]
    suppressed = {"/repo/io": 3}

    report = sweep.render_report(derivation, hits, gaps, suppressed, {})

    assert isinstance(report, str)
    assert report.strip() != ""


# -- main (CLI end-to-end) --------------------------------------------------


def _build_sweep_main_scaffold(tmp_path, monkeypatch, marker, build_repo):
    """Set up three registered repos (each built by `build_repo` and planted
    with one `marker` match), a control repo, and a registry. Returns
    `(argv, repos, out_path)` so callers can run `sweep.main(argv)` at the
    point in the test that suits them."""
    empty_portfolio_root = tmp_path / "empty_portfolio_root"
    empty_portfolio_root.mkdir()
    monkeypatch.setattr(sweep, "PORTFOLIO_ROOT", empty_portfolio_root)

    repo_a = build_repo(tmp_path / "org" / "repo-a")
    repo_b = build_repo(tmp_path / "org" / "repo-b")
    repo_c = build_repo(tmp_path / "org" / "repo-c")
    for repo in (repo_a, repo_b, repo_c):
        _plant_matches(repo, marker, 1)

    control_repo = tmp_path / "control"
    control_repo.mkdir()
    (control_repo / "file.txt").write_text(f"{marker} control line\n")

    registry = tmp_path / "repos.csv"
    _write_registry(registry, [str(repo_a), str(repo_b), str(repo_c)])

    out_path = repo_a / "report.md"

    argv = [
        "--kind", "rg",
        "--pattern", marker,
        "--reason", f"regression test for {marker}",
        "--control-term", marker,
        "--control-repo", str(control_repo),
        "--registry", str(registry),
        "--cwd", str(repo_a),
        "--out", str(out_path),
    ]

    return argv, (repo_a, repo_b, repo_c), out_path


def test_main_wires_pipeline_and_writes_report_with_one_row_per_planted_bug(
    tmp_path, monkeypatch
):
    argv, (repo_a, repo_b, repo_c), out_path = _build_sweep_main_scaffold(
        tmp_path, monkeypatch, "MAINE2EMARKER", _make_repo
    )

    exit_code = sweep.main(argv)

    assert isinstance(exit_code, int)
    assert exit_code == 0
    assert out_path.exists()

    report = out_path.read_text()

    assert "Hits (3):" in report
    hit_lines = re.findall(r"^- .+:\d+: .*MAINE2EMARKER.*$", report, re.MULTILINE)
    assert len(hit_lines) == 3
    for repo in (repo_a, repo_b, repo_c):
        assert str(repo) in report


def test_sweep_is_read_only_and_leaves_non_current_repos_status_byte_identical(
    tmp_path, monkeypatch
):
    argv, (repo_a, repo_b, repo_c), out_path = _build_sweep_main_scaffold(
        tmp_path,
        monkeypatch,
        "READONLYSWEEPMARKER",
        lambda root: _init_git_repo_with_tracked_files(root, ["README.md"]),
    )

    non_current_repos = [repo_b, repo_c]

    status_before = {repo: _git_status_porcelain(repo) for repo in non_current_repos}

    exit_code = sweep.main(argv)

    assert exit_code == 0

    for repo in non_current_repos:
        assert _git_status_porcelain(repo) == status_before[repo]


def test_main_survives_broken_buvis_bare_git_call_and_reports_it_as_failed(
    tmp_path, monkeypatch
):
    # _buvis_bare_entry() runs `git ls-files` with check=True against
    # BUVIS_BARE["git_dir"]; pointing that at a nonexistent git dir makes
    # the call fail exactly the way a broken bare repo would. The sweep
    # must still finish and write a report naming the bare repo as failed,
    # instead of the exception aborting enumerate_repos and main().
    empty_portfolio_root = tmp_path / "empty_portfolio_root"
    empty_portfolio_root.mkdir()
    monkeypatch.setattr(sweep, "PORTFOLIO_ROOT", empty_portfolio_root)

    fixture_home = tmp_path / "fixture_home"
    fixture_home.mkdir()
    monkeypatch.setattr(
        sweep,
        "BUVIS_BARE",
        {"git_dir": tmp_path / "does-not-exist" / ".git", "work_tree": fixture_home},
    )

    registry = tmp_path / "repos.csv"
    _write_registry(registry, [])

    control_repo = tmp_path / "control"
    control_repo.mkdir()
    (control_repo / "file.txt").write_text("BAREFAILMARKER control line\n")

    out_path = fixture_home / "report.md"
    argv = [
        "--kind", "rg",
        "--pattern", "BAREFAILMARKER",
        "--reason", "regression test for broken bare entry",
        "--control-term", "BAREFAILMARKER",
        "--control-repo", str(control_repo),
        "--registry", str(registry),
        "--cwd", str(fixture_home),
        "--out", str(out_path),
    ]

    exit_code = sweep.main(argv)

    assert exit_code == 0
    assert out_path.exists()
    report = out_path.read_text()
    assert "Failed:" in report
    assert str(fixture_home) in report


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


# -- render_report: names a failed repo ---------------------------------


def test_render_report_names_a_failed_repo_with_its_reason_and_not_as_suppressed():
    # Shape assumed: render_report() widens to accept a fifth positional
    # parameter, `failed`, mirroring the `failed` channel scan() now
    # returns: a dict mapping str(repo) to a non-empty reason string for
    # repos that could not be scanned at all. Every existing
    # render_report(...) call site in this file gains a trailing `{}`
    # argument for this new parameter -- mechanical only, the same kind of
    # update already made for scan()'s widened 3-tuple return.
    derivation = {"kind": "rg", "pattern": "X", "reason": "y", "control_term": "z"}
    suppressed = {"/repo/capped": 5}
    failed = {"/repo/unreachable": "no such file or directory"}

    report = sweep.render_report(derivation, [], [], suppressed, failed)

    assert "/repo/unreachable" in report
    assert "no such file or directory" in report

    # The two channels must stay apart: a repo that was never searched must
    # never be described with the cap-suppression wording ("N more hits
    # suppressed (cap reached)") that the truly-capped repo above gets.
    failed_repo_lines = [line for line in report.splitlines() if "/repo/unreachable" in line]
    assert failed_repo_lines
    assert all("suppressed (cap reached)" not in line for line in failed_repo_lines)


def test_render_report_collapses_multiline_failed_reason_into_a_single_line():
    # _run_rg raises RuntimeError(f"rg failed: {result.stderr}"), and rg's
    # stderr is routinely multi-line (e.g. a regex parse error). The
    # "Failed:" section's contract is one line per repo, so embedded
    # newlines/whitespace in the reason must be collapsed before rendering.
    derivation = {"kind": "rg", "pattern": "X", "reason": "y", "control_term": "z"}
    failed = {"/repo/multiline": "rg failed: line one\nline two\n  line three"}

    report = sweep.render_report(derivation, [], [], {}, failed)

    matching_lines = [line for line in report.splitlines() if "/repo/multiline" in line]
    assert len(matching_lines) == 1
    assert "line one line two line three" in matching_lines[0]


# -- module imports -----------------------------------------------------


def test_sweep_module_imports_only_stdlib_modules():
    # Pins the "runs on a bare python3" contract: no third-party import at
    # module load time, so the script cannot die on import before it
    # parses a single argument on a machine that never installed anything
    # for it. Parses the source rather than inspecting sys.modules, so this
    # fails on the import statement itself rather than on whatever happens
    # to be installed on the machine running the suite.
    source = Path(sweep.__file__).read_text()
    tree = ast.parse(source, filename=sweep.__file__)

    top_level_modules = set()
    for node in ast.walk(tree):
        if isinstance(node, ast.Import):
            for alias in node.names:
                top_level_modules.add(alias.name.split(".")[0])
        elif isinstance(node, ast.ImportFrom):
            if node.level == 0 and node.module:
                top_level_modules.add(node.module.split(".")[0])

    non_stdlib = sorted(top_level_modules - sys.stdlib_module_names)
    assert not non_stdlib, f"sweep.py imports non-stdlib module(s): {non_stdlib}"


# -- render_report: ast-grep rule block quoting --------------------------


def _render_astgrep_rule_text(reason, pattern):
    """Render a single-language ast-grep rule-pack block and return its raw
    text. render_report performs no I/O (see
    test_render_report_performs_no_subprocess_or_file_io), so this needs no
    tmp_path or files on disk -- just a derivation and one hit."""
    derivation = {
        "kind": "astgrep",
        "pattern": pattern,
        "reason": reason,
        "control_term": "control-term",
    }
    hits = [
        {
            "repo": "/repo/quoting",
            "file": "sample.py",
            "line": 1,
            "snippet": "irrelevant",
            "lang": "python",
        }
    ]

    report = sweep.render_report(derivation, hits, [], {}, {})

    blocks = _extract_rule_pack_blocks(report)
    assert blocks, "expected an ast-grep rule-pack block in the report"
    return blocks[0]


def test_render_report_astgrep_rule_block_roundtrips_colon_space_value():
    value = "flag foo: bar handler calls"

    rule_text = _render_astgrep_rule_text(reason=value, pattern=value)
    parsed = yaml.safe_load(rule_text)

    assert parsed["message"] == value
    assert parsed["rule"]["pattern"] == value


def test_render_report_astgrep_rule_block_roundtrips_double_quote_value():
    value = 'flag "quoted" handler calls'

    rule_text = _render_astgrep_rule_text(reason=value, pattern=value)
    parsed = yaml.safe_load(rule_text)

    assert parsed["message"] == value
    assert parsed["rule"]["pattern"] == value


def test_render_report_astgrep_rule_block_roundtrips_single_quote_value():
    value = "flag it's handler calls"

    rule_text = _render_astgrep_rule_text(reason=value, pattern=value)
    parsed = yaml.safe_load(rule_text)

    assert parsed["message"] == value
    assert parsed["rule"]["pattern"] == value


def test_render_report_astgrep_rule_block_roundtrips_hash_value():
    value = "flag #legacy handler calls"

    rule_text = _render_astgrep_rule_text(reason=value, pattern=value)
    parsed = yaml.safe_load(rule_text)

    assert parsed["message"] == value
    assert parsed["rule"]["pattern"] == value


@pytest.mark.parametrize(
    "value",
    ["null", "true", "- leading dash handler"],
    ids=["null-token", "true-token", "leading-dash"],
)
def test_render_report_astgrep_rule_block_roundtrips_whole_value_yaml_token(value):
    rule_text = _render_astgrep_rule_text(reason=value, pattern=value)
    parsed = yaml.safe_load(rule_text)

    assert parsed["message"] == value
    assert parsed["rule"]["pattern"] == value


def test_render_report_astgrep_rule_block_roundtrips_newline_value():
    value = "flag handler calls\nacross two lines"

    rule_text = _render_astgrep_rule_text(reason=value, pattern=value)
    parsed = yaml.safe_load(rule_text)

    assert parsed["message"] == value
    assert parsed["rule"]["pattern"] == value


@pytest.mark.parametrize(
    "value",
    [" leading space", "trailing space ", "123", "1.5", "0x1F", "1_000", "2026-08-29"],
    ids=[
        "leading-space",
        "trailing-space",
        "bare-int",
        "bare-float",
        "hex-int",
        "underscore-int",
        "bare-date",
    ],
)
def test_render_report_astgrep_rule_block_roundtrips_type_coercion_value(value):
    rule_text = _render_astgrep_rule_text(reason=value, pattern=value)
    parsed = yaml.safe_load(rule_text)

    assert parsed["message"] == value
    assert parsed["rule"]["pattern"] == value


@pytest.mark.parametrize(
    "value",
    ["flag\thandler calls", ".inf", "-.inf", ".nan"],
    ids=["tab", "dot-inf", "dot-neg-inf", "dot-nan"],
)
def test_render_report_astgrep_rule_block_roundtrips_control_and_special_float_value(value):
    rule_text = _render_astgrep_rule_text(reason=value, pattern=value)
    parsed = yaml.safe_load(rule_text)

    assert parsed["message"] == value
    assert isinstance(parsed["message"], str)
    assert parsed["rule"]["pattern"] == value
    assert isinstance(parsed["rule"]["pattern"], str)


@pytest.mark.parametrize(
    "value",
    ["flag\rhandler calls", "flag\thandler calls", "flag\x00handler calls"],
    ids=["carriage-return", "tab", "nul"],
)
def test_render_report_astgrep_rule_block_roundtrips_escaped_control_char_value(value):
    rule_text = _render_astgrep_rule_text(reason=value, pattern=value)
    parsed = yaml.safe_load(rule_text)

    assert parsed["message"] == value
    assert isinstance(parsed["message"], str)
    assert parsed["rule"]["pattern"] == value
    assert isinstance(parsed["rule"]["pattern"], str)


# -- main: default --out is rooted at --cwd, not at the process cwd --------


def test_main_default_out_lands_under_cwd_repo_when_process_cwd_is_elsewhere(
    tmp_path, monkeypatch
):
    argv, (repo_a, _repo_b, _repo_c), _scaffold_out_path = _build_sweep_main_scaffold(
        tmp_path, monkeypatch, "DEFAULTOUTROOTMARKER", _make_repo
    )
    out_index = argv.index("--out")
    del argv[out_index : out_index + 2]  # omit --out so main() computes the default

    elsewhere = tmp_path / "elsewhere"
    elsewhere.mkdir()
    monkeypatch.chdir(elsewhere)

    exit_code = sweep.main(argv)

    assert exit_code == 0

    expected_dir = repo_a / "dev" / "local" / "audit-results"
    assert expected_dir.is_dir(), f"expected a report directory at {expected_dir}"
    reports = list(expected_dir.glob("sweep-*.md"))
    assert len(reports) == 1, f"expected exactly one report in {expected_dir}"
    report_name = reports[0].name

    # Filename shape (root aside) is unchanged: sweep-{slug}-{date}.md.
    today = time.strftime("%Y-%m-%d")
    assert re.match(rf"^sweep-.+-{re.escape(today)}\.md$", report_name), report_name

    # The old bug rooted the default path at the process cwd instead.
    assert not (elsewhere / "dev").exists()


# -- main: --out is confined to the --cwd repo ------------------------------


def test_main_refuses_relative_out_that_escapes_cwd_repo_via_dotdot(
    tmp_path, monkeypatch, capsys
):
    # Assumed failure mechanism: main() raises SystemExit (sys.exit(1)) with
    # a message on stderr, mirroring verify_control's existing convention
    # for a caller error that must stop the whole run. An implementer could
    # instead have main() return a non-zero int without raising; if so, this
    # test's pytest.raises(SystemExit) would need to become an exit-code
    # assertion instead.
    argv, (repo_a, _repo_b, _repo_c), _scaffold_out_path = _build_sweep_main_scaffold(
        tmp_path, monkeypatch, "ESCAPEDOTDOTMARKER", _make_repo
    )
    out_index = argv.index("--out")
    escaping_out = "../escaped-report.md"
    argv[out_index + 1] = escaping_out
    target = (repo_a / escaping_out).resolve()

    with pytest.raises(SystemExit) as exc_info:
        sweep.main(argv)

    assert exc_info.value.code != 0
    assert not target.exists()
    message = capsys.readouterr().err
    assert message.strip() != ""
    assert escaping_out in message or str(target) in message


def test_main_refuses_absolute_out_outside_cwd_repo(tmp_path, monkeypatch, capsys):
    # Assumed failure mechanism: same as
    # test_main_refuses_relative_out_that_escapes_cwd_repo_via_dotdot above.
    argv, (repo_a, _repo_b, _repo_c), _scaffold_out_path = _build_sweep_main_scaffold(
        tmp_path, monkeypatch, "ABSOUTSIDEMARKER", _make_repo
    )
    out_index = argv.index("--out")
    outside_dir = tmp_path / "elsewhere"
    outside_dir.mkdir()
    outside_out = outside_dir / "escaped-report.md"
    argv[out_index + 1] = str(outside_out)

    with pytest.raises(SystemExit) as exc_info:
        sweep.main(argv)

    assert exc_info.value.code != 0
    assert not outside_out.exists()
    message = capsys.readouterr().err
    assert message.strip() != ""
    assert str(outside_out) in message


def test_main_accepts_out_nested_several_directories_inside_cwd_repo(
    tmp_path, monkeypatch
):
    argv, (repo_a, _repo_b, _repo_c), _scaffold_out_path = _build_sweep_main_scaffold(
        tmp_path, monkeypatch, "NESTEDOUTMARKER", _make_repo
    )
    out_index = argv.index("--out")
    nested_out = repo_a / "dev" / "local" / "audit-results" / "nested-report.md"
    argv[out_index + 1] = str(nested_out)

    exit_code = sweep.main(argv)

    assert exit_code == 0
    assert nested_out.exists()
    assert nested_out.read_text().strip() != ""


# -- main: control check runs only when the whole sweep found nothing -------


def test_main_completes_and_reports_hits_when_pattern_absent_from_control_repo_but_present_elsewhere(
    tmp_path, monkeypatch
):
    # The control repo is typically the repo the fix just landed in, and the
    # fix usually removed the pattern from it -- so the pattern is
    # legitimately absent from the control repo while still present in
    # every repo that has not been fixed yet. verify_control's own contract
    # says it only guards the all-zero case; a sweep that already found
    # hits elsewhere has nothing left to verify, so this combination must
    # not abort the sweep.
    empty_portfolio_root = tmp_path / "empty_portfolio_root"
    empty_portfolio_root.mkdir()
    monkeypatch.setattr(sweep, "PORTFOLIO_ROOT", empty_portfolio_root)

    repo_a = _make_repo(tmp_path / "org" / "repo-a")
    _plant_matches(repo_a, "REORDERPATTERN", 1)

    control_repo = tmp_path / "control"
    control_repo.mkdir()
    (control_repo / "file.txt").write_text(
        "REORDERCONTROLTERM only, no pattern text here\n"
    )

    registry = tmp_path / "repos.csv"
    _write_registry(registry, [str(repo_a)])

    out_path = repo_a / "report.md"
    argv = [
        "--kind", "rg",
        "--pattern", "REORDERPATTERN",
        "--reason", "regression test for control-check ordering",
        "--control-term", "REORDERCONTROLTERM",
        "--control-repo", str(control_repo),
        "--registry", str(registry),
        "--cwd", str(repo_a),
        "--out", str(out_path),
    ]

    exit_code = sweep.main(argv)

    assert exit_code == 0
    assert out_path.exists()

    report = out_path.read_text()
    assert "Hits (1):" in report
    hit_lines = re.findall(r"^- .+:\d+: .*REORDERPATTERN.*$", report, re.MULTILINE)
    assert len(hit_lines) == 1
    assert str(repo_a) in report


def test_main_still_aborts_as_unverified_when_all_zero_sweep_and_control_term_present(
    tmp_path, monkeypatch, capsys
):
    # Pairing case for the test above: a genuinely all-zero sweep (the
    # pattern has no hits anywhere, including the control repo) with the
    # control term present in the control repo must still abort. This
    # proves the reorder narrowed the check to the all-zero case rather
    # than disabling it outright.
    empty_portfolio_root = tmp_path / "empty_portfolio_root"
    empty_portfolio_root.mkdir()
    monkeypatch.setattr(sweep, "PORTFOLIO_ROOT", empty_portfolio_root)

    repo_a = _make_repo(tmp_path / "org" / "repo-a")

    control_repo = tmp_path / "control"
    control_repo.mkdir()
    (control_repo / "file.txt").write_text(
        "ALLZEROCONTROLTERM only, no pattern text here\n"
    )

    registry = tmp_path / "repos.csv"
    _write_registry(registry, [str(repo_a)])

    out_path = repo_a / "report.md"
    argv = [
        "--kind", "rg",
        "--pattern", "ALLZEROPATTERN",
        "--reason", "regression test for all-zero abort still working",
        "--control-term", "ALLZEROCONTROLTERM",
        "--control-repo", str(control_repo),
        "--registry", str(registry),
        "--cwd", str(repo_a),
        "--out", str(out_path),
    ]

    with pytest.raises(SystemExit) as exc_info:
        sweep.main(argv)

    assert exc_info.value.code == 1
    assert not out_path.exists()
    message = capsys.readouterr().err
    assert "unverified" in message
    assert "ALLZEROCONTROLTERM" in message
    assert str(control_repo) in message


# -- render_report: how-to-proceed block states the safety rule -------------


def _how_to_proceed_block():
    """Render a report and return the text of its how-to-proceed block: the
    tail after every other rendered section, using the same last-known-
    content technique as
    test_render_report_ends_with_nonempty_how_to_proceed_block_after_all_sections."""
    derivation = {
        "kind": "rg",
        "pattern": "PROCEEDMARKER",
        "reason": "flag legacy calls",
        "control_term": "PROCEEDCTRL",
    }
    hits = [
        {
            "repo": "/repo/zed",
            "file": "path/to/file.py",
            "line": 99,
            "snippet": "PROCEEDMARKER here",
            "lang": "python",
        }
    ]
    gaps = ["/repo/missing-gap"]
    suppressed = {"/repo/zed": 44}

    report = sweep.render_report(derivation, hits, gaps, suppressed, {})

    candidates = [
        derivation["pattern"],
        derivation["reason"],
        hits[0]["file"],
        str(hits[0]["line"]),
        gaps[0],
        str(suppressed["/repo/zed"]),
    ]
    tail_start = max(report.rfind(text) + len(text) for text in candidates)
    return report[tail_start:]


def test_render_report_how_to_proceed_states_fixes_apply_only_in_invoking_repo():
    block = _how_to_proceed_block().lower()

    assert "only in the repo" in block
    assert "report-only" in block or "report only" in block


def test_render_report_how_to_proceed_states_fix_applied_only_after_approval():
    block = _how_to_proceed_block().lower()

    assert "only after" in block
    assert "approv" in block


# -- main: prints the report path ---


def test_main_prints_resolved_report_path_to_stdout_on_success_with_explicit_relative_out(
    tmp_path, monkeypatch, capsys
):
    # The raw --out argument is relative and is resolved against --cwd, not
    # the process cwd; chdir'ing elsewhere proves the printed path can't be
    # the caller's raw string re-emitted, nor built from process cwd.
    argv, (repo_a, _repo_b, _repo_c), _scaffold_out_path = _build_sweep_main_scaffold(
        tmp_path, monkeypatch, "EXPLICITOUTPRINTMARKER", _make_repo
    )
    out_index = argv.index("--out")
    relative_out = "printed-report.md"
    argv[out_index + 1] = relative_out
    expected_out_path = repo_a / relative_out

    elsewhere = tmp_path / "elsewhere"
    elsewhere.mkdir()
    monkeypatch.chdir(elsewhere)

    exit_code = sweep.main(argv)

    assert exit_code == 0
    assert expected_out_path.exists()

    captured = capsys.readouterr()
    assert str(expected_out_path) in captured.out


def test_main_prints_resolved_report_path_to_stdout_on_success_with_default_out(
    tmp_path, monkeypatch, capsys
):
    argv, (repo_a, _repo_b, _repo_c), _scaffold_out_path = _build_sweep_main_scaffold(
        tmp_path, monkeypatch, "DEFAULTOUTPRINTMARKER", _make_repo
    )
    out_index = argv.index("--out")
    del argv[out_index : out_index + 2]  # omit --out so main() computes the default

    elsewhere = tmp_path / "elsewhere"
    elsewhere.mkdir()
    monkeypatch.chdir(elsewhere)

    exit_code = sweep.main(argv)

    assert exit_code == 0

    expected_dir = repo_a / "dev" / "local" / "audit-results"
    reports = list(expected_dir.glob("sweep-*.md"))
    assert len(reports) == 1, f"expected exactly one report in {expected_dir}"
    written_report = reports[0]

    captured = capsys.readouterr()
    assert str(written_report) in captured.out


# -- main: --cap must be a positive integer ---


def test_main_rejects_cap_of_zero(tmp_path, monkeypatch, capsys):
    argv, (_repo_a, _repo_b, _repo_c), out_path = _build_sweep_main_scaffold(
        tmp_path, monkeypatch, "ZEROCAPMARKER", _make_repo
    )
    argv += ["--cap", "0"]

    with pytest.raises(SystemExit) as exc_info:
        sweep.main(argv)

    assert exc_info.value.code != 0
    assert not out_path.exists()
    captured = capsys.readouterr()
    assert "cap" in (captured.out + captured.err).lower()


def test_main_rejects_negative_cap(tmp_path, monkeypatch, capsys):
    argv, (_repo_a, _repo_b, _repo_c), out_path = _build_sweep_main_scaffold(
        tmp_path, monkeypatch, "NEGATIVECAPMARKER", _make_repo
    )
    argv += ["--cap", "-1"]

    with pytest.raises(SystemExit) as exc_info:
        sweep.main(argv)

    assert exc_info.value.code != 0
    assert not out_path.exists()
    captured = capsys.readouterr()
    assert "cap" in (captured.out + captured.err).lower()


def test_main_accepts_cap_of_one_as_smallest_legal_value(tmp_path, monkeypatch):
    argv, (repo_a, repo_b, repo_c), out_path = _build_sweep_main_scaffold(
        tmp_path, monkeypatch, "ONECAPMARKER", _make_repo
    )
    argv += ["--cap", "1"]

    exit_code = sweep.main(argv)

    assert exit_code == 0
    assert out_path.exists()
    report = out_path.read_text()
    for repo in (repo_a, repo_b, repo_c):
        assert str(repo) in report
