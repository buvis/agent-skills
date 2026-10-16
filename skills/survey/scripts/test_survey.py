"""
End-to-end behavioral tests for the survey brief generator (run.py).

All tests operate on real tmp-dir (git) repos and assert on the markdown brief
`run._survey` returns.  The brief is ephemeral, so there is no atlas.json, no
atlas.md, and no staleness flag to assert on.
"""

import os
import subprocess
import sys
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parent))

import run
from survey_test_helpers import PINNED_KINDS, _init_git_repo, requires_tree_sitter


# ---------------------------------------------------------------------------
# R1: the brief is ephemeral — surveying writes nothing
# ---------------------------------------------------------------------------

def test_survey_writes_nothing_under_home(tmp_path, monkeypatch, capsys):
    """A full `main()` run must leave no store behind anywhere under HOME.

    The map is generated and handed to the session, never stored. An
    implementation that writes an atlas.json, a cache dir, an audit log, or
    even one empty directory fails here.
    """
    repo = tmp_path / "repo"
    repo.mkdir()
    _init_git_repo(repo)
    home = tmp_path / "home"
    home.mkdir()
    monkeypatch.setattr(Path, "home", staticmethod(lambda: home))

    prev = os.getcwd()
    try:
        os.chdir(repo)
        run.main()
    finally:
        os.chdir(prev)

    assert capsys.readouterr().out.strip(), "survey must print the brief to stdout"
    assert not list(home.iterdir()), (
        f"survey must not create anything under HOME; found {list(home.iterdir())}"
    )


def test_run_py_executes_standalone(tmp_path):
    """run.py surveys and prints as a plain child process, writing no HOME.

    The rest of the suite imports `run` directly, so it cannot see an
    import-time failure, a missing dependency, or a write the module makes on
    someone else's HOME. This is the only test that runs the real entry point.
    """
    repo = tmp_path / "repo"
    repo.mkdir()
    _init_git_repo(repo)
    home = tmp_path / "home"
    home.mkdir()

    proc = subprocess.run(
        [sys.executable, str(Path(__file__).resolve().parent / "run.py")],
        cwd=repo,
        capture_output=True,
        text=True,
        env={**os.environ, "HOME": str(home)},
        timeout=60,
    )

    assert proc.returncode == 0, f"run.py exited {proc.returncode}:\n{proc.stderr}"
    assert "## Where things live" in proc.stdout, \
        f"run.py must print the brief to stdout:\n{proc.stdout}"

    # tree_sitter_language_pack unpacks its compiled grammars into the platform
    # cache dir on first import (~/Library/Caches on macOS, ~/.cache on Linux).
    # That belongs to the dependency; any other file here would be survey's.
    strays = [
        str(p.relative_to(home))
        for p in home.rglob("*")
        if p.is_file() and "tree-sitter-language-pack" not in p.parts
    ]
    assert not strays, f"run.py must not write under HOME; found {strays}"


# ---------------------------------------------------------------------------
# Tree-sitter symbol extraction
# ---------------------------------------------------------------------------

# --- Python: indented method, kind 'method', computed line --------------------
# Each case: (class_name, method_name, leading_blank_lines). The class sits at
# line `blanks + 1`; the method at `blanks + 2`. Varying names AND blank-line
# count means no fixed if/else chain returning canned tuples can satisfy all
# cases — the expected line is computed from the input, never hardcoded.

@requires_tree_sitter
@pytest.mark.parametrize(
    "class_name, method_name, blanks",
    [
        ("Service", "handle", 0),
        ("Repository", "find_by_id", 2),
        ("OrderBook", "settle", 5),
        ("Cache", "evict", 1),
    ],
)
def test_python_method_extracted_with_method_kind_and_computed_line(
    tmp_path, class_name, method_name, blanks
):
    """An indented method is extracted as kind 'method' at its real line.

    A naive ^def|^class regex misses indented methods and cannot tell method
    from function; a content-matching stub cannot enumerate these cases.
    """
    f = tmp_path / "svc.py"
    f.write_text(
        "\n" * blanks
        + f"class {class_name}:\n"
        + f"    def {method_name}(self, req):\n"
        + "        return req\n"
    )
    class_line = blanks + 1
    method_line = blanks + 2
    symbols = run._extract_file_symbols(f)

    assert (class_name, "class", class_line) in symbols, \
        f"class {class_name!r} must be kind 'class' at line {class_line}: {symbols}"
    assert (method_name, "method", method_line) in symbols, \
        f"method {method_name!r} must be kind 'method' at line {method_line}: {symbols}"


