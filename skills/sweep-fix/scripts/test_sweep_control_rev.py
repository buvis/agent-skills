"""Tests for sweep.py: --control-rev, the control check on a fix's pre-image."""
import subprocess
import time
from pathlib import Path

import pytest

import sweep
import sweep_preimage
from sweep_test_helpers import _write_registry

_GIT_IDENTITY = [
    "-c", "user.name=Sweep Test",
    "-c", "user.email=sweep-test@example.invalid",
    "-c", "commit.gpgsign=false",
]
_BUG = "result = eval(raw)\n"
_FIXED = "result = safe_parse(raw)\n"
_PATTERN = r"\beval\("
_CONTROL_TERM = "eval(raw)"


def _git(repo, *args):
    return subprocess.run(
        ["git", *_GIT_IDENTITY, "-C", str(repo), *args],
        check=True,
        capture_output=True,
        text=True,
    ).stdout


def _commit(repo, files, message):
    for rel, text in files.items():
        path = repo / rel
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(text, newline="\n")
    _git(repo, "add", "-A")
    _git(repo, "commit", "-q", "-m", message)
    return _git(repo, "rev-parse", "HEAD").strip()


def _new_repo(tmp_path):
    repo = tmp_path / "org" / "fixed"
    repo.mkdir(parents=True)
    _git(repo, "init", "-q")
    return repo


def _fixed_repo(tmp_path, fix_files=None):
    """A repo whose HEAD is the fix: `app.py` loses the bug, and the fix
    also writes `fix_files`. Returns `(repo, first commit)`."""
    repo = _new_repo(tmp_path)
    first = _commit(repo, {"app.py": _BUG, "notes.txt": "notes\n"}, "add app")
    _commit(repo, {"app.py": _FIXED, **(fix_files or {})}, "fix app")
    return repo, first


@pytest.fixture
def sweep_argv(tmp_path, monkeypatch):
    """Build argv for a sweep of `repo` alone, with `repo` as the control."""
    empty_portfolio_root = tmp_path / "empty_portfolio_root"
    empty_portfolio_root.mkdir()
    monkeypatch.setattr(sweep, "PORTFOLIO_ROOT", empty_portfolio_root)

    def build(repo, pattern=_PATTERN, control_term=_CONTROL_TERM, rev="HEAD", deadline=60):
        registry = tmp_path / "repos.csv"
        _write_registry(registry, [str(repo)])
        out_path = repo / "reports" / "report.md"
        argv = [
            "--kind", "rg",
            "--pattern", pattern,
            "--reason", "regression test for the pre-image control check",
            "--control-term", control_term,
            "--control-repo", str(repo),
            "--registry", str(registry),
            "--cwd", str(repo),
            "--out", str(out_path),
            "--deadline", str(deadline),
        ]
        if rev is not None:
            argv += ["--control-rev", rev]
        return argv, out_path

    return build


@pytest.fixture
def export_dests(monkeypatch):
    """Record every directory the pre-image is exported to."""
    dests = []
    real_export = sweep._export_preimage

    def recording_export(repo, rev, dest, deadline_at):
        dests.append(dest)
        real_export(repo, rev, dest, deadline_at)

    monkeypatch.setattr(sweep, "_export_preimage", recording_export)
    return dests


def _run_main(argv):
    """`sweep.main(argv)`'s exit code, whether it returns or exits."""
    try:
        return sweep.main(argv)
    except SystemExit as exc:
        return exc.code


def test_zero_hit_sweep_verified_against_the_fix_preimage_exits_zero(tmp_path, sweep_argv):
    repo, _first = _fixed_repo(tmp_path)
    argv, out_path = sweep_argv(repo)

    exit_code = sweep.main(argv)

    assert exit_code == 0
    report = out_path.read_text()
    assert "Hits (0):" in report
    assert "Unverified:" not in report


