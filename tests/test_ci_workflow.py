"""Pin the CI facts that make the Windows lane worth its runtime.

A Windows job only proves anything if it runs what the Linux job runs. The
cheap ways to turn it green - filter the collection with `-k`, stop at
`--collect-only`, run pytest from some other directory, gate the job behind an
`if:` that never matches, or swallow the exit status - all leave the badge
green while the platform bug ships. These tests refuse each of those escapes,
and they refuse them wherever the argument can enter: the command line, an
`env:` block, and pytest's own `addopts`.

`*.sh eol=lf` is the other half. Without it a Windows checkout rewrites every
shell suite to CRLF, and bash reads the carriage return as part of the command.
Git applies the last matching pattern per attribute, so a later `*` rule
carrying `eol=` takes the LF right back - order matters as much as content.

Job membership is checked by containment, never by count, so adding a job is
never a failure here.
"""

from __future__ import annotations

import ast
import re
import shlex
import sys
from fnmatch import fnmatchcase
from pathlib import Path

import yaml

if sys.version_info >= (3, 11):
    import tomllib
else:  # 3.10 is the floor from requires-python and ships no tomllib.
    tomllib = None

REPO = Path(__file__).resolve().parents[1]
WORKFLOW = REPO / ".github" / "workflows" / "ci.yml"
GITATTRIBUTES = REPO / ".gitattributes"
PYPROJECT = REPO / "pyproject.toml"

ORIGINAL_JOBS = {"test", "shell", "lint", "node"}
COLLECTED = {"tests", "skills", "scripts"}

# The exact command the Windows job must carry, per the spec.
FULL_SUITE = "uv run --python 3.13 pytest"

# Anything that shrinks what pytest collects: the two filter flags, the marker
# filter, and any positional argument, which can only name a path or a node id.
FILTER_FLAGS = ("-k", "--deselect", "-m")

# Collects the whole suite, executes none of it, and still exits 0.
COLLECT_ONLY_FLAGS = frozenset({"--co", "--collect-only"})

# pytest reads this as extra argv, so it narrows a command it never appears in.
ARGV_ENV = "PYTEST_ADDOPTS"

# GitHub's default bash wrapper adds `-e`. A `{0}` template replaces the whole
# wrapper and drops it, so a later line decides the step's exit status.
PLAIN_INTERPRETER = re.compile(r"^[A-Za-z][\w.+-]*$")

# A forced success anywhere in the block that runs pytest.
FORCED_SUCCESS = re.compile(r"\bexit\s+0\b|\|\|\s*(?:true\b|:)")

# Paths a `.gitattributes` pattern has to miss to leave the `*.sh` rule alone.
SHELL_FILES = ("probe.sh", "skills/demo/scripts/probe.sh")


def workflow() -> dict:
    return yaml.safe_load(WORKFLOW.read_text(encoding="utf-8"))


def jobs() -> dict[str, dict]:
    return workflow()["jobs"]


def windows_job() -> dict:
    """The `windows` job, or a failure that says it is missing."""
    defined = jobs()
    if "windows" not in defined:
        raise AssertionError(
            f"{WORKFLOW.name} defines no `windows` job, so nothing runs the "
            f"suite on a CRLF checkout. Present jobs: {sorted(defined)}"
        )
    return defined["windows"]


def steps_of(job: dict) -> list[dict]:
    return job.get("steps") or []


def step_label(step: dict, index: int) -> str:
    label = step.get("name") or step.get("uses") or step.get("run") or f"step {index}"
    return str(label).splitlines()[0]


def pytest_commands(job: dict) -> list[str]:
    """Every `run:` block in the job that invokes the full suite."""
    blocks = [str(step.get("run", "")) for step in steps_of(job)]
    return [block for block in blocks if FULL_SUITE in block]


def collect_only_flags(argv: str | list[str]) -> list[str]:
    """The flags that make pytest stop after collection."""
    tokens = argv if isinstance(argv, list) else shlex.split(argv)
    return [token for token in tokens if token in COLLECT_ONLY_FLAGS]


def collection_narrowing(command: str) -> list[str]:
    """Everything in a `run:` block that leaves part of the suite unrun.

    The whole block is read, not just its first pytest line: what sits BEFORE
    the command on its line (`cd docs &&`) picks a different rootdir, and a
    second pytest line can carry the filter the first one does not.
    """
    found: list[str] = []
    for line in command.splitlines():
        if FULL_SUITE not in line:
            continue
        head, tail = line.split(FULL_SUITE, 1)
        if head.strip():
            found.append(head.strip())
        for token in shlex.split(tail):
            narrows = not token.startswith("-") or token.startswith(FILTER_FLAGS)
            if narrows or token in COLLECT_ONLY_FLAGS:
                found.append(token)
    return found


