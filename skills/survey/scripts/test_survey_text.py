"""
Tests for the optional pre-read text threaded through the symbol extractors
and the error-style scan.

Each test puts one content on disk and a different content in the `text` /
`texts` argument, so an implementation that ignores the argument and reads
the disk anyway reports the disk symbols (or style) and fails.
"""

import sys
from pathlib import Path
from types import SimpleNamespace

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parent))

import run
from survey_test_helpers import requires_tree_sitter


# ---------------------------------------------------------------------------
# _extract_file_symbols_regex
# ---------------------------------------------------------------------------

def test_regex_extractor_uses_given_text_instead_of_disk(tmp_path):
    """Given text wins over the file on disk; disk symbols must not appear."""
    f = tmp_path / "svc.py"
    f.write_text("def disk_only():\n    pass\n")
    text = "\n\nclass Ledger:\n    pass\n\ndef settle(x):\n    return x\n"

    symbols = run._extract_file_symbols_regex(f, text=text)

    assert ("Ledger", "class", 3) in symbols, f"text class missing: {symbols}"
    assert ("settle", "function", 6) in symbols, f"text function missing: {symbols}"
    assert "disk_only" not in {n for n, _, _ in symbols}, \
        f"disk content must not be read when text is given: {symbols}"


def test_regex_extractor_with_text_needs_no_file_on_disk(tmp_path):
    """A path that does not exist still yields the text's symbols."""
    f = tmp_path / "missing.rs"
    text = "pub fn spawn() {}\n\npub trait Codec {}\n"

    symbols = run._extract_file_symbols_regex(f, text=text)

    assert ("spawn", "function", 1) in symbols, f"{symbols}"
    assert ("Codec", "interface", 3) in symbols, f"{symbols}"


def test_regex_extractor_without_text_reads_disk_and_tolerates_missing_file(
    tmp_path,
):
    """text=None keeps today's behavior: read the file, [] when unreadable."""
    f = tmp_path / "svc.py"
    f.write_text("\ndef from_disk(a):\n    return a\n")

    assert ("from_disk", "function", 2) in run._extract_file_symbols_regex(f, text=None)
    assert run._extract_file_symbols_regex(tmp_path / "gone.py", text=None) == []


def test_regex_extractor_empty_text_yields_no_symbols_without_reading_disk(
    tmp_path,
):
    """An empty string is a real text, not 'absent': the disk is not read."""
    f = tmp_path / "svc.py"
    f.write_text("def disk_only():\n    pass\n")

    assert run._extract_file_symbols_regex(f, text="") == []


# ---------------------------------------------------------------------------
# _extract_tree_sitter
# ---------------------------------------------------------------------------

@requires_tree_sitter
def test_tree_sitter_extractor_uses_given_text_instead_of_disk(tmp_path):
    """tree-sitter parses the given text; a missing file does not matter."""
    f = tmp_path / "missing.py"
    text = "\nclass Box:\n    def open(self):\n        return 1\n"

    symbols = run._extract_tree_sitter(f, run.try_import_tree_sitter(), text=text)

    assert ("Box", "class", 2) in symbols, f"{symbols}"
    assert ("open", "method", 3) in symbols, f"{symbols}"


@requires_tree_sitter
def test_tree_sitter_extractor_without_text_reads_disk(tmp_path):
    """text=None reads the file as before; an unreadable file yields []."""
    f = tmp_path / "svc.py"
    f.write_text("class Box:\n    def open(self):\n        return 1\n")
    ts = run.try_import_tree_sitter()

    assert ("open", "method", 2) in run._extract_tree_sitter(f, ts, text=None)
    assert run._extract_tree_sitter(tmp_path / "gone.py", ts, text=None) == []


# ---------------------------------------------------------------------------
# _extract_file_symbols: text reaches every extractor call
# ---------------------------------------------------------------------------

@requires_tree_sitter
def test_file_symbols_pass_text_to_tree_sitter(tmp_path):
    """The 'method' kind only tree-sitter produces must come from the text."""
    f = tmp_path / "svc.py"
    f.write_text("def disk_only():\n    pass\n")
    text = "class Box:\n    def open(self):\n        return 1\n"

    symbols = run._extract_file_symbols(f, text=text)

    assert ("open", "method", 2) in symbols, f"{symbols}"
    assert "disk_only" not in {n for n, _, _ in symbols}, f"{symbols}"


