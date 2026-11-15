"""Run the full pytest suite and end with the autopilot gate summary line.

`autopilot verify` reads only `PASS n FAIL n SKIP n EXIT n`; pytest prints its
own summary, which the parser ignores. Run as `uv run python scripts/gate.py`.
"""

import re
import subprocess
import sys

_FINAL_RE = re.compile(r"^=+ (.+) in [\d.]+s\b")
_COUNT_RE = re.compile(r"(\d+) (passed|failed|skipped|errors?)\b")


def summary_line(output: str, exit_code: int) -> str:
    """Build the gate line from pytest's last summary line; errors count as failures."""
    counts = {"passed": 0, "failed": 0, "skipped": 0}
    finals = [m[1] for line in output.splitlines() if (m := _FINAL_RE.match(line))]
    for number, kind in _COUNT_RE.findall(finals[-1] if finals else ""):
        counts["failed" if kind.startswith("error") else kind] += int(number)
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
    assert proc.stdout is not None
    for line in proc.stdout:
        sys.stdout.write(line)
        lines.append(line)
    code = proc.wait()
    print(summary_line("".join(lines), code), flush=True)
    return code


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
