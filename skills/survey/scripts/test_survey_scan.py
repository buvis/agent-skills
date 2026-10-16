"""
Traversal and pruning tests for the survey layer scan (run._scan_layers).

Covers what becomes a layer, which directories are pruned at any depth, and
the per-layer file cap.
"""

import sys
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parent))

import run
from survey_test_helpers import _section_body


# ---------------------------------------------------------------------------
# Layers: what is skipped, and what is not
# ---------------------------------------------------------------------------

def test_build_output_is_skipped_but_ordinary_dirs_are_not(tmp_path):
    """Build and dependency output never becomes a layer; anything else does.

    The skip list holds only names that mean build output in every repo, so a
    source directory that happens to be called `tasks` or `logs` keeps its own
    layer. A host-tuned skip list would silently drop it from the brief.

    The directory is deliberately not a git repo: survey reads the tree, never
    the index, so a plain directory must produce a brief just the same.
    """
    repo = tmp_path / "repo"
    repo.mkdir()
    for name in ("services", "tasks", "logs", "node_modules", "dist", "target"):
        (repo / name).mkdir()
        (repo / name / "thing.py").write_text("def thing():\n    pass\n")

    section = _section_body(run._survey(repo), "Where things live")

    for kept in ("services", "tasks", "logs"):
        assert f"**{kept}**" in section, \
            f"{kept!r} is source, not build output, and must be its own layer:\n{section}"
    for skipped in ("node_modules", "dist", "target"):
        assert f"**{skipped}**" not in section, \
            f"{skipped!r} is build output and must never become a layer:\n{section}"


# ---------------------------------------------------------------------------
# Source contract: the old glob-based scan helper must be gone
# ---------------------------------------------------------------------------

def test_source_no_longer_names_rglob_scan_helper():
    """run.py's source must not name the old glob-based scan helper (rglob).

    Pins `rg -n "rglob" skills/survey/scripts/run.py` printing no match, a
    gate stated as both a task acceptance criterion and a project Success
    Criterion. This is a source-content rule, not a runtime behavior: read
    the module's own file through run.__file__ so the test follows the
    module rather than a hardcoded path.
    """
    source = Path(run.__file__).read_text()
    assert "rglob" not in source, (
        "run.py must not contain the literal token 'rglob'; the glob-based "
        "scan helper must be fully replaced by the pruning os.walk traversal"
    )


# ---------------------------------------------------------------------------
# _scan_layers: _SKIP_DIRS and dot-directories are pruned at any depth
# ---------------------------------------------------------------------------

def test_skip_dirs_are_pruned_at_every_depth(tmp_path):
    """Every _SKIP_DIRS name and every dot-directory under a top-level source
    dir is pruned, leaving only the ordinary file in the layer.

    Skip dirs nested further down are covered by
    test_skip_dir_at_any_depth_excluded_from_layer.
    """
    repo = tmp_path / "repo"
    repo.mkdir()

    (repo / "src").mkdir(parents=True)
    (repo / "src" / "real.py").write_text("x = 1\n")

    (repo / "src" / "node_modules" / "pkg").mkdir(parents=True)
    (repo / "src" / "node_modules" / "pkg" / "junk.js").write_text("x = 1;\n")

    (repo / "src" / "build").mkdir(parents=True)
    (repo / "src" / "build" / "out.py").write_text("x = 1\n")

    (repo / "src" / ".venv" / "lib").mkdir(parents=True)
    (repo / "src" / ".venv" / "lib" / "dep.py").write_text("x = 1\n")

    assert [p.name for p in run._scan_layers(repo)[0]["src"]] == ["real.py"]


@pytest.mark.parametrize("skip_name", sorted(run._SKIP_DIRS))
def test_skip_dir_at_any_depth_excluded_from_layer(tmp_path, skip_name):
    """Every name in _SKIP_DIRS is pruned when nested below a top-level dir,
    not just the ones exercised by other tests (e.g. node_modules, build).

    An ordinary sibling directory at the same depth keeps its file, so an
    impl that drops the whole top-level layer instead of pruning one branch
    also fails here.
    """
    repo = tmp_path / "repo"
    repo.mkdir()
    (repo / "src" / "mid" / skip_name / "deep").mkdir(parents=True)
    (repo / "src" / "mid" / skip_name / "deep" / "excluded.py").write_text("x = 1\n")
    (repo / "src" / "mid" / "keep" / "deep").mkdir(parents=True)
    (repo / "src" / "mid" / "keep" / "deep" / "included.py").write_text("y = 2\n")

    layers, _truncated = run._scan_layers(repo)
    names = {p.name for p in layers["src"]}

    assert "included.py" in names, f"ordinary nested file must survive: {names}"
    assert "excluded.py" not in names, (
        f"a file nested under skip dir {skip_name!r} at depth must not appear "
        f"in the 'src' layer: {names}"
    )