def test_file_symbols_pass_text_to_regex_when_tree_sitter_absent(
    tmp_path, monkeypatch
):
    """With the optional package absent, the regex fallback uses the text."""
    f = tmp_path / "svc.py"
    f.write_text("def disk_only():\n    pass\n")
    monkeypatch.setattr(run, "try_import_tree_sitter", lambda: None)

    symbols = run._extract_file_symbols(f, text="\ndef from_text(a):\n    return a\n")

    assert ("from_text", "function", 2) in symbols, f"{symbols}"
    assert "disk_only" not in {n for n, _, _ in symbols}, f"{symbols}"


def test_file_symbols_pass_text_to_regex_when_tree_sitter_finds_nothing(
    tmp_path, monkeypatch
):
    """The empty-tree-sitter fallback uses the text, not the disk."""
    f = tmp_path / "svc.py"
    f.write_text("def disk_only():\n    pass\n")
    monkeypatch.setattr(run, "try_import_tree_sitter", lambda: object())
    monkeypatch.setattr(run, "_extract_tree_sitter", lambda *a, **k: [])

    symbols = run._extract_file_symbols(f, text="\n\ndef from_text(a):\n    return a\n")

    assert ("from_text", "function", 3) in symbols, f"{symbols}"
    assert "disk_only" not in {n for n, _, _ in symbols}, f"{symbols}"


def test_file_symbols_pass_text_to_go_type_merge(tmp_path, monkeypatch):
    """The .go struct/interface merge reads types from the text, not the disk.

    tree-sitter is made to return one function so the empty fallback is not
    taken and only the .go merge can contribute the type symbols.
    """
    f = tmp_path / "main.go"
    f.write_text("package main\n\ntype DiskType struct {\n}\n")
    text = (
        "package main\n\n"
        "func run() {}\n\n"
        "type Server struct {\n}\n\n"
        "type Handler interface {\n}\n"
    )
    monkeypatch.setattr(run, "try_import_tree_sitter", lambda: object())
    monkeypatch.setattr(
        run, "_extract_tree_sitter", lambda *a, **k: [("run", "function", 3)]
    )

    symbols = run._extract_file_symbols(f, text=text)

    assert ("Server", "class", 5) in symbols, f"{symbols}"
    assert ("Handler", "interface", 8) in symbols, f"{symbols}"
    assert "DiskType" not in {n for n, _, _ in symbols}, f"{symbols}"


# ---------------------------------------------------------------------------
# _compute_error_style: texts map
# ---------------------------------------------------------------------------

_GO_RESULT = "func f() error {\n    if err != nil {\n        return err\n    }\n}\n"
_GO_PANIC = "func f() {\n    panic(\"boom\")\n}\n"


def test_error_style_uses_texts_instead_of_disk(tmp_path):
    """A file present in texts is classified from texts, not its disk content."""
    f = tmp_path / "main.go"
    f.write_text(_GO_PANIC)

    style = run._compute_error_style({"cmd": [f]}, texts={f: _GO_RESULT})

    assert style == "result", f"texts must override disk content, got {style!r}"


def test_error_style_reads_disk_for_files_missing_from_texts(tmp_path):
    """Files absent from texts are read from disk; both sources count.

    a.go exists only in texts (result style), b.go only on disk (panic). One
    of each gives 'mixed'; dropping either source gives a pure style.
    """
    a = tmp_path / "a.go"
    b = tmp_path / "b.go"
    b.write_text(_GO_PANIC)

    style = run._compute_error_style({"cmd": [a, b]}, texts={a: _GO_RESULT})

    assert style == "mixed", f"expected both sources counted, got {style!r}"


@pytest.mark.parametrize("texts", [None, {}])
def test_error_style_without_usable_texts_reads_disk(tmp_path, texts):
    """texts None or empty falls back to the disk read; missing files skip."""
    f = tmp_path / "main.go"
    f.write_text(_GO_PANIC)
    gone = tmp_path / "gone.go"

    style = run._compute_error_style({"cmd": [gone, f]}, texts=texts)

    assert style == "exceptions", f"disk content must be read, got {style!r}"


def test_error_style_ignores_texts_outside_the_50_file_sample(tmp_path):
    """texts never widen the sample: the 51st file is not scanned.

    The first file carries result style via texts; files 2-50 do not exist;
    file 51 carries panic style via texts. Only 'result' respects the cap.
    """
    files = [tmp_path / f"f{i:02d}.go" for i in range(51)]
    texts = {files[0]: _GO_RESULT, files[50]: _GO_PANIC}

    style = run._compute_error_style({"cmd": files}, texts=texts)

    assert style == "result", f"file beyond the cap was scanned, got {style!r}"


