"""Tests for sweep.py: resolve_rg, resolve_ast_grep, module imports."""
import ast
import os
import shutil
import subprocess
import sys
from pathlib import Path

import pytest

import sweep


# -- resolve_rg -----------------------------------------------------------


def test_run_rg_never_invokes_a_bare_rg_binary_by_name():
    # Pins the invocation shape _run_rg must use: "rg" is a shell function
    # on some hosts, not a PATH binary, so a naive bare-name subprocess call
    # is not viable there. Rather than asserting that fact about whatever
    # host happens to run the suite (true only when rg is absent from
    # PATH), this parses sweep.py's own source (like
    # test_sweep_module_imports_only_stdlib_modules does) and fails if
    # someone drops the `executable=` argument or changes argv[0] away from
    # the literal "rg".
    source = Path(sweep.__file__).read_text()
    tree = ast.parse(source, filename=sweep.__file__)

    run_rg = next(
        node
        for node in ast.walk(tree)
        if isinstance(node, ast.FunctionDef) and node.name == "_run_rg"
    )
    call = next(
        node
        for node in ast.walk(run_rg)
        if isinstance(node, ast.Call)
        and isinstance(node.func, ast.Attribute)
        and node.func.attr == "run"
    )

    argv0 = call.args[0].elts[0]
    assert isinstance(argv0, ast.Constant) and argv0.value == "rg"
    assert "executable" in {kw.arg for kw in call.keywords}


def test_resolve_rg_finds_a_real_rg_binary_on_path(tmp_path, monkeypatch):
    fake_rg = tmp_path / "rg"
    fake_rg.write_text("#!/bin/sh\necho fake-rg\n")
    fake_rg.chmod(0o755)
    monkeypatch.setenv("PATH", f"{tmp_path}{os.pathsep}{os.environ['PATH']}")

    result = sweep.resolve_rg()

    assert result == str(fake_rg)


def test_resolve_rg_result_is_cached_across_calls(tmp_path, monkeypatch):
    original_path = os.environ["PATH"]
    fake_rg = tmp_path / "rg"
    fake_rg.write_text("#!/bin/sh\necho fake-rg\n")
    fake_rg.chmod(0o755)
    monkeypatch.setenv("PATH", f"{tmp_path}{os.pathsep}{original_path}")

    first = sweep.resolve_rg()
    assert first == str(fake_rg)

    # Restore PATH so the fake binary is no longer reachable; an uncached
    # call would now resolve differently (fallback path or SystemExit).
    monkeypatch.setenv("PATH", original_path)
    second = sweep.resolve_rg()

    assert second == first


def test_resolve_rg_returns_a_working_path_when_absent_from_path(tmp_path, monkeypatch):
    # Force the claude-binary fallback branch regardless of what the host
    # running the suite has on PATH: point PATH at a directory with no rg,
    # and CLAUDE_CODE_EXECPATH at a fixture executable that behaves like the
    # claude binary for this purpose.
    empty_path_dir = tmp_path / "empty_path"
    empty_path_dir.mkdir()
    monkeypatch.setenv("PATH", str(empty_path_dir))

    fake_claude = tmp_path / "claude"
    fake_claude.write_text("#!/bin/sh\necho ripgrep 14.0.0\n")
    fake_claude.chmod(0o755)
    monkeypatch.setenv("CLAUDE_CODE_EXECPATH", str(fake_claude))

    path = sweep.resolve_rg()

    assert path == str(fake_claude)

    result = subprocess.run(
        ["rg", "--version"], executable=path, capture_output=True, text=True
    )

    assert result.returncode == 0
    assert "ripgrep" in result.stdout.lower()


def test_resolve_rg_exits_naming_both_candidates_when_neither_resolves(
    tmp_path, monkeypatch
):
    monkeypatch.setenv("PATH", "/usr/bin:/bin")  # no rg here
    monkeypatch.delenv("CLAUDE_CODE_EXECPATH", raising=False)
    monkeypatch.setenv("HOME", str(tmp_path))  # no ~/.local/bin/claude here

    with pytest.raises(RuntimeError) as exc_info:
        sweep.resolve_rg()

    combined = str(exc_info.value).lower()
    assert "rg" in combined
    assert "claude" in combined


# -- resolve_ast_grep -------------------------------------------------------


def test_resolve_ast_grep_matches_mise_which_output():
    expected = subprocess.run(
        ["mise", "which", "ast-grep"], capture_output=True, text=True, check=True
    ).stdout.strip()

    assert sweep.resolve_ast_grep() == expected


def test_resolve_ast_grep_falls_back_to_mise_when_absent_from_path(monkeypatch):
    mise_path = shutil.which("mise")
    assert mise_path is not None, "mise must be on PATH for this test to be meaningful"
    mise_dir = os.path.dirname(mise_path)
    expected = subprocess.run(
        ["mise", "which", "ast-grep"], capture_output=True, text=True, check=True
    ).stdout.strip()

    monkeypatch.setenv("PATH", f"{mise_dir}{os.pathsep}/usr/bin{os.pathsep}/bin")

    result = sweep.resolve_ast_grep()

    assert result == expected


def test_resolve_ast_grep_result_is_cached_across_calls(monkeypatch):
    mise_path = shutil.which("mise")
    assert mise_path is not None, "mise must be on PATH for this test to be meaningful"
    mise_dir = os.path.dirname(mise_path)

    monkeypatch.setenv("PATH", f"{mise_dir}{os.pathsep}/usr/bin{os.pathsep}/bin")
    first = sweep.resolve_ast_grep()

    # A PATH with neither ast-grep nor mise reachable; an uncached call
    # would now raise SystemExit instead of matching `first`.
    monkeypatch.setenv("PATH", "/usr/bin:/bin")
    second = sweep.resolve_ast_grep()

    assert second == first


def test_resolve_ast_grep_exits_naming_both_attempts_when_neither_resolves(
    monkeypatch,
):
    monkeypatch.setenv("PATH", "/usr/bin:/bin")  # neither ast-grep nor mise here

    with pytest.raises(RuntimeError) as exc_info:
        sweep.resolve_ast_grep()

    combined = str(exc_info.value).lower()
    assert "ast-grep" in combined
    assert "mise" in combined


# -- module imports -----------------------------------------------------


def test_sweep_module_imports_only_stdlib_modules():
    # Pins the "runs on a bare python3" contract: no third-party import at
    # module load time, so the script cannot die on import before it
    # parses a single argument on a machine that never installed anything
    # for it. Parses the source rather than inspecting sys.modules, so this
    # fails on the import statement itself rather than on whatever happens
    # to be installed on the machine running the suite.
    source = Path(sweep.__file__).read_text()
    tree = ast.parse(source, filename=sweep.__file__)

    top_level_modules = set()
    for node in ast.walk(tree):
        if isinstance(node, ast.Import):
            for alias in node.names:
                top_level_modules.add(alias.name.split(".")[0])
        elif isinstance(node, ast.ImportFrom):
            if node.level == 0 and node.module:
                top_level_modules.add(node.module.split(".")[0])

    non_stdlib = sorted(top_level_modules - sys.stdlib_module_names)
    assert not non_stdlib, f"sweep.py imports non-stdlib module(s): {non_stdlib}"