@pytest.mark.parametrize("dot_name", [".venv", ".secretdir"])
def test_dot_directory_at_any_depth_excluded_from_layer(tmp_path, dot_name):
    """A file nested under any dot-prefixed directory, at any depth, must not
    appear in its top directory's layer.

    Two different dot names guard against an impl that special-cases a single
    literal (e.g. only '.venv') instead of a generic dot-prefix rule.
    """
    repo = tmp_path / "repo"
    repo.mkdir()
    (repo / "src" / "mid" / dot_name / "deep").mkdir(parents=True)
    (repo / "src" / "mid" / dot_name / "deep" / "excluded.py").write_text("x = 1\n")
    (repo / "src" / "mid" / "keep" / "deep").mkdir(parents=True)
    (repo / "src" / "mid" / "keep" / "deep" / "included.py").write_text("y = 2\n")

    layers, _truncated = run._scan_layers(repo)
    names = {p.name for p in layers["src"]}

    assert "included.py" in names, f"ordinary nested file must survive: {names}"
    assert "excluded.py" not in names, (
        f"a file nested under dot-directory {dot_name!r} at depth must not "
        f"appear in the 'src' layer: {names}"
    )


def test_pruned_directories_are_never_descended_into(tmp_path, monkeypatch):
    """_scan_layers must prune skip dirs and dot-dirs from the walk itself, not
    just filter the results afterward.

    Wraps run.os.walk with a recorder that delegates to the real os.walk, so
    the walk's real behavior is unchanged and only observed. An impl that
    filters after a naive, unpruned walk would still yield dirpaths inside
    the skip/dot directories, which this test catches directly.
    """
    # The repo sits beneath a dot-prefixed ancestor (tmp_path/.cache/repo), not
    # directly under tmp_path: if the assertions below stopped scoping to
    # paths relative to the repo, the ancestor's ".cache" segment would show
    # up in every recorded dirpath and this test would fail.
    repo = tmp_path / ".cache" / "repo"
    repo.mkdir(parents=True)
    (repo / "src" / "node_modules" / "pkg").mkdir(parents=True)
    (repo / "src" / "node_modules" / "pkg" / "file.py").write_text("x = 1\n")
    (repo / "src" / ".venv" / "lib").mkdir(parents=True)
    (repo / "src" / ".venv" / "lib" / "file.py").write_text("x = 1\n")

    real_walk = run.os.walk
    recorded_dirpaths = []

    def _recording_walk(top, *args, **kwargs):
        for dirpath, dirnames, filenames in real_walk(top, *args, **kwargs):
            recorded_dirpaths.append(dirpath)
            yield dirpath, dirnames, filenames

    monkeypatch.setattr(run.os, "walk", _recording_walk)

    run._scan_layers(repo)

    for dirpath in recorded_dirpaths:
        # Relative to the repo: an absolute tmp base can itself contain a dot
        # segment or a _SKIP_DIRS name, which would fail a correct walk.
        parts = Path(dirpath).relative_to(repo).parts
        assert not any(part in run._SKIP_DIRS for part in parts), (
            f"walk descended into a skip dir: {dirpath}"
        )
        assert not any(part.startswith(".") for part in parts), (
            f"walk descended into a dot-directory: {dirpath}"
        )


def test_only_regular_files_enter_a_layer(tmp_path):
    """A layer holds regular files only, never a dangling symlink.

    os.walk reports every non-directory entry in `filenames`, dangling
    symlinks and special files included, so the walk needs its own is_file()
    filter. Without it they consume _FILE_CAP slots ahead of real source and
    reach read_text.
    """
    repo = tmp_path / "repo"
    repo.mkdir()
    (repo / "src").mkdir()
    (repo / "src" / "real.py").write_text("x = 1\n")
    (repo / "src" / "dangling.py").symlink_to(repo / "src" / "gone.py")

    names = [p.name for p in run._scan_layers(repo)[0]["src"]]

    assert names == ["real.py"], f"only regular files belong in a layer: {names}"


# ---------------------------------------------------------------------------
# _scan_layers: return shape and the 50-file-per-layer cap
# ---------------------------------------------------------------------------

def test_scan_layers_returns_dict_of_path_lists_and_bool_flag(tmp_path):
    """_scan_layers returns (layers, truncated): a dict of Path lists and a bool."""
    repo = tmp_path / "repo"
    repo.mkdir()
    (repo / "app").mkdir()
    (repo / "app" / "main.py").write_text("x = 1\n")

    result = run._scan_layers(repo)

    assert isinstance(result, tuple) and len(result) == 2
    layers, truncated = result
    assert isinstance(layers, dict)
    assert isinstance(truncated, bool)
    assert "app" in layers
    assert isinstance(layers["app"], list)
    assert all(isinstance(p, Path) for p in layers["app"]), \
        f"layer entries must be Path objects: {layers['app']}"
    assert truncated is False, "a single file must not trip the per-layer cap"


def test_scan_layers_caps_each_layer_at_50_files(tmp_path):
    """A layer with more than 50 files is capped at 50, and truncated is True."""
    repo = tmp_path / "repo"
    repo.mkdir()
    (repo / "many").mkdir()
    for i in range(60):
        (repo / "many" / f"mod_{i:03d}.py").write_text(f"x = {i}\n")

    layers, truncated = run._scan_layers(repo)

    assert len(layers["many"]) == 50, (
        f"layer must be capped at 50 files, got {len(layers['many'])}"
    )
    assert truncated is True, "exceeding the per-layer cap must report truncated=True"
