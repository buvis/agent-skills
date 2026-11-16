"""Run the full pytest suite and end with the autopilot gate summary line.

`autopilot verify` reads only `PASS n FAIL n SKIP n EXIT n`; pytest prints its
own summary, which the parser ignores. Run as `uv run python scripts/gate.py`.
"""

import re
import subprocess
import sys

# pytest's last line, with or without the `=` rails (`-q` drops them).
# A count may be one word (`3 passed`) or a subtest count (`4 subtests passed`).
_FINAL_RE = re.compile(r"^(?:=+ )?(\d+ [a-z ]+?(?:, \d+ [a-z ]+?)*) in [\d.]+s\b")
# Subtest passes and skips are not test results; a failed subtest is a failure.
_COUNT_RE = re.compile(r"(\d+) (subtests failed|passed|failed|skipped|errors?)\b")
_ANSI_RE = re.compile(r"\x1b\[[0-9;]*m")


def parse_counts(output: str) -> dict[str, int] | None:
    """Counts from pytest's last summary line, or None when there is none."""
    plain = (_ANSI_RE.sub("", line) for line in output.splitlines())
    finals = [m[1] for line in plain if (m := _FINAL_RE.match(line))]
    if not finals:
        return None
    counts = {"passed": 0, "failed": 0, "skipped": 0}
    for number, kind in _COUNT_RE.findall(finals[-1]):
        counts[kind if kind in counts else "failed"] += int(number)
    return counts


def summary_line(output: str, exit_code: int) -> str:
    """Build the gate line from pytest's last summary line; errors count as failures.

    Without a summary line the counts are unknown, so the line never reads as a
    pass: a zero exit code is reported as 1.
    """
    counts = parse_counts(output)
    if counts is None:
        return f"PASS 0 FAIL 0 SKIP 0 EXIT {exit_code or 1}"
    return (
        f"PASS {counts['passed']} FAIL {counts['failed']} SKIP {counts['skipped']} EXIT {exit_code}"
    )


def main(argv: list[str]) -> int:
    proc = subprocess.Popen(
        [sys.executable, "-m", "pytest", *argv],
        stdout=subprocess.PIPE,
        stderr=subprocess.STDOUT,
        text=True,
    )
    lines = []
    for line in proc.stdout:
        sys.stdout.write(line)
        lines.append(line)
    code = proc.wait()
    output = "".join(lines)
    if parse_counts(output) is None:
        print("gate: no pytest summary line found; counts are unknown", file=sys.stderr)
        code = code or 1
    print(summary_line(output, code), flush=True)
    return code


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
