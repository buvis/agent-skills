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


def test_survey_reads_each_sampled_file_exactly_once(tmp_path, monkeypatch):
    """Every sampled file is read once per survey, never by a consumer again.

    An implementation that still lets the extractors or the error-style scan
    read for themselves reads every file at least twice. One that treats
    an empty text as missing re-reads empty.py.
    """
    repo = _build_repo(tmp_path)
    sampled = [p.resolve() for p in (repo / "src").iterdir()] + [
        p.resolve() for p in (repo / "pkg").iterdir()
    ]
    reads = _count_reads(monkeypatch)

    run._survey(repo)

    over_read = {str(p): reads[p] for p in sampled if reads[p] != 1}
    assert not over_read, (
        f"each sampled file must be read from disk exactly once; got {over_read}"
    )


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
