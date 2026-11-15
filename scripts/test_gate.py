from gate import summary_line


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
