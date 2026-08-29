"""Tests for sweep.py (resolve_rg, resolve_ast_grep)."""
import os
from pathlib import Path
import shutil
import subprocess

import pytest

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
    tmp_path, monkeypatch, capsys
):
    monkeypatch.setenv("PATH", "/usr/bin:/bin")  # no rg here
    monkeypatch.delenv("CLAUDE_CODE_EXECPATH", raising=False)
    monkeypatch.setenv("HOME", str(tmp_path))  # no ~/.local/bin/claude here

    with pytest.raises(SystemExit) as exc_info:
        sweep.resolve_rg()

    assert exc_info.value.code == 1

    out, err = capsys.readouterr()
    combined = (out + err + str(exc_info.value)).lower()
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
    monkeypatch, capsys
):
    monkeypatch.setenv("PATH", "/usr/bin:/bin")  # neither ast-grep nor mise here

    with pytest.raises(SystemExit) as exc_info:
        sweep.resolve_ast_grep()

    assert exc_info.value.code == 1

    out, err = capsys.readouterr()
    combined = (out + err + str(exc_info.value)).lower()
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


def test_enumerate_repos_uses_git_ls_files_for_buvis_bare_cwd(tmp_path, monkeypatch):
    empty_portfolio_root = tmp_path / "empty_portfolio_root"
    empty_portfolio_root.mkdir()
    monkeypatch.setattr(sweep, "PORTFOLIO_ROOT", empty_portfolio_root)

    fixture_home = tmp_path / "fixture_home"
    _init_git_repo_with_tracked_files(fixture_home, ["a.txt", "sub/b.txt"])
    monkeypatch.setattr(
        sweep,
        "BUVIS_BARE",
        {"git_dir": fixture_home / ".git", "work_tree": fixture_home},
    )
    registry = tmp_path / "repos.csv"
    _write_registry(registry, [])

    repos, _gaps = sweep.enumerate_repos(registry, fixture_home)

    assert fixture_home / "a.txt" in repos
    assert fixture_home / "sub" / "b.txt" in repos
    assert fixture_home not in repos  # replaced by its file set, not a directory walk


def test_enumerate_repos_excludes_untracked_files_from_buvis_bare_file_set(
    tmp_path, monkeypatch
):
    empty_portfolio_root = tmp_path / "empty_portfolio_root"
    empty_portfolio_root.mkdir()
    monkeypatch.setattr(sweep, "PORTFOLIO_ROOT", empty_portfolio_root)

    fixture_home = tmp_path / "fixture_home"
    _init_git_repo_with_tracked_files(
        fixture_home, ["tracked.txt"], untracked=["scratch.tmp"]
    )
    monkeypatch.setattr(
        sweep,
        "BUVIS_BARE",
        {"git_dir": fixture_home / ".git", "work_tree": fixture_home},
    )
    registry = tmp_path / "repos.csv"
    _write_registry(registry, [])

    repos, _gaps = sweep.enumerate_repos(registry, fixture_home)

    assert fixture_home / "tracked.txt" in repos
    assert fixture_home / "scratch.tmp" not in repos


# -- scan ---------------------------------------------------------------


def _plant_matches(repo, pattern, count, ext=".txt"):
    """Create `repo` with `count` files, each containing one line matching `pattern`."""
    repo.mkdir(parents=True, exist_ok=True)
    for i in range(count):
        (repo / f"match_{i:03d}{ext}").write_text(f"{pattern} line {i}\n")
    return repo


def test_scan_caps_hits_at_default_cap_and_records_suppressed_count_for_overflow(tmp_path):
    repo = _plant_matches(tmp_path / "repo", "SWEEPMARKER", 25)

    hits, suppressed = sweep.scan("SWEEPMARKER", "rg", [repo])

    repo_hits = [hit for hit in hits if hit["repo"] == str(repo)]
    assert len(repo_hits) == 20
    assert suppressed[str(repo)] == 5
    for hit in repo_hits:
        assert hit["file"]
        assert hit["line"] == 1
        assert "SWEEPMARKER" in hit["snippet"]


def test_scan_omits_suppressed_entry_for_repo_with_hits_under_cap(tmp_path):
    repo = _plant_matches(tmp_path / "repo", "UNDERMARKER", 3)

    hits, suppressed = sweep.scan("UNDERMARKER", "rg", [repo])

    repo_hits = [hit for hit in hits if hit["repo"] == str(repo)]
    assert len(repo_hits) == 3
    assert str(repo) not in suppressed
    for hit in repo_hits:
        assert hit["line"] == 1


def test_scan_applies_cap_independently_per_repo(tmp_path):
    repo_a = _plant_matches(tmp_path / "repo_a", "MULTIMARKER", 8)
    repo_b = _plant_matches(tmp_path / "repo_b", "MULTIMARKER", 3)

    hits, suppressed = sweep.scan("MULTIMARKER", "rg", [repo_a, repo_b], cap=5)

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

    hits, _suppressed = sweep.scan("LANGMARKER", "rg", [repo])

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
    original_status = subprocess.run(
        ["git", "-C", str(repo), "status", "--porcelain"],
        capture_output=True,
        text=True,
        check=True,
    ).stdout

    sweep.scan("READONLYMARKER", "rg", [repo])

    assert tracked.read_bytes() == original_bytes
    new_status = subprocess.run(
        ["git", "-C", str(repo), "status", "--porcelain"],
        capture_output=True,
        text=True,
        check=True,
    ).stdout
    assert new_status == original_status


def test_scan_supports_astgrep_kind_and_returns_matching_hits(tmp_path):
    repo = tmp_path / "repo"
    repo.mkdir()
    (repo / "sample.py").write_text('print("hi")\n')

    hits, _suppressed = sweep.scan("print($X)", "astgrep", [repo])

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
