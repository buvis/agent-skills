"""Tests for sweep.py: enumerate_repos."""
import os
from pathlib import Path

import pytest

import sweep
from sweep_test_helpers import (
    _init_git_repo_with_tracked_files,
    _make_repo,
    _plant_matches,
    _write_registry,
)


# -- enumerate_repos --------------------------------------------------------


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


# -- cwd walk-up to the git root ---------------------------------------------


def test_a_subdirectory_cwd_resolves_to_its_repo_root_and_is_not_a_gap(
    tmp_path, monkeypatch
):
    portfolio_root = tmp_path / "portfolio"
    monkeypatch.setattr(sweep, "PORTFOLIO_ROOT", portfolio_root)

    repo = _make_repo(portfolio_root / "org" / "repo")
    nested = repo / "a" / "b"
    nested.mkdir(parents=True)
    _plant_matches(repo, "SUBDIRWALKUPMARKER", 1)  # at the root, outside a/b
    other = _make_repo(portfolio_root / "org" / "other")  # unregistered: a real gap
    registry = tmp_path / "repos.csv"
    _write_registry(registry, [str(repo)])

    repos, gaps = sweep.enumerate_repos(registry, nested)

    assert repos == [repo]
    assert nested not in repos
    assert gaps == [str(other)]

    hits, _suppressed, _failed = sweep.scan("SUBDIRWALKUPMARKER", "rg", repos)

    matched_files = {Path(hit["file"]).name for hit in hits}
    assert matched_files == {"match_000.txt"}


def test_an_unregistered_repo_run_from_its_subdirectory_is_scanned_and_not_a_gap(
    tmp_path, monkeypatch
):
    portfolio_root = tmp_path / "portfolio"
    monkeypatch.setattr(sweep, "PORTFOLIO_ROOT", portfolio_root)

    repo = _make_repo(portfolio_root / "org" / "repo")
    nested = repo / "a" / "b"
    nested.mkdir(parents=True)
    other = _make_repo(portfolio_root / "org" / "other")  # unregistered: a real gap
    registry = tmp_path / "repos.csv"
    _write_registry(registry, [])

    repos, gaps = sweep.enumerate_repos(registry, nested)

    assert repo in repos
    assert repos.count(repo) == 1
    assert nested not in repos
    assert gaps == [str(other)]


def test_a_relative_subdirectory_cwd_walks_up_to_the_absolute_repo_root(
    tmp_path, monkeypatch
):
    empty_portfolio_root = tmp_path / "empty_portfolio_root"
    empty_portfolio_root.mkdir()
    monkeypatch.setattr(sweep, "PORTFOLIO_ROOT", empty_portfolio_root)

    repo = _make_repo(tmp_path / "org" / "repo")
    nested = repo / "a" / "b"
    nested.mkdir(parents=True)
    registry = tmp_path / "repos.csv"
    _write_registry(registry, [])
    monkeypatch.chdir(nested)

    repos, _gaps = sweep.enumerate_repos(registry, Path("."))

    assert repo in repos
    assert nested not in repos
    path_entries = [Path(entry) for entry in repos if not isinstance(entry, dict)]
    assert all(entry.is_absolute() for entry in path_entries)

    monkeypatch.chdir(repo)  # a multi-part relative cwd, not just "."

    repos, _gaps = sweep.enumerate_repos(registry, Path("a/b"))

    assert repo in repos
    assert nested not in repos
    path_entries = [Path(entry) for entry in repos if not isinstance(entry, dict)]
    assert all(entry.is_absolute() for entry in path_entries)


def test_a_relative_cwd_outside_any_repo_is_appended_as_its_absolute_path(
    tmp_path, monkeypatch
):
    empty_portfolio_root = tmp_path / "empty_portfolio_root"
    empty_portfolio_root.mkdir()
    monkeypatch.setattr(sweep, "PORTFOLIO_ROOT", empty_portfolio_root)

    plain = tmp_path / "plain"
    plain.mkdir()  # no .git here or in any ancestor under tmp_path
    registry = tmp_path / "repos.csv"
    _write_registry(registry, [])
    monkeypatch.chdir(plain)

    repos, _gaps = sweep.enumerate_repos(registry, Path("."))

    assert plain in repos
    path_entries = [Path(entry) for entry in repos if not isinstance(entry, dict)]
    assert all(entry.is_absolute() for entry in path_entries)