def forced_success(command: str) -> list[str]:
    """Lines of a `run:` block that hand the step a zero exit status."""
    return [line.strip() for line in command.splitlines() if FORCED_SUCCESS.search(line)]


def custom_shell_templates(job: dict) -> list[str]:
    """`shell:` values that replace GitHub's error-checked default wrapper."""
    configured = []
    default = ((job.get("defaults") or {}).get("run") or {}).get("shell")
    if default is not None:
        configured.append(("the job's defaults", default))
    for index, step in enumerate(steps_of(job)):
        if step.get("shell") is not None:
            configured.append((step_label(step, index), step["shell"]))
    return [
        f"{where} -> {value!r}"
        for where, value in configured
        if not PLAIN_INTERPRETER.match(str(value))
    ]


def conditioned_places(job: dict) -> list[str]:
    """Every `if:` between the workflow's events and the suite running."""
    gated = []
    if "if" in job:
        gated.append(f"the job itself -> {job['if']!r}")
    for index, step in enumerate(steps_of(job)):
        if "if" in step:
            gated.append(f"{step_label(step, index)} -> {step['if']!r}")
    return gated


def argv_env_places() -> list[str]:
    """Every `env:` reaching the Windows job that rewrites pytest's argv."""
    setting = []
    if ARGV_ENV in (workflow().get("env") or {}):
        setting.append("the workflow's top-level env")
    job = windows_job()
    if ARGV_ENV in (job.get("env") or {}):
        setting.append("the `windows` job's env")
    for index, step in enumerate(steps_of(job)):
        if ARGV_ENV in (step.get("env") or {}):
            setting.append(step_label(step, index))
    return setting


def gitattributes_entries() -> list[tuple[str, list[str]]]:
    """Every `pattern attributes...` line, in file order."""
    entries = []
    for raw in GITATTRIBUTES.read_text(encoding="utf-8").splitlines():
        line = raw.strip()
        if not line or line.startswith("#"):
            continue
        pattern, *attributes = line.split()
        entries.append((pattern, attributes))
    return entries


def shell_attributes() -> list[str]:
    """Every attribute `.gitattributes` grants the `*.sh` pattern."""
    granted: list[str] = []
    for pattern, attributes in gitattributes_entries():
        if pattern == "*.sh":
            granted.extend(attributes)
    return granted


def later_eol_overrides() -> list[str]:
    """Lines after `*.sh` that also match a shell file and re-decide `eol`."""
    entries = gitattributes_entries()
    patterns = [pattern for pattern, _ in entries]
    start = patterns.index("*.sh") + 1 if "*.sh" in patterns else len(entries)
    overriding = []
    for pattern, attributes in entries[start:]:
        if not any(fnmatchcase(probe, pattern) for probe in SHELL_FILES):
            continue
        for attribute in attributes:
            if attribute.split("=", 1)[0].lstrip("-!") == "eol" and attribute != "eol=lf":
                overriding.append(f"{pattern} {' '.join(attributes)}")
                break
    return overriding


def pytest_ini_options() -> dict:
    """The `[tool.pytest.ini_options]` table."""
    text = PYPROJECT.read_text(encoding="utf-8")
    if tomllib is not None:
        return tomllib.loads(text)["tool"]["pytest"]["ini_options"]
    # No TOML parser on 3.10 and no dependency to add one; both keys are unique.
    pattern = r"^{key}\s*=\s*(\[[^\]]*\]|\"[^\"]*\"|'[^']*')"
    return {
        key: ast.literal_eval(match.group(1))
        for key in ("testpaths", "addopts")
        if (match := re.search(pattern.format(key=key), text, re.MULTILINE))
    }


def configured_testpaths() -> list[str]:
    """The trees a bare `pytest` collects, per [tool.pytest.ini_options]."""
    options = pytest_ini_options()
    if "testpaths" not in options:
        raise AssertionError("pyproject.toml sets no testpaths under [tool.pytest.ini_options]")
    return options["testpaths"]


def configured_addopts() -> str | list[str]:
    """The arguments [tool.pytest.ini_options] adds to every pytest run."""
    return pytest_ini_options().get("addopts", "")


def collect_only_complaint() -> str:
    """Why `addopts` stops pytest at collection, or an empty string."""
    stopping = collect_only_flags(configured_addopts())
    if not stopping:
        return ""
    return (
        f"[tool.pytest.ini_options] addopts carries {stopping}, so every "
        f"pytest run in CI collects the suite, executes none of it, and exits "
        f"0 - on Windows and on ubuntu alike."
    )


def test_windows_job_runs_on_a_windows_runner() -> None:
    """An ubuntu runner named `windows` would test nothing new."""
    runner = windows_job().get("runs-on")
    assert runner == "windows-latest", (
        f"the `windows` job runs on {runner!r}; it has to be 'windows-latest' "
        f"or it never sees a CRLF checkout or a Windows path separator."
    )


