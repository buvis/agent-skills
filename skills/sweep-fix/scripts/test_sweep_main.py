"""Tests for sweep.py: main (CLI end-to-end)."""
import re
import time
from pathlib import Path

import pytest

import sweep
from sweep_test_helpers import (
    _git_status_porcelain,
    _init_git_repo_with_tracked_files,
    _make_repo,
    _plant_matches,
    _write_registry,
)


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

    expected_dir = repo_a / "docs" / "dev" / "project-management" / "audit-results"
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
    assert str(target) in message


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
    nested_out = repo_a / "docs" / "dev" / "project-management" / "audit-results" / "nested-report.md"
    argv[out_index + 1] = str(nested_out)

    exit_code = sweep.main(argv)

    assert exit_code == 0
    assert nested_out.exists()
    assert nested_out.read_text().strip() != ""


def test_a_refused_out_path_creates_no_report_directory(tmp_path, monkeypatch):
    argv, (_repo_a, _repo_b, _repo_c), _scaffold_out_path = _build_sweep_main_scaffold(
        tmp_path, monkeypatch, "NODIRCREATEDMARKER", _make_repo
    )
    out_index = argv.index("--out")
    argv[out_index + 1] = str(tmp_path / "outside" / "report.md")

    with pytest.raises(SystemExit):
        sweep.main(argv)

    assert (tmp_path / "outside").exists() is False


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

    expected_dir = repo_a / "docs" / "dev" / "project-management" / "audit-results"
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
    assert "--cap must be a positive integer" in (captured.out + captured.err).lower()


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
    assert "--cap must be a positive integer" in (captured.out + captured.err).lower()


def test_main_rejects_a_deadline_of_zero(tmp_path, monkeypatch, capsys):
    argv, (_repo_a, _repo_b, _repo_c), out_path = _build_sweep_main_scaffold(
        tmp_path, monkeypatch, "ZERODEADLINEMARKER", _make_repo
    )
    argv += ["--deadline", "0"]

    with pytest.raises(SystemExit) as exc_info:
        sweep.main(argv)

    assert exc_info.value.code != 0
    assert not out_path.exists()
    captured = capsys.readouterr()
    assert "--deadline must be a positive integer" in (
        captured.out + captured.err
    ).lower()


def test_main_rejects_a_negative_deadline(tmp_path, monkeypatch, capsys):
    argv, (_repo_a, _repo_b, _repo_c), out_path = _build_sweep_main_scaffold(
        tmp_path, monkeypatch, "NEGATIVEDEADLINEMARKER", _make_repo
    )
    argv += ["--deadline", "-1"]

    with pytest.raises(SystemExit) as exc_info:
        sweep.main(argv)

    assert exc_info.value.code != 0
    assert not out_path.exists()
    captured = capsys.readouterr()
    assert "--deadline must be a positive integer" in (
        captured.out + captured.err
    ).lower()


def test_main_passes_deadline_through_to_scan(tmp_path, monkeypatch):
    # The spy finds no hits, so main() would run verify_control, which calls
    # scan() itself; stub it out so the spy sees only main()'s own scan call.
    monkeypatch.setattr(sweep, "verify_control", lambda *a, **k: None)

    def _run_main_and_record_deadlines(root, marker, extra_argv):
        root.mkdir()
        argv, _repos, out_path = _build_sweep_main_scaffold(
            root, monkeypatch, marker, _make_repo
        )
        deadlines = []

        def _spy_scan(*args, **kwargs):
            deadlines.append(kwargs.get("deadline", "<not passed>"))
            return [], {}, {}

        monkeypatch.setattr(sweep, "scan", _spy_scan)
        exit_code = sweep.main(argv + extra_argv)
        assert exit_code == 0
        assert out_path.exists()
        return deadlines

    with_flag = _run_main_and_record_deadlines(
        tmp_path / "with-flag", "DEADLINEWIREMARKER", ["--deadline", "5"]
    )
    assert with_flag == [5]

    without_flag = _run_main_and_record_deadlines(
        tmp_path / "without-flag", "NODEADLINEWIREMARKER", []
    )
    assert len(without_flag) == 1
    assert without_flag[0] is None


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


def test_an_out_path_outside_the_cwd_repo_is_refused_before_any_repo_is_scanned(
    tmp_path, monkeypatch
):
    argv, _repos, _out_path = _build_sweep_main_scaffold(
        tmp_path, monkeypatch, "OUTFENCEMARKER", _make_repo
    )
    argv[argv.index("--out") + 1] = str(tmp_path / "outside" / "report.md")

    scans = []
    monkeypatch.setattr(sweep, "scan", lambda *a, **k: scans.append(a) or ([], [], []))

    with pytest.raises(SystemExit):
        sweep.main(argv)

    assert scans == []


