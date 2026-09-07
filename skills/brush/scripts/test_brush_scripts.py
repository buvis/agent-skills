#!/usr/bin/env python3
"""Regression net for brush helper scripts: classification, vetoes, moves."""

from __future__ import annotations

import json
import os
import posixpath
import subprocess
import time
from pathlib import Path

import pytest

import collect_facts as cf
import trash_untracked as tu

OLD = time.time() - 10 * 86400


def _git(repo: Path, *args: str) -> None:
    subprocess.run(["git", "-C", str(repo), *args], check=True,
                   capture_output=True, text=True)


@pytest.fixture()
def repo(tmp_path: Path) -> Path:
    r = tmp_path / "r"
    r.mkdir()
    _git(r, "init", "-q", "-b", "master")
    _git(r, "config", "user.email", "t@t")
    _git(r, "config", "user.name", "t")
    (r / "tracked.log").write_text("x")
    _git(r, "add", "tracked.log")
    _git(r, "commit", "-qm", "init")
    return r


@pytest.mark.parametrize("rel,expected", [
    ("dev/local/tmp/x.bin", "devlocal"),
    (".env.local", "secret"),
    ("a/__pycache__/m.pyc", "junk-dir"),
    (".DS_Store", "os-junk"),
    ("docs/guide.pdf", "doc"),
    ("README", "doc"),
    ("node_modules/x.js", "heavy"),
    ("foo.log", "junk"),
    ("scratch_bench.py", "scratch"),
    ("src/module.py", "other"),
])
def test_classify_path_rules(rel: str, expected: str) -> None:
    assert cf.classify_path(rel) == expected


def test_default_branch_prefers_master(repo: Path) -> None:
    assert cf.detect_default_branch(repo) == "master"


def test_ctx_flags_in_progress_merge(repo: Path) -> None:
    (repo / ".git/MERGE_HEAD").write_text("x")
    assert cf.gather_repo_ctx(repo)["in_progress_op"] == ["MERGE_HEAD"]


def test_ctx_refuses_non_repo(tmp_path: Path) -> None:
    d = tmp_path / "nogit"
    d.mkdir()
    assert cf.gather_repo_ctx(d)["refusals"]


def test_ctx_refuses_home_work_tree(repo: Path,
                                    monkeypatch: pytest.MonkeyPatch) -> None:
    """A dotfiles bare repo checks out $HOME; brush never runs there."""
    top = Path(cf.git_out(repo, "rev-parse", "--show-toplevel").strip())
    monkeypatch.setattr(cf.Path, "home", classmethod(lambda cls: top))
    assert "home work-tree" in cf.gather_repo_ctx(repo)["refusals"][0]


