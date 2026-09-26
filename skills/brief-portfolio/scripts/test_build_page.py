"""Regression tests for build.py's payload injection and output placement.

Both cases were found by an agoge run on 2026-08-31. The tokenizer-injection
case is fixed (PRD 00011); the --out/--dir default case is fixed (PRD 00013).

Run: python3 -m pytest test_build_page.py -q
"""

import importlib.util
import json
import re
import subprocess
import sys
from pathlib import Path

# Loaded by path under a unique name rather than via sys.path: the repo carries
# a second, unrelated scripts/build.py under skills/debrief-meeting, and a plain
# `import build` would let whichever suite ran first win in sys.modules.
_spec = importlib.util.spec_from_file_location(
    "brief_portfolio_build", Path(__file__).parent / "build.py"
)
build = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(build)

_BUILD_SCRIPT = Path(__file__).parent / "build.py"


def _run_build_subprocess(args: list[str]) -> subprocess.CompletedProcess:
    """Run build.py as a real process, so stderr/exit code reflect what a user sees.

    build.main() exits via sys.exit(), which raises SystemExit without ever
    printing anything itself — only the interpreter's own unwind writes the
    message to stderr. Calling main() in-process only exposes the SystemExit
    value, not the actual stderr text or exit code, so decode-error contracts
    are checked against the real subprocess instead.
    """
    return subprocess.run(
        [sys.executable, str(_BUILD_SCRIPT), *args],
        capture_output=True,
        text=True,
        timeout=30,
    )


def _json_decode_error_text(malformed_json: str) -> str:
    """The exact json.JSONDecodeError text build.py embeds in its exit message."""
    try:
        json.loads(malformed_json)
    except json.JSONDecodeError as e:
        return str(e)
    raise AssertionError("fixture must be invalid JSON")


def _payload_of(page: str) -> str:
    """The exact text build.py substituted for the template's placeholder."""
    head, tail = build.TEMPLATE.read_text().split(build.PLACEHOLDER)
    assert page.startswith(head) and page.endswith(tail)
    return page[len(head) : len(page) - len(tail)]


def _workdir(tmp_path: Path, data: dict) -> Path:
    workdir = tmp_path / "work"
    workdir.mkdir()
    (workdir / "data.json").write_text(json.dumps(data))
    return workdir


def test_no_collected_text_can_reach_the_html_tokenizer(tmp_path, monkeypatch):
    workdir = _workdir(
        tmp_path,
        {"repos": [{"owner": "o", "name": "n", "org": "o", "title": "benign <!--<script> tail"}]},
    )
    out = tmp_path / "page.html"
    monkeypatch.setattr(sys, "argv", ["build.py", "--dir", str(workdir), "--out", str(out)])

    build.main()

    assert "<" not in _payload_of(out.read_text())


def test_dir_without_out_writes_the_page_beside_its_own_inputs(tmp_path, monkeypatch):
    workdir = _workdir(tmp_path, {"repos": []})
    home = tmp_path / "home"
    monkeypatch.setattr(Path, "home", classmethod(lambda cls: home))
    monkeypatch.setattr(sys, "argv", ["build.py", "--dir", str(workdir)])

    build.main()

    assert (workdir / "portfolio-brief.html").is_file()
    assert not (home / ".local/share/agents/portfolio-brief/portfolio-brief.html").exists()


def test_no_flags_writes_the_home_default(tmp_path, monkeypatch):
    home = tmp_path / "home"
    workdir = home / ".local/share/agents/portfolio-brief"
    workdir.mkdir(parents=True)
    (workdir / "data.json").write_text(json.dumps({"repos": []}))
    monkeypatch.setattr(Path, "home", classmethod(lambda cls: home))
    monkeypatch.setattr(sys, "argv", ["build.py"])

    build.main()

    assert (home / ".local/share/agents/portfolio-brief/portfolio-brief.html").is_file()


def test_a_torn_history_line_does_not_abort_the_build(tmp_path, monkeypatch, capsys):
    workdir = _workdir(tmp_path, {"repos": []})
    (workdir / "history.jsonl").write_text(
        '{"at": "2026-09-04T00:00:00+00:00", "skipped": 0, "repos": {}}\n{"at":'
    )
    out = tmp_path / "page.html"
    monkeypatch.setattr(sys, "argv", ["build.py", "--dir", str(workdir), "--out", str(out)])

    build.main()

    captured = capsys.readouterr()
    assert out.is_file()
    assert re.search(r"history\.jsonl line 2 skipped: .+", captured.err)
    history = json.loads(_payload_of(out.read_text()))["history"]
    assert len(history) == 1


def test_warn_names_the_physical_line_number_including_blank_lines(tmp_path, monkeypatch, capsys):
    workdir = _workdir(tmp_path, {"repos": []})
    history_text = "\n".join(
        [
            "",
            '{"at": "2026-09-01T00:00:00+00:00", "skipped": 0, "repos": {}}',
            "",
            '{"at": bad',
        ]
    )
    (workdir / "history.jsonl").write_text(history_text)
    out = tmp_path / "page.html"
    monkeypatch.setattr(sys, "argv", ["build.py", "--dir", str(workdir), "--out", str(out)])

    build.main()

    captured = capsys.readouterr()
    assert out.is_file()
    assert re.search(r"history\.jsonl line 4 skipped: .+", captured.err)