# --- Python: decorated function, extracted at its `def` line ------------------
# decorators is a tuple; the `def` sits at line `blanks + len(decorators) + 1`.

@pytest.mark.parametrize(
    "func_name, decorators, blanks",
    [
        ("fetch", ("@cache", "@retry(times=3)"), 0),
        ("load_config", ("@lru_cache",), 3),
        ("dispatch", ("@app.route('/x')", "@auth", "@trace"), 1),
        ("render", (), 4),
    ],
)
def test_python_decorated_function_extracted_at_def_line(
    tmp_path, func_name, decorators, blanks
):
    """A decorated function is extracted as a function at its `def` line.

    A regex anchored to ^def after decorator lines either misses it or reports
    the wrong line; the expected line is computed from blanks + decorator count.
    """
    f = tmp_path / "deco.py"
    f.write_text(
        "\n" * blanks
        + "".join(d + "\n" for d in decorators)
        + f"def {func_name}(url):\n"
        + "    return url\n"
    )
    def_line = blanks + len(decorators) + 1
    symbols = run._extract_file_symbols(f)

    assert (func_name, "function", def_line) in symbols, \
        f"function {func_name!r} must be kind 'function' at line {def_line}: {symbols}"


# --- TypeScript: interface, kind 'interface', computed line -------------------

@pytest.mark.parametrize(
    "iface_name, blanks",
    [
        ("User", 0),
        ("OrderRow", 2),
        ("ApiResponse", 5),
        ("Config", 1),
    ],
)
def test_typescript_interface_extracted_with_interface_kind(
    tmp_path, iface_name, blanks
):
    """A TypeScript interface is extracted with kind 'interface' at its line."""
    f = tmp_path / "model.ts"
    f.write_text(
        "\n" * blanks
        + f"export interface {iface_name} {{\n"
        + "  id: string;\n"
        + "}\n"
    )
    iface_line = blanks + 1
    symbols = run._extract_file_symbols(f)

    assert (iface_name, "interface", iface_line) in symbols, \
        f"TS interface {iface_name!r} must be kind 'interface' " \
        f"at line {iface_line}: {symbols}"


# --- Rust: trait + struct, pinned kinds, computed lines -----------------------
# trait at line `blanks + 1`; the struct follows the 3-line trait body plus one
# blank separator, at line `blanks + 5`.

@pytest.mark.parametrize(
    "trait_name, struct_name, blanks",
    [
        ("Greeter", "Robot", 0),
        ("Handler", "Server", 2),
        ("Codec", "GzipCodec", 4),
        ("Reader", "FileReader", 1),
    ],
)
def test_rust_struct_and_trait_extracted_with_pinned_kinds(
    tmp_path, trait_name, struct_name, blanks
):
    """Rust trait -> 'interface' and struct -> pinned enum, at computed lines.

    The kinds enum is {function, class, method, type, interface}; assert the
    extractor maps Rust constructs into that enum at the right lines.
    """
    f = tmp_path / "lib.rs"
    f.write_text(
        "\n" * blanks
        + f"pub trait {trait_name} {{\n"
        + "    fn greet(&self) -> String;\n"
        + "}\n"
        + "\n"
        + f"pub struct {struct_name};\n"
    )
    trait_line = blanks + 1
    struct_line = blanks + 5
    symbols = run._extract_file_symbols(f)
    kinds = {n: k for n, k, _ in symbols}
    lines = {n: ln for n, _, ln in symbols}

    assert trait_name in kinds, f"Rust trait {trait_name!r} not extracted: {symbols}"
    assert kinds[trait_name] == "interface", \
        f"Rust trait must be kind 'interface', got {kinds[trait_name]!r}"
    assert lines[trait_name] == trait_line, \
        f"trait {trait_name!r} must be at line {trait_line}, got {lines[trait_name]}"

    assert struct_name in kinds, f"Rust struct {struct_name!r} not extracted: {symbols}"
    assert kinds[struct_name] in ("type", "class"), \
        f"Rust struct kind must be in the pinned enum, got {kinds[struct_name]!r}"
    assert lines[struct_name] == struct_line, \
        f"struct {struct_name!r} must be at line {struct_line}, got {lines[struct_name]}"


# ---------------------------------------------------------------------------
# _extract_file_symbols: regex fallback when tree-sitter yields nothing
# ---------------------------------------------------------------------------