def test_missing_pgrep_reports_no_live_batch(
        repo: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    """A host without pgrep loses the batch probe, not the whole preflight."""
    real = cf.subprocess.run

    def no_pgrep(cmd, *a, **kw):
        if cmd[0] == "pgrep":
            raise FileNotFoundError(cmd[0])
        return real(cmd, *a, **kw)

    monkeypatch.setattr(cf.subprocess, "run", no_pgrep)
    assert cf.gather_repo_ctx(repo)["autopilot_live"] is False


def test_branch_drift_counts(repo: Path) -> None:
    _git(repo, "branch", "feat")
    (repo / "f2").write_text("y")
    _git(repo, "add", "f2")
    _git(repo, "commit", "-qm", "second")
    feat = [b for b in cf.gather_branches(repo, "master", fast=True)
            if b["name"] == "feat"][0]
    assert (feat["behind"], feat["ahead"]) == (1, 0)
    assert feat["merged"] is True


def _veto(repo: Path, rel: str) -> str | None:
    return tu.veto_reason(rel, repo / rel, tu.load_tracked(repo), 3)


def test_veto_tracked_file(repo: Path) -> None:
    assert "tracked" in _veto(repo, "tracked.log")


def test_veto_doc_suffix(repo: Path) -> None:
    p = repo / "notes.md"
    p.write_text("d")
    os.utime(p, (OLD, OLD))
    assert "documentation" in _veto(repo, "notes.md")


def test_veto_devlocal_protected(repo: Path) -> None:
    p = repo / "dev/local/keep.bin"
    p.parent.mkdir(parents=True)
    p.write_text("k")
    os.utime(p, (OLD, OLD))
    assert "protected" in _veto(repo, "dev/local/keep.bin")


def test_veto_fresh_file(repo: Path) -> None:
    (repo / "fresh.tmp").write_text("f")
    assert "fresh" in _veto(repo, "fresh.tmp")


def test_old_junk_passes_veto(repo: Path) -> None:
    p = repo / "old_junk.log"
    p.write_text("j")
    os.utime(p, (OLD, OLD))
    assert _veto(repo, "old_junk.log") is None


def test_relocate_writes_manifest_row(repo: Path) -> None:
    (repo / "old_junk.log").write_text("j")
    date = "2026-07-13"
    trash_rel = tu.relocate(repo, "old_junk.log", date)
    tu.note_manifest(repo, date, "brush-junk", "old_junk.log", trash_rel)
    assert (repo / trash_rel).is_file()
    row = (repo / "dev/local/.trash/manifest.tsv").read_text().strip().split("\t")
    assert row == [date, "brush-junk", "old_junk.log", trash_rel]


def test_tracked_junk_pathspec_finds_nested(repo: Path) -> None:
    p = repo / "charts/sub/.DS_Store"
    p.parent.mkdir(parents=True)
    p.write_text("x")
    _git(repo, "add", "-f", "charts/sub/.DS_Store")
    _git(repo, "commit", "-qm", "junk")
    out = subprocess.run(
        ["git", "-C", str(repo), "ls-files", "-z", "--",
         ".DS_Store", "**/.DS_Store", "Thumbs.db", "**/Thumbs.db", "*.pyc"],
        capture_output=True, text=True, check=True).stdout
    assert "charts/sub/.DS_Store" in out.split("\0")


def test_veto_devlocal_protected_through_a_dotdot_segment(repo: Path) -> None:
    p = repo / "dev/local/keep.bin"
    p.parent.mkdir(parents=True)
    p.write_text("k")
    os.utime(p, (OLD, OLD))
    (repo / "sub").mkdir()

    assert "protected" in _veto(repo, "sub/../dev/local/keep.bin")


def test_main_refuses_a_protected_path_spelled_through_dotdot(
        repo: Path, monkeypatch: pytest.MonkeyPatch,
        capsys: pytest.CaptureFixture[str]) -> None:
    p = repo / "dev/local/keep.bin"
    p.parent.mkdir(parents=True)
    p.write_text("k")
    os.utime(p, (OLD, OLD))
    (repo / "sub").mkdir()

    monkeypatch.setattr(
        "sys.argv",
        ["trash_untracked.py", "--repo", str(repo),
         "sub/../dev/local/keep.bin"])
    tu.main()
    out = json.loads(capsys.readouterr().out)

    assert out["moved"] == []
    assert out["refused"] == [{
        "path": "dev/local/keep.bin",
        "reason": "protected path (dev/local, docs, .git)",
    }]
    assert p.exists()


def test_manifest_row_names_the_file_that_was_moved(
        repo: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    (repo / "old_junk.log").write_text("j")
    os.utime(repo / "old_junk.log", (OLD, OLD))
    (repo / "sub").mkdir()

    monkeypatch.setattr(
        "sys.argv",
        ["trash_untracked.py", "--repo", str(repo), "sub/../old_junk.log"])
    tu.main()

    row = (repo / "dev/local/.trash/manifest.tsv").read_text().strip().split("\t")
    assert row[2] == "old_junk.log"
    assert (repo / row[3]).is_file()


def test_a_tracked_nested_file_is_refused_by_its_slash_form_name(
        repo: Path) -> None:
    """`git ls-files` spells a nested entry with slashes on every host."""
    p = repo / "charts" / "sub" / "kept.log"
    p.parent.mkdir(parents=True)
    p.write_text("x")
    _git(repo, "add", "charts/sub/kept.log")
    _git(repo, "commit", "-qm", "nested")
    os.utime(p, (OLD, OLD))

    rel = tu.as_git_rel(repo, p)

    assert rel == "charts/sub/kept.log"
    assert "tracked" in _veto(repo, rel)


def test_an_untracked_nested_file_of_the_same_shape_is_permitted(
        repo: Path) -> None:
    p = repo / "charts" / "sub" / "old_junk.log"
    p.parent.mkdir(parents=True)
    p.write_text("j")
    os.utime(p, (OLD, OLD))

    rel = tu.as_git_rel(repo, p)

    assert rel == "charts/sub/old_junk.log"
    assert _veto(repo, rel) is None


@pytest.mark.parametrize("parts", [
    ("dev", "local", "keep.bin"),
    ("docs", "keep.bin"),
    (".git", "keep.bin"),
    ("dev", "local", "old_junk.log"),
    ("docs", "old_junk.log"),
])
def test_veto_refuses_each_protected_prefix_by_slash_form_identity(
        repo: Path, parts: tuple[str, ...]) -> None:
    p = repo.joinpath(*parts)
    p.parent.mkdir(parents=True, exist_ok=True)
    p.write_text("k")
    os.utime(p, (OLD, OLD))

    rel = tu.as_git_rel(repo, p)

    assert rel == "/".join(parts)
    assert "protected path" in _veto(repo, rel)


@pytest.mark.parametrize("parts", [
    ("dev", "tools", "old_junk.log"),
    ("guides", "old_junk.log"),
    ("dev", "tools", "keep.bin"),
    ("guides", "keep.bin"),
])
def test_veto_permits_a_sibling_directory_of_a_protected_prefix(
        repo: Path, parts: tuple[str, ...]) -> None:
    p = repo.joinpath(*parts)
    p.parent.mkdir(parents=True)
    p.write_text("j")
    os.utime(p, (OLD, OLD))

    rel = tu.as_git_rel(repo, p)

    assert rel == "/".join(parts)
    assert _veto(repo, rel) is None


def test_normalise_rel_reads_a_backslash_as_a_separator_only_on_nt(
        monkeypatch: pytest.MonkeyPatch) -> None:
    """Windows spells a separator there; POSIX spells a name character."""
    monkeypatch.setattr(tu.os, "name", "nt")

    assert tu.normalise_rel(r"dev\local\keep.bin") == "dev/local/keep.bin"
    assert tu.normalise_rel(r"sub\..\old_junk.log") == "old_junk.log"

    monkeypatch.setattr(tu.os, "name", "posix")

    assert tu.normalise_rel(r"dev\local\keep.bin") == r"dev\local\keep.bin"
    assert tu.normalise_rel(r"sub/../a\b.log") == r"a\b.log"


def test_normalise_rel_resolves_dot_and_dotdot_to_the_plain_name() -> None:
    assert tu.normalise_rel(
        "sub/../dev/local/keep.bin") == "dev/local/keep.bin"
    assert tu.normalise_rel("./sub/./../old_junk.log") == "old_junk.log"


def test_main_refuses_a_protected_path_that_contains_spaces(
        repo: Path, monkeypatch: pytest.MonkeyPatch,
        capsys: pytest.CaptureFixture[str]) -> None:
    p = repo / "dev" / "local" / "keep me" / "notes copy.bin"
    p.parent.mkdir(parents=True)
    p.write_text("k")
    os.utime(p, (OLD, OLD))
    spelled = str(Path("dev") / "local" / "keep me" / "notes copy.bin")

    monkeypatch.setattr(
        "sys.argv",
        ["trash_untracked.py", "--repo", str(repo), spelled])
    tu.main()
    out = json.loads(capsys.readouterr().out)

    assert out["moved"] == []
    assert out["refused"] == [{
        "path": "dev/local/keep me/notes copy.bin",
        "reason": "protected path (dev/local, docs, .git)",
    }]
    assert p.exists()


def test_main_reports_one_identity_for_a_moved_path_with_spaces(
        repo: Path, monkeypatch: pytest.MonkeyPatch,
        capsys: pytest.CaptureFixture[str]) -> None:
    """The report and the manifest name that file with one string."""
    p = repo / "old logs" / "run one.log"
    p.parent.mkdir(parents=True)
    p.write_text("j")
    os.utime(p, (OLD, OLD))
    (repo / "sub").mkdir()
    spelled = str(Path("sub") / ".." / "old logs" / "run one.log")

    monkeypatch.setattr(
        "sys.argv",
        ["trash_untracked.py", "--repo", str(repo), spelled])
    tu.main()
    out = json.loads(capsys.readouterr().out)

    row = (repo / "dev/local/.trash/manifest.tsv").read_text().strip().split("\t")
    assert out["refused"] == []
    assert out["moved"] == [{"path": "old logs/run one.log",
                             "trash": row[3]}]
    assert row[2] == "old logs/run one.log"
    assert row[3].startswith("dev/local/.trash/")
    assert (repo / row[3]).is_file()
    assert not p.exists()


def test_load_tracked_reads_the_index_in_slash_form(repo: Path) -> None:
    """The tracked set is git's spelling, nested entries included."""
    assert tu.load_tracked(repo) == {"tracked.log"}

    p = repo / "charts" / "sub" / "kept.log"
    p.parent.mkdir(parents=True)
    p.write_text("x")
    _git(repo, "add", "charts/sub/kept.log")
    _git(repo, "commit", "-qm", "nested")

    assert tu.load_tracked(repo) == {"tracked.log", "charts/sub/kept.log"}


def test_a_junk_named_file_that_git_tracks_is_still_refused(
        repo: Path) -> None:
    """The index decides, not the filename."""
    p = repo / "charts" / "sub" / "old_junk.log"
    p.parent.mkdir(parents=True)
    p.write_text("j")
    _git(repo, "add", "charts/sub/old_junk.log")
    _git(repo, "commit", "-qm", "junk-shaped")
    os.utime(p, (OLD, OLD))

    rel = tu.as_git_rel(repo, p)

    assert rel == "charts/sub/old_junk.log"
    assert "tracked" in _veto(repo, rel)


def test_an_untracked_file_named_like_a_tracked_one_is_permitted(
        repo: Path) -> None:
    p = repo / "charts" / "sub" / "kept.log"
    p.parent.mkdir(parents=True)
    p.write_text("j")
    os.utime(p, (OLD, OLD))

    rel = tu.as_git_rel(repo, p)

    assert rel == "charts/sub/kept.log"
    assert _veto(repo, rel) is None


def test_as_git_rel_spells_a_deep_path_under_a_root_of_any_name(
        tmp_path: Path) -> None:
    root = tmp_path / "workspace"
    p = root / "charts" / "deep" / "nested" / "old logs" / "run one.log"
    p.parent.mkdir(parents=True)
    p.write_text("j")

    assert tu.as_git_rel(root, p) == (
        "charts/deep/nested/old logs/run one.log")


def test_as_git_rel_spells_a_path_the_way_git_ls_files_prints_it(
        tmp_path: Path) -> None:
    """Git's representation is pinned to git, not to a literal."""
    root = tmp_path / "workspace"
    root.mkdir()
    _git(root, "init", "-q", "-b", "master")
    _git(root, "config", "user.email", "t@t")
    _git(root, "config", "user.name", "t")
    p = root / "charts" / "deep" / "nested" / "kept.log"
    p.parent.mkdir(parents=True)
    p.write_text("x")
    _git(root, "add", "charts/deep/nested/kept.log")

    printed = subprocess.run(
        ["git", "-C", str(root), "ls-files", "-z"],
        capture_output=True, text=True, check=True).stdout.split("\0")

    assert tu.as_git_rel(root, p) == printed[0]
    assert printed[0] == "charts/deep/nested/kept.log"


@pytest.mark.parametrize("os_name", ["nt", "posix"])
@pytest.mark.parametrize("rel", [
    "dev/local/",
    ".",
    "../old_junk.log",
    "sub/../../old_junk.log",
    "a//b/c",
    "a/b/../../c",
    "./sub/./../old_junk.log",
])
def test_normalise_rel_resolves_slash_input_like_posix_normpath(
        rel: str, os_name: str, monkeypatch: pytest.MonkeyPatch) -> None:
    """Same segment arithmetic on every host, slash form out."""
    monkeypatch.setattr(tu.os, "name", os_name)

    assert tu.normalise_rel(rel) == posixpath.normpath(rel)


@pytest.mark.parametrize("rel", [
    r"dev\local\keep.bin",
    r"sub\..\old_junk.log",
    r"a\\b\c",
    r"a\b\..\..\c",
    r"..\old_junk.log",
    r"charts\sub\.",
])
def test_normalise_rel_reads_a_backslash_as_a_separator_on_nt(
        rel: str, monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(tu.os, "name", "nt")

    assert tu.normalise_rel(rel) == posixpath.normpath(rel.replace("\\", "/"))


@pytest.mark.parametrize("rel", [
    r"dev\local\keep.bin",
    r"sub/../a\b.log",
    r"a\b\..\..\c",
    r"charts/sub/a\b/",
])
def test_normalise_rel_reads_a_backslash_as_a_name_character_on_posix(
        rel: str, monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(tu.os, "name", "posix")

    assert tu.normalise_rel(rel) == posixpath.normpath(rel)


def test_main_refuses_a_path_that_climbs_out_of_the_repository(
        repo: Path, monkeypatch: pytest.MonkeyPatch,
        capsys: pytest.CaptureFixture[str]) -> None:
    """A `..` that escapes the root is refused, and the file survives."""
    outside = repo.parent / "old_junk.log"
    outside.write_text("j")
    os.utime(outside, (OLD, OLD))

    monkeypatch.setattr(
        "sys.argv",
        ["trash_untracked.py", "--repo", str(repo), "../old_junk.log"])
    tu.main()
    out = json.loads(capsys.readouterr().out)

    assert out["moved"] == []
    assert len(out["refused"]) == 1
    assert "outside repo" in out["refused"][0]["reason"]
    assert outside.is_file()
