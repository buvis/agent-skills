import pytest
from gate import main, summary_line


def test_summary_line_reports_counts_from_pytests_final_line():
    output = (
        "skills/x/test_a.py ..F\n"
        "====== 2 failed, 4328 passed, 12 skipped, 2 warnings in 357.17s (0:05:57) ======\n"
    )
    assert summary_line(output, 1) == "PASS 4328 FAIL 2 SKIP 12 EXIT 1"


def test_summary_line_counts_collection_errors_as_failures():
    output = "==== 1 failed, 3 passed, 2 errors in 1.02s ====\n"
    assert summary_line(output, 1) == "PASS 3 FAIL 3 SKIP 0 EXIT 1"


def test_summary_line_ignores_counts_outside_the_final_line():
    output = "test says 99 passed here\n==== 5 passed in 0.10s ====\n"
    assert summary_line(output, 0) == "PASS 5 FAIL 0 SKIP 0 EXIT 0"


def test_summary_line_takes_the_last_of_several_summary_lines():
    output = "==== 9 passed in 0.10s ====\nplugin noise\n==== 1 failed, 2 passed in 0.20s ====\n"
    assert summary_line(output, 1) == "PASS 2 FAIL 1 SKIP 0 EXIT 1"


@pytest.mark.parametrize(
    "final",
    [
        "3 passed, 1 skipped in 0.10s",
        "\x1b[32m==== \x1b[1m3 passed\x1b[0m, \x1b[33m1 skipped\x1b[0m\x1b[32m in 0.10s\x1b[0m ==",
    ],
    ids=["quiet", "colored"],
)
def test_summary_line_reads_quiet_and_colored_summaries(final):
    assert summary_line(f"...s\n{final}\n", 0) == "PASS 3 FAIL 0 SKIP 1 EXIT 0"


def test_summary_line_never_reads_as_a_pass_without_a_summary():
    assert summary_line("no summary here\n", 0) == "PASS 0 FAIL 0 SKIP 0 EXIT 1"
    assert summary_line("no tests ran in 0.01s\n", 5) == "PASS 0 FAIL 0 SKIP 0 EXIT 5"


@pytest.mark.parametrize(
    "body, expected_code, expected_line",
    [
        ("def test_ok():\n    pass\n", 0, "PASS 1 FAIL 0 SKIP 0 EXIT 0"),
        ("def test_bad():\n    assert False\n", 1, "PASS 0 FAIL 1 SKIP 0 EXIT 1"),
    ],
    ids=["green", "red"],
)
def test_main_returns_pytests_exit_code_and_prints_the_gate_line_last(
    tmp_path, capfd, body, expected_code, expected_line
):
    target = tmp_path / "test_probe.py"
    target.write_text(body, encoding="utf-8")

    code = main(["-q", "-p", "no:cacheprovider", str(target)])

    assert code == expected_code
    assert capfd.readouterr().out.splitlines()[-1] == expected_line