# -- main: setup failures exit 1 with one stderr line and no report ---------


def _zero_hit_argv(tmp_path, monkeypatch, control_repo, control_term):
    """One registered repo with no pattern hits, so the whole sweep finds
    zero hits and main() must run the control check. The report would land
    in a not-yet-existing `reports/` directory inside the repo."""
    empty_portfolio_root = tmp_path / "empty_portfolio_root"
    empty_portfolio_root.mkdir()
    monkeypatch.setattr(sweep, "PORTFOLIO_ROOT", empty_portfolio_root)

    repo_a = _make_repo(tmp_path / "org" / "repo-a")
    (repo_a / "file.txt").write_text("nothing relevant here\n")

    registry = tmp_path / "repos.csv"
    _write_registry(registry, [str(repo_a)])

    out_path = repo_a / "reports" / "report.md"
    argv = [
        "--kind", "rg",
        "--pattern", "ZEROHITPATTERN",
        "--reason", "regression test for fail-loud setup",
        "--control-term", control_term,
        "--control-repo", str(control_repo),
        "--registry", str(registry),
        "--cwd", str(repo_a),
        "--out", str(out_path),
    ]
    return argv, out_path


@pytest.mark.parametrize(
    ("kind", "resolver_name", "tool_name"),
    [("rg", "resolve_rg", "rg"), ("astgrep", "resolve_ast_grep", "ast-grep")],
)
def test_an_unresolvable_scan_tool_exits_one_and_writes_no_report(
    tmp_path, monkeypatch, capsys, kind, resolver_name, tool_name
):
    argv, (repo_a, _repo_b, _repo_c), _scaffold_out_path = _build_sweep_main_scaffold(
        tmp_path, monkeypatch, "UNRESOLVABLETOOLMARKER", _make_repo
    )
    argv[argv.index("--kind") + 1] = kind
    out_path = repo_a / "reports" / "report.md"
    argv[argv.index("--out") + 1] = str(out_path)

    def _unresolvable():
        raise RuntimeError(f"Could not resolve {tool_name}: not found on PATH")

    monkeypatch.setattr(sweep, resolver_name, _unresolvable)
    scans = []
    monkeypatch.setattr(sweep, "scan", lambda *a, **k: scans.append(a) or ([], [], []))

    exit_code = sweep.main(argv)

    assert exit_code == 1
    assert scans == []
    assert not out_path.exists()
    assert not out_path.parent.exists()
    err_lines = capsys.readouterr().err.strip().splitlines()
    assert len(err_lines) == 1
    assert f"Could not resolve {tool_name}" in err_lines[0]
    assert "not found on PATH" in err_lines[0]


@pytest.mark.parametrize(
    ("kind", "unneeded_resolver_name"),
    [("rg", "resolve_ast_grep"), ("astgrep", "resolve_rg")],
)
def test_a_sweep_does_not_need_the_scan_tool_of_the_other_kind(
    tmp_path, monkeypatch, kind, unneeded_resolver_name
):
    argv, repos, out_path = _build_sweep_main_scaffold(
        tmp_path, monkeypatch, "OTHERTOOLMARKER", _make_repo
    )
    argv[argv.index("--kind") + 1] = kind
    for repo in repos:
        _plant_matches(repo, "OTHERTOOLMARKER", 1, ext=".py")

    def _unresolvable():
        raise RuntimeError("Could not resolve the other tool: not found on PATH")

    monkeypatch.setattr(sweep, unneeded_resolver_name, _unresolvable)

    exit_code = sweep.main(argv)

    assert exit_code == 0
    assert out_path.exists()
    assert "OTHERTOOLMARKER" in out_path.read_text()


def test_an_invalid_out_is_refused_before_the_scan_tool_is_resolved(
    tmp_path, monkeypatch, capsys
):
    argv, _repos, _out_path = _build_sweep_main_scaffold(
        tmp_path, monkeypatch, "OUTBEFORETOOLMARKER", _make_repo
    )
    outside_out = tmp_path / "outside" / "report.md"
    argv[argv.index("--out") + 1] = str(outside_out)

    resolver_calls = []

    def _unresolvable():
        resolver_calls.append(True)
        raise RuntimeError("Could not resolve rg: not found on PATH")

    monkeypatch.setattr(sweep, "resolve_rg", _unresolvable)

    with pytest.raises(SystemExit) as exc_info:
        sweep.main(argv)

    assert exc_info.value.code == 1
    assert resolver_calls == []
    assert not outside_out.parent.exists()
    message = capsys.readouterr().err
    assert str(outside_out) in message
    assert "Could not resolve" not in message