def test_the_four_original_jobs_survive() -> None:
    """Adding the Windows lane must not quietly retire an existing one."""
    defined = set(jobs())
    assert defined >= ORIGINAL_JOBS, (  # containment, never a count
        f"jobs missing from {WORKFLOW.name}: {sorted(ORIGINAL_JOBS - defined)}. "
        f"Still defined: {sorted(defined)}"
    )


def test_windows_job_runs_on_every_event_the_workflow_triggers_on() -> None:
    """An `if:` the workflow's events never satisfy makes the lane a no-op."""
    gated = conditioned_places(windows_job())
    assert not gated, (
        f"an `if:` condition guards {gated}. The workflow triggers on push, "
        f"pull_request and workflow_dispatch, so a condition here decides "
        f"whether Windows is tested at all - it has to run every time."
    )


def test_windows_job_runs_the_whole_python_suite() -> None:
    """A filtered Windows run is a green badge over an untested platform."""
    commands = pytest_commands(windows_job())
    assert commands, (
        f"no step in the `windows` job runs {FULL_SUITE!r}, so the suite never runs on Windows."
    )
    for command in commands:
        narrowed = collection_narrowing(command)
        assert not narrowed, (
            f"the Windows pytest run carries {narrowed}, which leaves part of "
            f"the suite uncollected or unrun. Run it bare, like the ubuntu "
            f"`test` job does, or the platform bugs hide in the skipped part."
        )
    rewriting = argv_env_places()
    assert not rewriting, (
        f"{ARGV_ENV} is set on: {rewriting}. pytest appends it to argv, so a "
        f"`--co` or `-k` there empties the run without touching the command."
    )


def test_windows_job_does_not_suppress_failures() -> None:
    """A red Windows suite has to end as a red check."""
    job = windows_job()
    suppressing = ["the job itself"] if job.get("continue-on-error") else []
    for index, step in enumerate(steps_of(job)):
        if step.get("continue-on-error"):
            suppressing.append(step_label(step, index))
    assert not suppressing, (
        f"continue-on-error is set on: {suppressing}. A Windows failure would "
        f"then report as success, which is worse than having no Windows job."
    )
    templated = custom_shell_templates(job)
    assert not templated, (
        f"a custom `shell:` command is set on: {templated}. GitHub's default "
        f"wrapper runs bash with `-e`; a `{{0}}` template replaces it and "
        f"drops that, so a failing pytest no longer ends the step."
    )
    for command in pytest_commands(job):
        forced = forced_success(command)
        assert not forced, (
            f"the Windows pytest block forces its status with {forced}. The "
            f"step then exits 0 whatever pytest returned, so the check stays "
            f"green over a failing suite."
        )


def test_gitattributes_keeps_shell_files_lf() -> None:
    """CRLF in a .sh file makes bash read the carriage return as an argument."""
    assert GITATTRIBUTES.is_file(), (
        f"{GITATTRIBUTES.name} is missing from the repository root, so a "
        f"Windows checkout rewrites every skills/*/scripts/*.sh to CRLF."
    )
    granted = shell_attributes()
    assert "eol=lf" in granted, (
        f"{GITATTRIBUTES.name} grants `*.sh` {granted or 'nothing'}; it needs "
        f"`eol=lf` so shell suites stay LF wherever they are checked out."
    )
    overriding = later_eol_overrides()
    assert not overriding, (
        f"{GITATTRIBUTES.name} decides `eol` for shell files again after the "
        f"`*.sh` rule: {overriding}. Git keeps the LAST matching pattern per "
        f"attribute, so that line, not `*.sh eol=lf`, rules the checkout."
    )


def test_pytest_collects_tests_skills_and_scripts() -> None:
    """Otherwise a bare `pytest` never sees the repo-level scripts tests."""
    configured = set(configured_testpaths())
    assert configured >= COLLECTED, (  # containment, never equality
        f"testpaths is missing {sorted(COLLECTED - configured)}; a bare "
        f"`pytest` then skips those trees, including on Windows. "
        f"Configured: {sorted(configured)}"
    )


def test_pytest_runs_what_it_collects() -> None:
    """`--co` in addopts turns every pytest run, everywhere, into a no-op."""
    complaint = collect_only_complaint()
    assert not complaint, complaint


# Measured on pytest 9.1.1: `addopts = "--strict-markers --co"` collects this
# file, runs no test body, and exits 0. A rule that only lives in a test body
# therefore cannot fail on the one config that breaks it. Collection still
# imports the module, so the same check runs here and errors the run instead.
if collect_only_complaint():
    raise AssertionError(collect_only_complaint())
