"""
Brief rendering tests for the survey brief generator (run.py).

Covers the brief's sections, size, truncation footers, degraded notes, and the
file:line references in the implementations index and extension points.
"""

import os
import re
import subprocess
import sys
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parent))

import run
from survey_test_helpers import _init_git_repo, _section_body


# ---------------------------------------------------------------------------
# Pinned contract constants - do NOT alter these strings
# ---------------------------------------------------------------------------

VALID_ERROR_STYLES = {"result", "exceptions", "mixed", "unknown"}

MD_SECTIONS = [
    "Where things live",
    "Naming conventions",
    "Error-handling style",
    "Existing implementations index",
    "Extension points",
]

TRUNCATION_FOOTER = "*brief truncated*"


# ---------------------------------------------------------------------------
# Brief: error_style enum
# ---------------------------------------------------------------------------

def test_error_style_value_is_in_allowed_enum(git_repo):
    brief = run._survey(git_repo)
    match = re.search(r"Detected style: \*\*(\w+)\*\*", brief)
    assert match, f"brief must report a detected error style:\n{brief}"
    assert match.group(1) in VALID_ERROR_STYLES, \
        f"error_style {match.group(1)!r} must be one of {VALID_ERROR_STYLES}"


# ---------------------------------------------------------------------------
# Brief: naming structure
# ---------------------------------------------------------------------------

def test_naming_maps_layer_to_case_counts(git_repo):
    """Every naming line reports all three case counts for its layer."""
    section = _section_body(run._survey(git_repo), "Naming conventions")
    entries = [ln for ln in section.split("\n") if ln.startswith("- **")]
    assert entries, f"brief must list at least one layer's naming counts:\n{section}"
    for line in entries:
        assert re.match(
            r"^- \*\*[^*]+\*\*: \w+ \(camelCase=\d+, snake_case=\d+, PascalCase=\d+\)$",
            line,
        ), f"naming entry must carry all three case counts: {line!r}"


# ---------------------------------------------------------------------------
# Brief: size and sections
# ---------------------------------------------------------------------------

def test_brief_within_5120_byte_limit(git_repo):
    size = len(run._survey(git_repo).encode())
    assert size <= 5120, f"brief is {size} bytes, limit is 5120"


def test_brief_sections_present_in_correct_order(git_repo):
    content = run._survey(git_repo)
    positions = []
    for heading in MD_SECTIONS:
        pos = content.find(heading)
        assert pos != -1, f"Required section {heading!r} missing from the brief"
        positions.append(pos)
    assert positions == sorted(positions), "brief sections are not in the required order"


def test_brief_contains_real_surveyed_content(tmp_path):
    """Guard against the brief being rendered from an empty/default dict."""
    repo = tmp_path / "repo"
    repo.mkdir()
    _init_git_repo(repo)
    (repo / "utils.py").write_text("def format_date(d):\n    return str(d)\n")
    subprocess.run(["git", "add", "."], cwd=repo, check=True, capture_output=True)
    subprocess.run(["git", "commit", "-m", "add utils"], cwd=repo, check=True, capture_output=True)

    content = run._survey(repo)
    assert len(content) > 300, \
        f"brief is suspiciously short ({len(content)} chars); likely rendered from empty data"


def test_survey_prints_the_brief_to_stdout(git_repo, capsys):
    """`main()` hands the brief to the session, not to a file."""
    prev = os.getcwd()
    try:
        os.chdir(git_repo)
        run.main()
    finally:
        os.chdir(prev)
    out = capsys.readouterr().out
    assert "## Where things live" in out, \
        f"main() must print the brief itself, not a status line:\n{out}"


# ---------------------------------------------------------------------------
# Truncation: >50 files per layer
# ---------------------------------------------------------------------------