def test_a_failed_control_search_exits_one(tmp_path, monkeypatch, capsys):
    control_repo = tmp_path / "control"
    control_repo.mkdir()
    (control_repo / "file.txt").write_text("unrelated control content\n")
    argv, out_path = _zero_hit_argv(
        tmp_path, monkeypatch, control_repo, "FAILEDSEARCHTERM"
    )

    original_run_rg = sweep._run_rg

    def _fail_fixed_string_search(args, *rest, **kwargs):
        if "-F" in args:
            raise RuntimeError("rg failed: line one\nline two")
        return original_run_rg(args, *rest, **kwargs)

    monkeypatch.setattr(sweep, "_run_rg", _fail_fixed_string_search)

    exit_code = sweep.main(argv)

    assert exit_code == 1
    assert not out_path.exists()
    assert not out_path.parent.exists()
    err_lines = capsys.readouterr().err.strip().splitlines()
    assert len(err_lines) == 1
    assert "sweep unverified" in err_lines[0]
    assert str(control_repo) in err_lines[0]
    assert "line one line two" in err_lines[0]


def test_a_control_repo_whose_pattern_scan_fails_exits_one_with_one_stderr_line(
    tmp_path, monkeypatch, capsys
):
    # The control repo exists, but scanning it for the pattern blows up with
    # multi-line error text. That is a failed control check, not "no hits",
    # and the reason must reach stderr collapsed onto one line.
    control_repo = tmp_path / "control"
    control_repo.mkdir()
    (control_repo / "file.txt").write_text("unrelated control content\n")
    argv, out_path = _zero_hit_argv(
        tmp_path, monkeypatch, control_repo, "SCANFAILCONTROLTERM"
    )

    original_run_rg = sweep._run_rg

    def _fail_control_pattern_scan(args, cwd, *rest, **kwargs):
        if "-F" not in args and Path(cwd).resolve() == control_repo.resolve():
            raise RuntimeError("rg failed: a\nb")
        return original_run_rg(args, cwd, *rest, **kwargs)

    monkeypatch.setattr(sweep, "_run_rg", _fail_control_pattern_scan)

    exit_code = sweep.main(argv)

    assert exit_code == 1
    assert not out_path.exists()
    assert not out_path.parent.exists()
    err_lines = capsys.readouterr().err.strip().splitlines()
    assert len(err_lines) == 1
    assert "could not be scanned" in err_lines[0]
    assert str(control_repo) in err_lines[0]


def test_an_unscannable_control_repo_exits_one_and_writes_no_report(
    tmp_path, monkeypatch, capsys
):
    control_repo = tmp_path / "control-does-not-exist"
    argv, out_path = _zero_hit_argv(
        tmp_path, monkeypatch, control_repo, "MISSINGCONTROLTERM"
    )

    exit_code = sweep.main(argv)

    assert exit_code == 1
    assert not out_path.exists()
    assert not out_path.parent.exists()
    err_lines = capsys.readouterr().err.strip().splitlines()
    assert len(err_lines) == 1
    assert "could not be scanned" in err_lines[0]
    assert str(control_repo) in err_lines[0]


def test_a_missing_registry_exits_one_naming_the_path(
    tmp_path, monkeypatch, capsys
):
    argv, (repo_a, _repo_b, _repo_c), _scaffold_out_path = _build_sweep_main_scaffold(
        tmp_path, monkeypatch, "MISSINGREGISTRYMARKER", _make_repo
    )
    missing_registry = str(tmp_path / "no-such-repos.csv")
    argv[argv.index("--registry") + 1] = missing_registry
    out_path = repo_a / "reports" / "report.md"
    argv[argv.index("--out") + 1] = str(out_path)

    with pytest.raises(RuntimeError) as exc_info:
        sweep.enumerate_repos(missing_registry, repo_a)
    assert str(exc_info.value) == f"registry not found: {missing_registry}"

    exit_code = sweep.main(argv)

    assert exit_code == 1
    assert not out_path.exists()
    assert not out_path.parent.exists()
    assert capsys.readouterr().err.strip() == f"registry not found: {missing_registry}"