def test_git_root_walks_up_to_a_repo_whose_git_entry_is_a_file(tmp_path):
    repo = tmp_path / "worktree"
    repo.mkdir()
    (repo / ".git").write_text("gitdir: /elsewhere/.git/worktrees/worktree\n")
    nested = repo / "a" / "b"
    nested.mkdir(parents=True)
    deep = repo / "a" / "b" / "c" / "d" / "e"
    deep.mkdir(parents=True)

    assert sweep._git_root(nested) == repo
    assert sweep._git_root(deep) == repo


def test_git_root_picks_the_nearest_repo_including_the_path_itself(tmp_path):
    outer = _make_repo(tmp_path / "outer")
    inner = _make_repo(outer / "vendor" / "inner")
    inner_sub = inner / "src"
    inner_sub.mkdir()
    deep = inner / "a" / "b" / "c" / "d" / "e"
    deep.mkdir(parents=True)

    assert sweep._git_root(inner) == inner
    assert sweep._git_root(inner_sub) == inner
    assert sweep._git_root(deep) == inner
    assert sweep._git_root(outer / "vendor") == outer


def test_git_root_returns_the_path_unchanged_when_no_ancestor_holds_git(tmp_path):
    plain = tmp_path / "plain" / "dir"
    plain.mkdir(parents=True)

    assert sweep._git_root(plain) == plain


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


def test_a_subdirectory_cwd_inside_the_bare_work_tree_becomes_the_bare_entry(
    tmp_path, monkeypatch
):
    fixture_home, registry = _setup_buvis_bare_fixture(
        tmp_path, monkeypatch, ["top.txt", "sub/nested.txt"], untracked=["loose.tmp"]
    )
    (fixture_home / "top.txt").write_text("BARESUBDIRMARKER content\n")
    (fixture_home / "sub" / "nested.txt").write_text("BARESUBDIRMARKER content\n")
    (fixture_home / "loose.tmp").write_text("BARESUBDIRMARKER content\n")

    repos, _gaps = sweep.enumerate_repos(registry, fixture_home / "sub")

    bare_entries = [
        repo for repo in repos if isinstance(repo, dict) and repo["cwd"] == fixture_home
    ]
    assert len(bare_entries) == 1
    plain_entries = [repo for repo in repos if not isinstance(repo, dict)]
    assert fixture_home not in plain_entries
    assert fixture_home / "sub" not in plain_entries

    hits, _suppressed, _failed = sweep.scan("BARESUBDIRMARKER", "rg", repos)

    matched_files = {Path(hit["file"]).name for hit in hits}
    assert matched_files == {"top.txt", "nested.txt"}


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


# -- enumerate_repos: `..` segments in cwd -----------------------------------


def test_enumerate_repos_normalises_dotdot_cwd_to_the_registered_repo_once(
    tmp_path, monkeypatch
):
    base = tmp_path.resolve()
    empty_portfolio_root = base / "empty_portfolio_root"
    empty_portfolio_root.mkdir()
    monkeypatch.setattr(sweep, "PORTFOLIO_ROOT", empty_portfolio_root)

    registered = _make_repo(base / "org" / "repo-a")
    (registered / "a").mkdir()
    registry = base / "repos.csv"
    _write_registry(registry, [str(registered)])

    repos, _gaps = sweep.enumerate_repos(registry, registered / "a" / "..")

    assert repos.count(registered) == 1
    assert not [repo for repo in repos if ".." in str(repo)]


def test_enumerate_repos_resolves_dotdot_cwd_into_unregistered_portfolio_repo(
    tmp_path, monkeypatch
):
    portfolio_root = tmp_path.resolve() / "portfolio"
    monkeypatch.setattr(sweep, "PORTFOLIO_ROOT", portfolio_root)

    repo = _make_repo(portfolio_root / "org" / "repo")
    (repo / "a" / "b").mkdir(parents=True)
    registry = tmp_path.resolve() / "repos.csv"
    _write_registry(registry, [])

    repos, gaps = sweep.enumerate_repos(registry, repo / "a" / ".." / "a" / "b")

    assert Path(repo) in repos
    assert not [entry for entry in repos if ".." in str(entry)]
    assert gaps == []


