"""Tests for sweep.py: report path resolution (same-day same-reason reports)."""
import datetime

import sweep
from sweep_test_helpers import _make_repo, _plant_matches, _write_registry


# -- _resolve_report_path: same-day same-reason reports never overwrite -----


_SAME_REASON = "Same Reason Twice"


def _default_report_path(cwd_path, suffix=""):
    """The default report path for `_SAME_REASON` today, with `suffix`
    (e.g. "-2") inserted before `.md`."""
    today = datetime.date.today().isoformat()
    return (
        cwd_path
        / "docs" / "dev" / "project-management" / "audit-results"
        / f"sweep-same-reason-twice-{today}{suffix}.md"
    )


def test_a_second_sweep_with_the_same_reason_on_the_same_day_gets_a_suffixed_report(
    tmp_path,
):
    cwd_path = tmp_path.resolve()
    first_report = _default_report_path(cwd_path)
    first_report.parent.mkdir(parents=True)
    first_report.write_text("first sweep report\n")

    result = sweep._resolve_report_path(cwd_path, None, _SAME_REASON)

    assert result.name.endswith("-2.md")
    assert result == _default_report_path(cwd_path, "-2")
    assert first_report.read_text() == "first sweep report\n"


def test_a_third_sweep_with_the_same_reason_on_the_same_day_gets_the_next_free_suffix(
    tmp_path,
):
    cwd_path = tmp_path.resolve()
    first_report = _default_report_path(cwd_path)
    first_report.parent.mkdir(parents=True)
    first_report.write_text("first sweep report\n")
    second_report = _default_report_path(cwd_path, "-2")
    second_report.write_text("second sweep report\n")

    result = sweep._resolve_report_path(cwd_path, "", _SAME_REASON)

    assert result.name.endswith("-3.md")
    assert result == _default_report_path(cwd_path, "-3")
    assert first_report.read_text() == "first sweep report\n"
    assert second_report.read_text() == "second sweep report\n"


def test_an_explicit_out_naming_an_existing_report_is_returned_unsuffixed(tmp_path):
    # The explicit --out points at the very file a default run would have
    # suffixed around; as given, it must be honoured (and later overwritten).
    cwd_path = tmp_path.resolve()
    existing_report = _default_report_path(cwd_path)
    existing_report.parent.mkdir(parents=True)
    existing_report.write_text("earlier report\n")

    result = sweep._resolve_report_path(cwd_path, str(existing_report), _SAME_REASON)

    assert result == existing_report


def test_a_fourth_sweep_with_the_same_reason_on_the_same_day_looks_past_the_third_suffix(
    tmp_path,
):
    cwd_path = tmp_path.resolve()
    first_report = _default_report_path(cwd_path)
    first_report.parent.mkdir(parents=True)
    first_report.write_text("first sweep report\n")
    _default_report_path(cwd_path, "-2").write_text("second sweep report\n")
    third_report = _default_report_path(cwd_path, "-3")
    third_report.write_text("third sweep report\n")

    result = sweep._resolve_report_path(cwd_path, None, _SAME_REASON)

    assert result == _default_report_path(cwd_path, "-4")
    assert third_report.read_text() == "third sweep report\n"


def test_a_gap_in_the_suffix_chain_is_filled_with_the_first_free_suffix(tmp_path):
    # Base and -3 exist, -2 does not: the first FREE suffix from 2 is -2.
    # A count-based suffix would land on -3 and overwrite it.
    cwd_path = tmp_path.resolve()
    first_report = _default_report_path(cwd_path)
    first_report.parent.mkdir(parents=True)
    first_report.write_text("first sweep report\n")
    third_report = _default_report_path(cwd_path, "-3")
    third_report.write_text("third sweep report\n")

    result = sweep._resolve_report_path(cwd_path, None, _SAME_REASON)

    assert result == _default_report_path(cwd_path, "-2")
    assert first_report.read_text() == "first sweep report\n"
    assert third_report.read_text() == "third sweep report\n"