def test_footer_visible_when_file_cap_hit(tmp_path):
    """Repo with >50 Python files: the truncation footer is visible in the brief."""
    repo = tmp_path / "repo"
    repo.mkdir()
    _init_git_repo(repo)

    for i in range(60):
        (repo / f"mod_{i:03d}.py").write_text(f"def fn_{i}():\n    return {i}\n")

    subprocess.run(["git", "add", "."], cwd=repo, check=True, capture_output=True)
    subprocess.run(["git", "commit", "-m", "many files"], cwd=repo, check=True, capture_output=True)

    md = run._survey(repo)
    assert TRUNCATION_FOOTER in md, \
        f"brief must contain the visible literal {TRUNCATION_FOOTER!r} when truncated"

    # Must not be hidden inside an HTML comment
    for segment in md.split("<!--"):
        if "-->" in segment:
            comment_body = segment.split("-->")[0]
            assert TRUNCATION_FOOTER not in comment_body, \
                f"{TRUNCATION_FOOTER} must not appear only inside an HTML comment"

    assert len(md.encode()) <= 5120, \
        f"brief must still be <=5120 bytes when truncated; got {len(md.encode())}"


# ---------------------------------------------------------------------------
# Truncation: byte budget exceeded (no per-layer file cap)
# ---------------------------------------------------------------------------

def test_small_repo_not_truncated(git_repo):
    """A small repo (brief well under 5120 bytes) must NOT carry the footer.

    Kills the always-truncate exploit: a correct _fit_to_budget returns content
    unchanged with was_truncated=False when it is under budget.
    """
    md = run._survey(git_repo)
    assert len(md.encode()) < 5120, (
        f"precondition failed: small git_repo brief is {len(md.encode())} bytes, "
        "expected well under 5120"
    )
    assert TRUNCATION_FOOTER not in md, (
        f"brief must NOT contain {TRUNCATION_FOOTER!r} for a small repo under the byte budget"
    )


def _repo_with_many_layers(tmp_path) -> Path:
    """A repo with 50 layers of 3 files each — over the byte budget, under the file cap."""
    repo = tmp_path / "repo"
    repo.mkdir()
    _init_git_repo(repo)

    # The naming-conventions section alone emits ~60 bytes per layer; 50 layers
    # ~3000 bytes there plus "Where things live" and headers easily exceeds the
    # 5120-byte budget without any layer reaching the 50-file cap.
    for layer_idx in range(50):
        layer_dir = repo / f"layer_{layer_idx:02d}"
        layer_dir.mkdir()
        for file_idx in range(3):
            (layer_dir / f"module_{file_idx}.py").write_text(
                f"def function_in_layer_{layer_idx}_file_{file_idx}():\n    pass\n"
            )

    subprocess.run(["git", "add", "."], cwd=repo, check=True, capture_output=True)
    subprocess.run(["git", "commit", "-m", "many layers"], cwd=repo, check=True, capture_output=True)
    return repo


def test_footer_present_when_byte_budget_exceeded(tmp_path):
    """The byte-budget truncation path fires independently of the file cap."""
    md = run._survey(_repo_with_many_layers(tmp_path))

    assert TRUNCATION_FOOTER in md, (
        f"brief must contain the visible literal {TRUNCATION_FOOTER!r} when byte budget exceeded"
    )
    assert len(md.encode()) <= 5120, (
        f"brief must still be <=5120 bytes after byte-budget truncation; got {len(md.encode())}"
    )


# A complete line the brief renderer can emit. Truncation must drop whole
# lines, so every surviving line (footer aside) must match one of these forms.
_COMPLETE_MD_LINE = re.compile(
    r"^(?:"
    r"|## .+"
    r"|Detected style: \*\*\w+\*\*"
    r"|- \*\*[^*]+\*\*: \d+ files"
    r"|- \*\*[^*]+\*\*: \w+ \(camelCase=\d+, snake_case=\d+, PascalCase=\d+\)"
    r"|- `[^`]+` \(\w+\) - .+:\d+"
    r"|_\([^)]+\)_"
    r"|_degraded: .+_"
    r")$"
)