def test_enumerate_repos_resolves_a_relative_dotdot_cwd_to_the_absolute_repo_root(
    tmp_path, monkeypatch
):
    portfolio_root = tmp_path.resolve() / "portfolio"
    monkeypatch.setattr(sweep, "PORTFOLIO_ROOT", portfolio_root)

    repo = _make_repo(portfolio_root / "org" / "repo")
    (repo / "a" / "b").mkdir(parents=True)
    registry = tmp_path.resolve() / "repos.csv"
    _write_registry(registry, [])
    monkeypatch.chdir(repo / "a" / "b")

    repos, gaps = sweep.enumerate_repos(registry, Path("../../a/b/.."))

    assert repos == [repo]
    assert gaps == []


# -- enumerate_repos: unreadable registry ------------------------------------


def test_enumerate_repos_reports_missing_and_non_repo_registered_rows_as_distinct_gaps(
    tmp_path, monkeypatch
):
    portfolio_root = tmp_path / "portfolio"
    monkeypatch.setattr(sweep, "PORTFOLIO_ROOT", portfolio_root)

    valid_repo = _make_repo(portfolio_root / "org" / "valid-repo")
    missing_path = portfolio_root / "org" / "missing-repo"  # never created on disk
    non_repo_path = portfolio_root / "org" / "non-repo-dir"
    non_repo_path.mkdir(parents=True)  # exists on disk but has no .git
    unregistered = _make_repo(
        portfolio_root / "org" / "unregistered-repo"
    )  # pre-existing kind of gap: on disk, not registered

    registry = tmp_path / "repos.csv"
    _write_registry(registry, [str(valid_repo), str(missing_path), str(non_repo_path)])
    cwd = tmp_path / "cwd_dir"
    cwd.mkdir()

    repos, gaps = sweep.enumerate_repos(registry, cwd)

    assert valid_repo in repos
    assert missing_path not in repos
    assert non_repo_path not in repos

    assert f"{missing_path}: not found on disk" in gaps
    assert f"{non_repo_path}: exists but is not a git repository" in gaps

    # the pre-existing unregistered-on-disk gap must still be reported
    assert any(str(unregistered) in str(gap) for gap in gaps)


def test_enumerate_repos_raises_runtimeerror_naming_an_unreadable_registry(
    tmp_path, monkeypatch
):
    if os.geteuid() == 0:
        pytest.skip("root can read a chmod 0o000 file")
    empty_portfolio_root = tmp_path / "empty_portfolio_root"
    empty_portfolio_root.mkdir()
    monkeypatch.setattr(sweep, "PORTFOLIO_ROOT", empty_portfolio_root)
    registry = tmp_path / "repos.csv"
    _write_registry(registry, [str(tmp_path / "org" / "repo-a")])
    registry.chmod(0o000)
    cwd = tmp_path / "cwd_dir"
    cwd.mkdir()

    try:
        with pytest.raises(RuntimeError) as exc_info:
            sweep.enumerate_repos(registry, cwd)
    finally:
        registry.chmod(0o600)

    assert str(registry) in str(exc_info.value)


def test_enumerate_repos_raises_runtimeerror_naming_a_non_utf8_registry(
    tmp_path, monkeypatch
):
    empty_portfolio_root = tmp_path / "empty_portfolio_root"
    empty_portfolio_root.mkdir()
    monkeypatch.setattr(sweep, "PORTFOLIO_ROOT", empty_portfolio_root)
    registry = tmp_path / "repos.csv"
    registry.write_bytes(b"\xff\xfe\xfa\n")
    cwd = tmp_path / "cwd_dir"
    cwd.mkdir()

    with pytest.raises(RuntimeError) as exc_info:
        sweep.enumerate_repos(registry, cwd)

    assert str(registry) in str(exc_info.value)