def test_preimage_of_a_merge_commit_comes_from_its_first_parent(tmp_path, sweep_argv):
    # The fix lands on a side branch and is merged with --no-ff. Against its
    # first parent the merge changed app.py, which still held the bug there.
    # Against the second parent it changed only notes.txt, so a pre-image
    # taken from that side would hold no bug and the sweep would not verify.
    repo = _new_repo(tmp_path)
    _commit(repo, {"app.py": _BUG, "notes.txt": "notes\n"}, "add app")
    main_branch = _git(repo, "rev-parse", "--abbrev-ref", "HEAD").strip()
    _git(repo, "checkout", "-q", "-b", "fix")
    _commit(repo, {"app.py": _FIXED}, "fix app")
    _git(repo, "checkout", "-q", main_branch)
    _commit(repo, {"notes.txt": "more notes\n"}, "edit notes")
    _git(repo, "merge", "-q", "--no-ff", "-m", "merge fix", "fix")
    argv, out_path = sweep_argv(repo)

    exit_code = sweep.main(argv)

    assert exit_code == 0
    assert "Unverified:" not in out_path.read_text()


def test_preimage_with_control_term_but_no_pattern_match_aborts_as_broken_pattern(
    tmp_path, sweep_argv, capsys
):
    # `\|` is a literal pipe in rg's regex, so this pattern misses the bug
    # the control term proves is in the pre-image.
    repo, _first = _fixed_repo(tmp_path)
    argv, out_path = sweep_argv(repo, pattern=r"eval\(raw\)\|exec")

    with pytest.raises(SystemExit) as exc_info:
        sweep.main(argv)

    assert exc_info.value.code == 1
    assert not out_path.exists()
    err_lines = capsys.readouterr().err.splitlines()
    assert len(err_lines) == 1
    assert err_lines[0].startswith("sweep unverified: ")
    assert _CONTROL_TERM in err_lines[0]
    assert f"the pre-image of HEAD in {repo}" in err_lines[0]


def test_preimage_without_pattern_or_control_term_saves_an_unverified_report(
    tmp_path, sweep_argv
):
    # The control term lives only in a file the fix added. An added file has
    # no pre-image, so the pre-image holds neither the pattern nor the term.
    # Checked against the live tree instead, the term would be present and
    # the sweep would abort as a broken pattern.
    repo, _first = _fixed_repo(tmp_path, {"guard.py": "GUARDTERM = True\n"})
    argv, out_path = sweep_argv(repo, pattern="NEVERPRESENTPATTERN", control_term="GUARDTERM")

    exit_code = sweep.main(argv)

    assert exit_code == 1
    assert "Unverified: control term not found" in out_path.read_text().splitlines()


def _sleep_past_the_deadline_after_export(monkeypatch):
    real_export = sweep._export_preimage

    def slow_export(repo, rev, dest, deadline_at):
        real_export(repo, rev, dest, deadline_at)
        time.sleep(max(deadline_at - time.monotonic(), 0) + 0.1)

    monkeypatch.setattr(sweep, "_export_preimage", slow_export)


@pytest.mark.parametrize(
    ("case", "expected_code", "report_saved"),
    [
        ("verified", 0, True),
        ("unverified", 1, True),
        ("broken-pattern", 1, False),
        ("unusable-rev", 1, False),
        ("deadline-expired", 1, False),
    ],
)
def test_preimage_export_leaves_no_temporary_directory_on_any_exit_path(
    tmp_path, sweep_argv, export_dests, monkeypatch, capsys, case, expected_code, report_saved
):
    repo, _first = _fixed_repo(tmp_path)
    kwargs = {
        "unverified": {"pattern": "NEVERPRESENTPATTERN", "control_term": "ABSENTTERM"},
        "broken-pattern": {"pattern": "NEVERPRESENTPATTERN"},
        "unusable-rev": {"rev": "no-such-rev"},
        "deadline-expired": {"deadline": 3},
    }.get(case, {})
    if case == "deadline-expired":
        # The export's own time is charged to --deadline: nothing is left
        # for the control check once it returns, so the sweep must refuse.
        _sleep_past_the_deadline_after_export(monkeypatch)
    argv, out_path = sweep_argv(repo, **kwargs)

    exit_code = _run_main(argv)

    assert exit_code == expected_code
    assert out_path.exists() is report_saved
    if case == "deadline-expired":
        assert "deadline expired" in capsys.readouterr().err
    assert len(export_dests) == 1
    dest = Path(export_dests[0])
    assert not dest.exists()
    assert not dest.resolve().is_relative_to(repo.resolve())