def test_byte_budget_truncation_keeps_every_line_well_formed(tmp_path):
    """Per-section truncation must drop whole lines, never byte-chop mid-token.

    A raw UTF-8 byte slice cuts the rendered document at an arbitrary offset,
    leaving a final line cut mid-token (e.g. '- **layer_2'). Per-section
    truncation drops complete entries instead, so every surviving line stays a
    well-formed markdown line the renderer could have emitted.
    """
    md = run._survey(_repo_with_many_layers(tmp_path))

    # Precondition: this repo actually triggers truncation.
    assert TRUNCATION_FOOTER in md, "precondition: repo must exceed the 5120-byte budget"
    assert len(md.encode()) <= 5120

    body = md[: md.rindex(TRUNCATION_FOOTER)].rstrip("\n")
    for line in body.split("\n"):
        assert _COMPLETE_MD_LINE.match(line), (
            f"truncated brief has a line cut mid-token: {line!r}; per-section "
            "truncation must drop whole entries, not slice raw UTF-8 bytes"
        )

    # The highest-priority section must survive truncation.
    assert "## Where things live" in body, (
        "per-section truncation must keep the leading 'Where things live' section"
    )


# ---------------------------------------------------------------------------
# Tree-sitter degraded gating
# ---------------------------------------------------------------------------

def test_degraded_not_reported_when_tree_sitter_available(git_repo, monkeypatch):
    """The degraded note must be absent when tree-sitter is importable.

    Fails against an implementation that hardcodes degraded = True. A stand-in
    module drives the branch, so the assertion holds on a host without the
    optional package too: the flag keys on importability, not on parse results.
    """
    monkeypatch.setattr(run, "try_import_tree_sitter", lambda: object())
    assert "_degraded:" not in run._survey(git_repo), \
        "brief must not claim a degraded run when tree-sitter is available"


def test_degraded_reported_when_tree_sitter_unavailable(git_repo, monkeypatch):
    """The degraded note appears exactly when tree-sitter cannot be imported."""
    monkeypatch.setattr(run, "try_import_tree_sitter", lambda: None)
    brief = run._survey(git_repo)
    assert "_degraded: tree-sitter unavailable" in brief, \
        f"brief must flag a degraded run when try_import_tree_sitter returns None:\n{brief}"


# ---------------------------------------------------------------------------
# Brief: implementations index uses file:line, not layer:line
# ---------------------------------------------------------------------------

def _make_repo_with_symbol(tmp_path, subdir: str, filename: str, symbol: str, line: int) -> tuple:
    """
    Create a git repo containing one Python file at `subdir/filename`.
    The file has `line - 1` blank lines then `def symbol():`.
    Returns (repo_path, relative_file_path).
    """
    repo = tmp_path / "repo"
    repo.mkdir()
    _init_git_repo(repo)

    layer_dir = repo / subdir
    layer_dir.mkdir(parents=True, exist_ok=True)

    src_file = layer_dir / filename
    src_file.write_text("\n" * (line - 1) + f"def {symbol}():\n    pass\n")

    subprocess.run(["git", "add", "."], cwd=repo, check=True, capture_output=True)
    subprocess.run(["git", "commit", "-m", "add symbol"], cwd=repo, check=True, capture_output=True)

    return repo, f"{subdir}/{filename}"


@pytest.mark.parametrize(
    "subdir, filename, symbol, sym_line",
    [
        ("handlers", "order_handler.py", "process_order", 3),
        ("services", "user_svc.py", "create_user", 5),
    ],
)
def test_implementations_index_uses_file_path_not_layer_name(
    tmp_path, subdir, filename, symbol, sym_line
):
    """Implementations index must show the source file path, not a bare layer name.

    Fails against a `layer:line` rendering: the bare layer directory (e.g.
    'handlers') must not be the only file reference; the actual filename
    (e.g. 'order_handler.py') must appear in the entry for the symbol.
    """
    repo, _rel_path = _make_repo_with_symbol(tmp_path, subdir, filename, symbol, sym_line)
    section = _section_body(run._survey(repo), "Existing implementations index")

    # The entry for this symbol must contain the actual filename
    assert filename in section, (
        f"the implementations index must reference the source file "
        f"'{filename}', not a bare layer name.\nSection:\n{section}"
    )

    # The line number must appear
    assert str(sym_line) in section, (
        f"the implementations index must include line number {sym_line} "
        f"for symbol '{symbol}'.\nSection:\n{section}"
    )

    # A bare layer-only reference (subdir + colon, no filename) must not be the
    # pattern used — the real path component must be the filename, not the dir.
    layer_only_pattern = f"{subdir}:{sym_line}"
    assert layer_only_pattern not in section, (
        f"the implementations index must not use the bare layer reference "
        f"'{layer_only_pattern}'; it must show the actual file path.\nSection:\n{section}"
    )