def test_a_malformed_line_outside_the_last_60_window_is_not_decoded_or_warned_about(
    tmp_path, monkeypatch, capsys
):
    # 61 physical lines: line 1 sits outside the last-60 window and must be
    # silently dropped; line 40 sits inside the window and must be skipped
    # with a warning naming its own physical line number. A fixture with only
    # the out-of-window defect would pass even with no skip-and-warn behavior
    # at all, since the selected tail would never touch a malformed line.
    workdir = _workdir(tmp_path, {"repos": []})
    valid_line = '{"at": "2026-09-01T00:00:00+00:00", "skipped": 0, "repos": {}}'
    lines = ['{"bad-out-of-window"'] + [valid_line] * 60
    lines[39] = '{"bad-in-window"'  # physical line 40, inside the last-60 window
    (workdir / "history.jsonl").write_text("\n".join(lines))
    out = tmp_path / "page.html"
    monkeypatch.setattr(sys, "argv", ["build.py", "--dir", str(workdir), "--out", str(out)])

    build.main()

    captured = capsys.readouterr()
    assert out.is_file()
    assert re.findall(r"history\.jsonl line (\d+) skipped:", captured.err) == ["40"]
    history = json.loads(_payload_of(out.read_text()))["history"]
    assert len(history) == 59


def test_multiple_torn_history_lines_are_each_skipped_independently(tmp_path, monkeypatch, capsys):
    workdir = _workdir(tmp_path, {"repos": []})
    lines = [
        '{"at": "2026-09-01T00:00:00+00:00", "skipped": 0, "repos": {}}',
        '{"at": "2026-09-02T00:00:00+00:00", "skipped":',
        '{"at": "2026-09-03T00:00:00+00:00", "skipped": 2, "repos": {}}',
        '{"at": bad',
    ]
    (workdir / "history.jsonl").write_text("\n".join(lines))
    out = tmp_path / "page.html"
    monkeypatch.setattr(sys, "argv", ["build.py", "--dir", str(workdir), "--out", str(out)])

    build.main()

    captured = capsys.readouterr()
    assert out.is_file()
    assert re.findall(r"history\.jsonl line (\d+) skipped:", captured.err) == ["2", "4"]
    history = json.loads(_payload_of(out.read_text()))["history"]
    assert len(history) == 2


def test_a_torn_history_line_yields_one_fewer_trend_point(tmp_path, monkeypatch, capsys):
    valid_lines = [
        '{"at": "2026-09-01T00:00:00+00:00", "skipped": 0, "repos": {}}',
        '{"at": "2026-09-02T00:00:00+00:00", "skipped": 1, "repos": {}}',
        '{"at": "2026-09-03T00:00:00+00:00", "skipped": 2, "repos": {}}',
    ]

    healthy_dir = _workdir(tmp_path, {"repos": []})
    (healthy_dir / "history.jsonl").write_text("\n".join(valid_lines))
    healthy_out = tmp_path / "healthy.html"
    monkeypatch.setattr(
        sys, "argv", ["build.py", "--dir", str(healthy_dir), "--out", str(healthy_out)]
    )
    build.main()
    healthy_history = json.loads(_payload_of(healthy_out.read_text()))["history"]

    torn_dir = tmp_path / "torn"
    torn_dir.mkdir()
    (torn_dir / "data.json").write_text(json.dumps({"repos": []}))
    torn_lines = list(valid_lines)
    torn_lines[1] = '{"at": "2026-09-02T00:00:00+00:00", "skipped":'
    (torn_dir / "history.jsonl").write_text("\n".join(torn_lines))
    torn_out = tmp_path / "torn.html"
    monkeypatch.setattr(sys, "argv", ["build.py", "--dir", str(torn_dir), "--out", str(torn_out)])
    build.main()

    captured = capsys.readouterr()
    torn_history = json.loads(_payload_of(torn_out.read_text()))["history"]
    assert re.search(r"history\.jsonl line 2 skipped: .+", captured.err)
    assert len(torn_history) == len(healthy_history) - 1


def test_a_truncated_data_json_exits_with_a_message_naming_the_file(tmp_path):
    workdir = tmp_path / "work"
    workdir.mkdir()
    malformed = '{"repos": [{"owner": "o", "name": '
    (workdir / "data.json").write_text(malformed)

    result = _run_build_subprocess(
        ["--dir", str(workdir), "--out", str(tmp_path / "page.html")]
    )

    assert result.returncode != 0
    assert "Traceback" not in result.stderr
    lines = result.stderr.strip("\n").splitlines()
    assert len(lines) == 1
    assert "data.json" in lines[0]
    assert _json_decode_error_text(malformed) in lines[0]


def test_an_invalid_epics_json_exits_with_a_message_naming_the_file(tmp_path):
    workdir = _workdir(tmp_path, {"repos": []})
    malformed = '{"summary": "x", "repos": {'
    (workdir / "epics.json").write_text(malformed)

    result = _run_build_subprocess(
        ["--dir", str(workdir), "--out", str(tmp_path / "page.html")]
    )

    assert result.returncode != 0
    assert "Traceback" not in result.stderr
    lines = result.stderr.strip("\n").splitlines()
    assert len(lines) == 1
    assert "epics.json" in lines[0]
    assert _json_decode_error_text(malformed) in lines[0]


def test_a_malformed_data_prev_json_exits_with_a_message_naming_the_file(tmp_path):
    workdir = _workdir(tmp_path, {"repos": []})
    (workdir / "epics.json").write_text(json.dumps({"summary": "", "repos": {}}))
    malformed = '{"repos": {'
    (workdir / "data-prev.json").write_text(malformed)

    result = _run_build_subprocess(
        ["--dir", str(workdir), "--out", str(tmp_path / "page.html")]
    )

    assert result.returncode != 0
    assert "Traceback" not in result.stderr
    lines = result.stderr.strip("\n").splitlines()
    assert len(lines) == 1
    assert "data-prev.json" in lines[0]
    assert _json_decode_error_text(malformed) in lines[0]
