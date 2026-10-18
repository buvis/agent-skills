"""
Single-read tests for `run._survey`.

`_survey` reads each sampled file from disk once and hands that text to every
consumer: the symbol extractors (tree-sitter, regex fallback, Go type merge)
and the error-style scan. No consumer may read a sampled file again. A file
that cannot be read stays unreadable for every consumer, with no crash.
"""

import sys
from collections import Counter
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))

import run
from survey_test_helpers import _init_git_repo


_GO_SOURCE = (
    "package engine\n\n"
    "import \"errors\"\n\n"
    "type Engine struct {\n"
    "    name string\n"
    "}\n\n"
    "func (e *Engine) Start() error {\n"
    "    if err := check(); err != nil {\n"
    "        return err\n"
    "    }\n"
    "    return errors.New(\"stopped\")\n"
    "}\n\n"
    "func check() error { return nil }\n"
)


def _build_repo(tmp_path: Path) -> Path:
    """Two layers mixing languages, a Go file, an empty file and a non-code file.

    The Go file is the costly case (tree-sitter, regex fallback and the Go
    type merge each want its text); the empty file catches an implementation
    that treats "" as "not read yet"; notes.md has no parser at all.
    """
    repo = tmp_path / "repo"
    repo.mkdir()
    _init_git_repo(repo)
    src = repo / "src"
    src.mkdir()
    (src / "svc.py").write_text(
        "class Service:\n    def handle(self, req):\n        return req\n"
    )
    (src / "engine.go").write_text(_GO_SOURCE)
    (src / "empty.py").write_text("")
    (src / "notes.md").write_text("# Notes\n\nNothing to parse.\n")
    pkg = repo / "pkg"
    pkg.mkdir()
    (pkg / "model.ts").write_text("export interface OrderRow {\n  id: string;\n}\n")
    return repo


def _count_reads(monkeypatch) -> Counter:
    """Record every Path.read_text call by resolved path, then read for real."""
    reads: Counter = Counter()
    real_read_text = Path.read_text

    def spy(self, *args, **kwargs):
        reads[self.resolve()] += 1
        return real_read_text(self, *args, **kwargs)

    monkeypatch.setattr(Path, "read_text", spy)
    return reads


def test_survey_brief_still_reflects_file_contents_after_single_read(
    tmp_path, monkeypatch
):
    """The text read once reaches every consumer, so the brief is unchanged.

    An implementation that hands consumers an empty or wrong text would pass
    the read count but lose these symbols and the error style.
    """
    repo = _build_repo(tmp_path)
    _count_reads(monkeypatch)

    brief = run._survey(repo)

    for name in ("Service", "Engine", "OrderRow"):
        assert f"`{name}`" in brief, f"symbol {name!r} missing from brief:\n{brief}"
    assert "Detected style: **result**" in brief, (
        f"Go err != nil / errors.New must still classify as 'result':\n{brief}"
    )


def test_survey_reads_current_contents_on_every_call(tmp_path):
    """The read-once texts belong to one survey call, not to the process.

    A cache kept across calls would report a symbol the file no longer has.
    """
    repo = _build_repo(tmp_path)
    first = run._survey(repo)
    assert "`Service`" in first, f"first survey must list Service:\n{first}"

    (repo / "src" / "svc.py").write_text("def renamed_handler(req):\n    return req\n")
    second = run._survey(repo)

    assert "`renamed_handler`" in second, \
        f"second survey must see the edited file:\n{second}"
    assert "`Service`" not in second, \
        f"second survey must not reuse the first call's text:\n{second}"


def test_survey_unreadable_file_is_skipped_without_error(tmp_path, monkeypatch):
    """A file whose read fails is left out; the rest of the survey still works.

    Indexing the read-once mapping directly would raise KeyError for the file
    that failed to read. The file still counts toward its layer.
    """
    repo = _build_repo(tmp_path)
    broken = (repo / "src" / "svc.py").resolve()
    real_read_text = Path.read_text

    def failing_read(self, *args, **kwargs):
        if self.resolve() == broken:
            raise PermissionError(13, "Permission denied", str(self))
        return real_read_text(self, *args, **kwargs)

    monkeypatch.setattr(Path, "read_text", failing_read)

    brief = run._survey(repo)

    assert "`Service`" not in brief, \
        f"symbols of an unreadable file must not appear:\n{brief}"
    assert "`Engine`" in brief and "`OrderRow`" in brief, \
        f"readable files must still be surveyed:\n{brief}"
    assert "- **src**: 4 files" in brief, \
        f"the unreadable file still counts toward its layer:\n{brief}"


def test_survey_invalid_utf8_file_degrades_instead_of_crashing(tmp_path, monkeypatch):
    """The single read decodes leniently, like the per-consumer reads it replaced.

    A strict utf-8 decode raises UnicodeDecodeError on a Latin-1 byte and
    aborts the survey; the lenient read replaces the byte and keeps the
    file's symbols.
    """
    repo = tmp_path / "repo"
    repo.mkdir()
    _init_git_repo(repo)
    src = repo / "src"
    src.mkdir()
    (src / "latin.py").write_bytes(b"# caf\xe9\nclass Latin:\n    pass\n")
    _count_reads(monkeypatch)

    brief = run._survey(repo)

    assert "`Latin`" in brief, \
        f"a file with invalid utf-8 bytes must still yield its symbols:\n{brief}"


class _RaisingTreeSitter:
    """Tree-sitter stand-in whose parse always fails, forcing the regex fallback."""

    class ProcessConfig:
        def __init__(self, **kwargs):
            self.kwargs = kwargs

    @staticmethod
    def process(text, config):
        raise RuntimeError("parse failed")


def test_survey_reads_every_sampled_file_once_beyond_fifty(tmp_path, monkeypatch):
    """The single read covers every sampled file, not just the first 50.

    The error-style scan historically sampled only 50 files. An implementation
    that pre-reads only that sample leaves files 51+ to the extractors, and
    with tree-sitter failing each such file is read by tree-sitter and again
    by the regex fallback.
    """
    repo = tmp_path / "repo"
    repo.mkdir()
    _init_git_repo(repo)
    sampled: list[Path] = []
    for layer in ("alpha", "beta"):
        layer_dir = repo / layer
        layer_dir.mkdir()
        for i in range(30):
            f = layer_dir / f"mod_{i:02d}.py"
            f.write_text(f"def handler_{layer}_{i:02d}(req):\n    return req\n")
            sampled.append(f.resolve())
    assert len(sampled) > 50
    monkeypatch.setattr(run, "try_import_tree_sitter", lambda: _RaisingTreeSitter)
    reads = _count_reads(monkeypatch)

    run._survey(repo)

    over_read = {str(p): reads[p] for p in sampled if reads[p] != 1}
    assert not over_read, (
        f"each of the {len(sampled)} sampled files must be read exactly once; "
        f"got {over_read}"
    )