def _make_repo_with_class_and_function(
    tmp_path, subdir: str, filename: str, class_name: str, plain_func: str
) -> Path:
    """
    Create a git repo containing one Python file at `subdir/filename` holding
    `class class_name` at line 1 and `def plain_func()` at line 5.
    Returns the repo path.
    """
    repo = tmp_path / "repo"
    repo.mkdir()
    _init_git_repo(repo)

    layer_dir = repo / subdir
    layer_dir.mkdir(parents=True, exist_ok=True)

    src_file = layer_dir / filename
    # class at line 1, plain function at line 5 (3 blank lines of separation)
    src_file.write_text(
        f"class {class_name}:\n"
        "    pass\n"
        "\n"
        "\n"
        f"def {plain_func}():\n"
        "    pass\n"
    )

    subprocess.run(["git", "add", "."], cwd=repo, check=True, capture_output=True)
    subprocess.run(
        ["git", "commit", "-m", "add ext point"], cwd=repo, check=True, capture_output=True
    )

    return repo


@pytest.mark.parametrize(
    "subdir, filename, class_name, class_line, plain_func, func_line",
    [
        ("ports/payment", "payment_port.py", "PaymentPort", 1, "helper_util", 5),
        ("adapters/email", "email_adapter.py", "EmailAdapter", 1, "build_headers", 5),
    ],
)
def test_extension_points_uses_file_path_not_layer_name(
    tmp_path, subdir, filename, class_name, class_line, plain_func, func_line
):
    """Extension points section: full file path shown and kind filter enforced.

    Two requirements in one fixture:
    1. The FULL nested relative path (e.g. ports/payment/payment_port.py:1) must
       appear as one contiguous substring — not just the filename alone, which would
       allow a layer/filename impl (dropping intermediate dirs) to pass.
    2. A class-based extension point IS present in the section; a plain top-level
       function in the same file is NOT — confirming the kind filter (interface/class
       only, not every function).
    """
    repo = _make_repo_with_class_and_function(tmp_path, subdir, filename, class_name, plain_func)

    section = _section_body(run._survey(repo), "Extension points")

    # The FULL nested path + line must be a single contiguous substring.
    full_path_ref = f"{Path(subdir) / filename}:{class_line}"
    assert full_path_ref in section, (
        f"extension points must contain the full nested path reference "
        f"'{full_path_ref}' as a contiguous substring. A layer/filename impl that "
        f"drops intermediate directories would fail this check.\nSection:\n{section}"
    )

    # The class-based extension point must appear in the section.
    assert class_name in section, (
        f"extension points must include the class/interface '{class_name}'."
        f"\nSection:\n{section}"
    )

    # The plain top-level function must NOT appear in the extension points section —
    # this confirms the kind filter (only interfaces/classes, not every function).
    assert plain_func not in section, (
        f"extension points must NOT include plain function '{plain_func}'; "
        f"extension points are for interfaces/abstractions, not every function."
        f"\nSection:\n{section}"
    )


