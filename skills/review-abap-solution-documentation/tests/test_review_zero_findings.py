"""A complete zero-finding report must pass check_review.py.

The report is derived from the checker's authored PASSING_REPORT fixture, not
from a captured SAP review.
"""

from pathlib import Path
import re
import runpy
import tempfile
import unittest

SCRIPT = Path(__file__).resolve().parents[1] / "scripts/check_review.py"


class ZeroFindingTests(unittest.TestCase):
    def test_review_validation_accepts_a_complete_zero_finding_report(self):
        module = runpy.run_path(str(SCRIPT))
        report = re.sub(r"(?ms)^### F\d+:.*?(?=^## |\Z)", "", module["PASSING_REPORT"])
        report = re.sub(
            r"(?m)^Findings:.*$",
            "Findings: 0 (CRITICAL: 0, HIGH: 0, MEDIUM: 0, LOW: 0, INFO: 0)",
            report,
        )
        with tempfile.TemporaryDirectory() as output:
            root = Path(output)
            (root / "review-report.md").write_text(report, encoding="utf-8")
            failures = [n for n, ok, _ in module["run_checks"](root) if not ok]
        self.assertEqual(failures, [], f"Valid zero-finding report rejected: {failures}")


if __name__ == "__main__":
    unittest.main()
