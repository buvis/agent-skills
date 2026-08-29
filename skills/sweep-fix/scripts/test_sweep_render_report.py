"""Tests for sweep.py: render_report."""
import re
import subprocess
from pathlib import Path

import pytest
import yaml  # test-only round-trip parser; sweep.py itself must stay stdlib-only

import sweep


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