def test_implementations_index_file_path_includes_relative_directory(tmp_path):
    """The file reference in the implementations index must be the full relative path.

    Uses a file nested two levels deep (core/domain/aggregate_root.py) so an impl
    that drops intermediate directories (emitting core/aggregate_root.py) also fails.
    The complete path must appear as one contiguous substring, not directory and
    filename asserted separately.
    """
    subdir = "core/domain"
    filename = "aggregate_root.py"
    symbol = "apply_event"
    sym_line = 6

    repo, _rel_path = _make_repo_with_symbol(tmp_path, subdir, filename, symbol, sym_line)
    section = _section_body(run._survey(repo), "Existing implementations index")

    # The FULL nested path followed by the line number must appear as one contiguous
    # substring. Asserting directory and filename separately would allow an impl that
    # drops the intermediate 'domain/' segment (e.g. emitting core/aggregate_root.py)
    # to pass this test.
    full_path_ref = f"{Path(subdir) / filename}:{sym_line}"
    assert full_path_ref in section, (
        f"the implementations index must contain the full path reference "
        f"'{full_path_ref}' as a contiguous substring. Asserting directory and filename "
        f"separately would allow a wrong impl (e.g. 'core/aggregate_root.py') to pass.\n"
        f"Section:\n{section}"
    )


# ---------------------------------------------------------------------------
# Trim: binary-search budget trimmer matches the old pop-loop, encodes O(log n) times
# ---------------------------------------------------------------------------

def _reference_trim(content, max_bytes):
    lines = content.split("\n")
    while lines and len("\n".join(lines).encode()) > max_bytes:
        lines.pop()
    while lines and (lines[-1] == "" or lines[-1].startswith("## ")):
        lines.pop()
    return "\n".join(lines)


def test_trim_matches_the_pop_loop_byte_for_byte():
    """`_trim_lines_to_budget` must agree with the old linear pop-loop everywhere.

    Covers: empty content, content already under budget, content cut mid-list,
    and content whose last surviving line (before the "" / "## " cleanup) is a
    section header.
    """
    # budget=0: empty content.
    empty_content = ""

    # budget=64: already under budget, no popping needed by either implementation.
    under_budget_content = "short\nlines\nok"

    # budget=512: long enough that trimming cuts off mid-list of plain lines.
    mid_list_content = "\n".join(
        f"item-{i:03d}-filler-text-here" for i in range(40)
    )

    # budget=5120: engineered so the pop-loop's post-trim boundary lands exactly
    # on a "## " header line, which the cleanup loop must then also pop.
    header_lines = [f"{i:04d}".ljust(20, "x") for i in range(300)]
    header_lines[242] = "## " + "h" * 17
    header_case_content = "\n".join(header_lines)

    cases = [
        (empty_content, 0),
        (under_budget_content, 64),
        (mid_list_content, 512),
        (header_case_content, 5120),
    ]

    for content, max_bytes in cases:
        expected = _reference_trim(content, max_bytes)
        actual = run._trim_lines_to_budget(content, max_bytes)
        assert actual == expected, (
            f"_trim_lines_to_budget(..., {max_bytes}) must match the pop-loop "
            f"reference byte-for-byte.\nexpected={expected!r}\nactual={actual!r}"
        )


def test_trim_encodes_a_logarithmic_number_of_times(monkeypatch):
    """Binary search must encode O(log n) times, not once per dropped line.

    The old pop loop takes 1,052 iterations on this input (600 lines, 40
    chars each, trimmed to 5120 bytes); the binary search must take at most
    12 encodes.
    """
    lines = ["a" * 40 for _ in range(600)]
    content = "\n".join(lines)

    original_encoded_len = run._encoded_len
    call_count = {"n": 0}

    def counting_encoded_len(ls):
        call_count["n"] += 1
        return original_encoded_len(ls)

    monkeypatch.setattr(run, "_encoded_len", counting_encoded_len)

    run._trim_lines_to_budget(content, 5120)

    assert call_count["n"] <= 12, (
        f"_trim_lines_to_budget encoded {call_count['n']} times trimming 600 lines "
        "to 5120 bytes; a binary search must take at most 12 encodes, not one per "
        "dropped line"
    )