def test_regex_fallback_used_when_tree_sitter_extraction_returns_empty(
    tmp_path, monkeypatch
):
    """When tree-sitter is importable but _extract_tree_sitter yields no
    symbols for a file (e.g. a per-file parse failure), _extract_file_symbols
    must fall back to the regex extractor instead of dropping every symbol.
    """
    f = tmp_path / "svc.py"
    f.write_text("def handler(req):\n    return req\n")

    # tree-sitter stays importable, but extraction yields nothing for this file.
    monkeypatch.setattr(run, "_extract_tree_sitter", lambda *a, **k: [])

    symbols = run._extract_file_symbols(f)
    names = {n for n, _, _ in symbols}
    assert "handler" in names, (
        "regex fallback must recover symbols when tree-sitter extraction "
        f"returns empty; got {symbols}"
    )


@requires_tree_sitter
def test_extracted_kinds_are_within_pinned_enum(git_repo):
    """Extracted kinds stay in the pinned enum AND expected symbols are present.

    The positive-content assertions ensure an extractor that returns [] (or
    drops the method) cannot pass this test by vacuous truth.
    """
    (git_repo / "extra.py").write_text(
        "class Box:\n"
        "    def open(self):\n"
        "        return 1\n"
    )
    syms = run._extract_file_symbols(git_repo / "extra.py")

    for name, kind, line in syms:
        assert kind in PINNED_KINDS, \
            f"symbol {name!r} has kind {kind!r} not in {PINNED_KINDS}"
        assert isinstance(line, int) and line >= 1, \
            f"symbol {name!r} has invalid line number {line!r}"

    assert ("Box", "class", 1) in syms, \
        f"expected class 'Box' at line 1 to be extracted: {syms}"
    assert ("open", "method", 2) in syms, \
        f"expected method 'open' at line 2 to be extracted: {syms}"


# ---------------------------------------------------------------------------
# _compute_error_style: Go support
# ---------------------------------------------------------------------------

def test_go_idiomatic_error_handling_classifies_as_result(tmp_path):
    """A Go-only repo using idiomatic if-err-nil style must classify as 'result'.

    A wrong impl with no Go branch returns 'unknown' — this test catches that.
    Returning 'mixed' or 'exceptions' would also fail.
    """
    go_dir = tmp_path / "cmd"
    go_dir.mkdir()

    (go_dir / "main.go").write_text(
        'package main\n\n'
        'import (\n'
        '    "errors"\n'
        '    "fmt"\n'
        ')\n\n'
        'func run() error {\n'
        '    if err := doWork(); err != nil {\n'
        '        return fmt.Errorf("run failed: %w", err)\n'
        '    }\n'
        '    return nil\n'
        '}\n\n'
        'func doWork() error {\n'
        '    if false {\n'
        '        return errors.New("something went wrong")\n'
        '    }\n'
        '    if err := validate(); err != nil {\n'
        '        return err\n'
        '    }\n'
        '    return nil\n'
        '}\n\n'
        'func validate() error { return nil }\n'
    )

    layers = {"cmd": [go_dir / "main.go"]}
    style = run._compute_error_style(layers)

    assert style == "result", (
        f"Go-only repo with idiomatic if-err-nil / errors.New / fmt.Errorf must classify "
        f"as 'result', got {style!r}. A missing Go branch returns 'unknown'."
    )


def test_go_panic_error_handling_classifies_as_exceptions(tmp_path):
    """A Go-only repo using panic() for errors (no if-err-nil) must classify as 'exceptions'.

    A wrong impl that returns 'result' whenever the substring 'err' appears
    (even in a comment) would fail here — the word 'err' exists only in a comment,
    while the actual error handling is panic-style.
    """
    go_dir = tmp_path / "cmd"
    go_dir.mkdir()

    (go_dir / "main.go").write_text(
        'package main\n\n'
        '// Note: we do not use err return values here; panics signal failure.\n'
        'func mustOpen(path string) []byte {\n'
        '    data, ok := readFile(path)\n'
        '    if !ok {\n'
        '        panic("failed to open " + path)\n'
        '    }\n'
        '    return data\n'
        '}\n\n'
        'func readFile(path string) ([]byte, bool) {\n'
        '    if path == "" {\n'
        '        return nil, false\n'
        '    }\n'
        '    return []byte(path), true\n'
        '}\n'
    )

    layers = {"cmd": [go_dir / "main.go"]}
    style = run._compute_error_style(layers)

    assert style == "exceptions", (
        f"Go-only repo that uses panic() (no if-err-nil, 'err' only in a comment) "
        f"must classify as 'exceptions', got {style!r}. "
        f"A wrong impl keying on bare 'err' substring would return 'result'."
    )