def test_error_style_empty_text_in_texts_is_used_not_disk(tmp_path):
    """An empty string in texts is real content, not 'absent'.

    `texts.get(f) or <disk read>` would fall through on "" and classify the
    panic on disk as 'exceptions'; the empty text carries no signal.
    """
    f = tmp_path / "main.go"
    f.write_text(_GO_PANIC)

    style = run._compute_error_style({"cmd": [f]}, texts={f: ""})

    assert style == "unknown", f"empty text must not fall back to disk, got {style!r}"


# ---------------------------------------------------------------------------
# Supplied text means the disk is never read, not merely ignored
# ---------------------------------------------------------------------------

def _forbid_disk_reads(monkeypatch):
    """Make every Path.read_text record the call and raise.

    The call is recorded as well as raised so an implementation that swallows
    the AssertionError in a broad except still fails the test.
    """
    calls: list[Path] = []

    def _raise(self, *args, **kwargs):
        calls.append(self)
        raise AssertionError("disk was read when text was supplied")

    monkeypatch.setattr(Path, "read_text", _raise)
    return calls


def _stub_ts_module(sources: list[str]):
    """A tree-sitter stand-in that records each source it is asked to parse."""

    def _process(source, cfg):
        sources.append(source)
        return SimpleNamespace(structure=[])

    return SimpleNamespace(
        process=_process,
        ProcessConfig=lambda **kwargs: SimpleNamespace(**kwargs),
    )


def test_regex_extractor_never_reads_disk_when_text_given(tmp_path, monkeypatch):
    f = tmp_path / "svc.py"
    f.write_text("def disk_only():\n    pass\n")
    calls = _forbid_disk_reads(monkeypatch)

    symbols = run._extract_file_symbols_regex(f, text="def from_text():\n    pass\n")

    assert calls == [], f"disk was read for {calls}"
    assert ("from_text", "function", 1) in symbols, f"{symbols}"


def test_tree_sitter_extractor_never_reads_disk_when_text_given(
    tmp_path, monkeypatch
):
    f = tmp_path / "svc.py"
    f.write_text("def disk_only():\n    pass\n")
    sources: list[str] = []
    calls = _forbid_disk_reads(monkeypatch)

    run._extract_tree_sitter(f, _stub_ts_module(sources), text="def from_text(): pass\n")

    assert calls == [], f"disk was read for {calls}"
    assert sources == ["def from_text(): pass\n"], f"parsed {sources!r}"


def test_tree_sitter_extractor_parses_empty_text_not_disk(tmp_path):
    """text="" is parsed as-is; `text or <disk read>` would parse the disk."""
    f = tmp_path / "svc.py"
    f.write_text("class Box:\n    def open(self):\n        return 1\n")
    sources: list[str] = []

    run._extract_tree_sitter(f, _stub_ts_module(sources), text="")

    assert sources == [""], f"empty text must reach the parser, got {sources!r}"


def test_error_style_never_reads_disk_for_files_in_texts(tmp_path, monkeypatch):
    f = tmp_path / "main.go"
    f.write_text(_GO_PANIC)
    calls = _forbid_disk_reads(monkeypatch)

    style = run._compute_error_style({"cmd": [f]}, texts={f: _GO_RESULT})

    assert calls == [], f"disk was read for {calls}"
    assert style == "result", f"{style!r}"


def test_file_symbols_hand_text_to_tree_sitter_extractor(tmp_path, monkeypatch):
    """The text kwarg itself reaches _extract_tree_sitter (no tree-sitter needed)."""
    f = tmp_path / "svc.py"
    f.write_text("def disk_only():\n    pass\n")
    seen: list[object] = []

    def _fake_ts(path, ts_module, *args, **kwargs):
        seen.append(kwargs.get("text", args[0] if args else None))
        return []

    monkeypatch.setattr(run, "try_import_tree_sitter", lambda: object())
    monkeypatch.setattr(run, "_extract_tree_sitter", _fake_ts)

    run._extract_file_symbols(f, text="some-marker-text")

    assert seen == ["some-marker-text"], f"tree-sitter got text={seen!r}"