def test_reports_for_another_reason_or_another_day_do_not_raise_the_suffix(tmp_path):
    cwd_path = tmp_path.resolve()
    first_report = _default_report_path(cwd_path)
    first_report.parent.mkdir(parents=True)
    first_report.write_text("first sweep report\n")
    today = datetime.date.today()
    yesterday = (today - datetime.timedelta(days=1)).isoformat()
    report_dir = first_report.parent
    (report_dir / f"sweep-other-{today.isoformat()}.md").write_text("other\n")
    (report_dir / f"sweep-same-reason-twice-{yesterday}.md").write_text("old\n")

    result = sweep._resolve_report_path(cwd_path, None, _SAME_REASON)

    assert result == _default_report_path(cwd_path, "-2")


def test_a_same_reason_report_from_another_day_leaves_todays_path_unsuffixed(
    tmp_path,
):
    cwd_path = tmp_path.resolve()
    report_dir = _default_report_path(cwd_path).parent
    report_dir.mkdir(parents=True)
    yesterday = (datetime.date.today() - datetime.timedelta(days=1)).isoformat()
    yesterdays_report = report_dir / f"sweep-same-reason-twice-{yesterday}.md"
    yesterdays_report.write_text("yesterday's sweep report\n")

    result = sweep._resolve_report_path(cwd_path, None, _SAME_REASON)

    assert result == _default_report_path(cwd_path)
    assert yesterdays_report.read_text() == "yesterday's sweep report\n"


def test_a_relative_explicit_out_naming_an_existing_report_is_returned_unsuffixed(
    tmp_path,
):
    cwd_path = tmp_path.resolve()
    existing_report = _default_report_path(cwd_path)
    existing_report.parent.mkdir(parents=True)
    existing_report.write_text("earlier report\n")
    relative_out = str(existing_report.relative_to(cwd_path))
    assert not relative_out.startswith("/")

    result = sweep._resolve_report_path(cwd_path, relative_out, _SAME_REASON)

    assert result == existing_report


# -- main: two same-reason sweeps on one day write two reports --------------


def test_two_default_out_sweeps_with_the_same_reason_on_one_day_write_two_reports(
    tmp_path, monkeypatch
):
    empty_portfolio_root = tmp_path / "empty_portfolio_root"
    empty_portfolio_root.mkdir()
    monkeypatch.setattr(sweep, "PORTFOLIO_ROOT", empty_portfolio_root)

    repo_a = _make_repo(tmp_path / "org" / "repo-a")
    _plant_matches(repo_a, "TWOREPORTSMARKER", 1)
    control_repo = tmp_path / "control"
    control_repo.mkdir()
    (control_repo / "file.txt").write_text("TWOREPORTSMARKER control line\n")
    registry = tmp_path / "repos.csv"
    _write_registry(registry, [str(repo_a)])
    argv = [
        "--kind", "rg",
        "--pattern", "TWOREPORTSMARKER",
        "--reason", _SAME_REASON,
        "--control-term", "TWOREPORTSMARKER",
        "--control-repo", str(control_repo),
        "--registry", str(registry),
        "--cwd", str(repo_a),
    ]
    report_dir = _default_report_path(repo_a).parent

    assert sweep.main(argv) == 0
    first_reports = list(report_dir.glob("sweep-*.md"))
    assert len(first_reports) == 1
    first_report = first_reports[0]
    first_text = first_report.read_text()

    _plant_matches(repo_a, "TWOREPORTSMARKER", 2)  # second run sees 2 hits
    assert sweep.main(argv) == 0

    reports = sorted(report_dir.glob("sweep-*.md"))
    assert len(reports) == 2, reports
    assert first_report.read_text() == first_text
    second_report = next(r for r in reports if r != first_report)
    assert second_report.read_text() != first_text