def test_preimage_export_stops_once_the_deadline_has_passed(tmp_path):
    repo, _first = _fixed_repo(tmp_path)
    dest = tmp_path / "preimage"
    dest.mkdir()

    with pytest.raises(subprocess.TimeoutExpired):
        sweep_preimage._export_preimage(repo, "HEAD", dest, time.monotonic() - 1)

    assert list(dest.iterdir()) == []


@pytest.mark.parametrize("temp_repo", ["control", "other"])
def test_preimage_refuses_a_temporary_root_inside_a_swept_repo(
    tmp_path, sweep_argv, monkeypatch, capsys, temp_repo
):
    repo, _first = _fixed_repo(tmp_path)
    other = tmp_path / "other"
    other.mkdir()
    _git(other, "init", "-q")
    argv, out_path = sweep_argv(repo)
    _write_registry(tmp_path / "repos.csv", [str(repo), str(other)])
    scratch = (repo if temp_repo == "control" else other) / "scratch"
    scratch.mkdir()
    monkeypatch.setattr(sweep.tempfile, "tempdir", str(scratch))

    assert sweep.main(argv) == 1
    assert not out_path.exists()
    assert list(scratch.iterdir()) == []
    assert "temporary pre-image directory is inside a swept repo" in capsys.readouterr().err


def _repo_state(repo):
    git_dir = repo / ".git"
    return {
        "index": (git_dir / "index").read_bytes(),
        "head": (git_dir / "HEAD").read_bytes(),
        "refs": _git(repo, "for-each-ref", "--format=%(refname) %(objectname)"),
        "status": _git(
            repo, "--no-optional-locks", "status", "--porcelain", "--untracked-files=no"
        ),
        "app": (repo / "app.py").read_bytes(),
    }


def test_preimage_export_does_not_change_the_control_repo(tmp_path, sweep_argv):
    repo, _first = _fixed_repo(tmp_path)
    argv, _out_path = sweep_argv(repo)
    before = _repo_state(repo)

    exit_code = sweep.main(argv)

    assert exit_code == 0
    assert _repo_state(repo) == before


@pytest.mark.parametrize("rev_kind", ["does-not-resolve", "has-no-parent"])
def test_unusable_control_rev_exits_one_with_one_stderr_line_and_no_report(
    tmp_path, sweep_argv, capsys, rev_kind
):
    repo, first = _fixed_repo(tmp_path)
    rev = "no-such-rev" if rev_kind == "does-not-resolve" else first
    argv, out_path = sweep_argv(repo, rev=rev)

    exit_code = sweep.main(argv)

    assert exit_code == 1
    assert not out_path.exists()
    err_lines = capsys.readouterr().err.splitlines()
    assert len(err_lines) == 1
    assert err_lines[0].startswith("sweep unverified: ")
    assert rev in err_lines[0]
    assert str(repo) in err_lines[0]


def test_sweep_without_control_rev_behaves_as_before(tmp_path, sweep_argv, monkeypatch):
    # Without the flag the live tree is the control: the fix removed the bug
    # from it, so the term is absent there too and the sweep stays unverified.
    def no_export(*args, **kwargs):
        raise AssertionError("no pre-image may be exported without --control-rev")

    monkeypatch.setattr(sweep, "_export_preimage", no_export)
    repo, _first = _fixed_repo(tmp_path)
    argv, out_path = sweep_argv(repo, rev=None)

    exit_code = sweep.main(argv)

    assert exit_code == 1
    assert "Unverified: control term not found" in out_path.read_text().splitlines()
