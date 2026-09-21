"""Pieces shared by the collect test modules.

`test_collect.py` was split into four per-concern modules, so they need the
same fixture builders. They live here rather than in one of those modules
because a test module is not a fixture library: importing one test module
from another is the shape the funnel family removed when
`funnel_test_helpers.py` was created.
"""

import json
import subprocess
import sys
from pathlib import Path

import collect
from collect import main


def write_report(tmp_path: Path, body: str) -> None:
    report = tmp_path / "dev/local/audit-results/brush-report.md"
    report.parent.mkdir(parents=True)
    report.write_text(body)


def make_registry(tmp_path: Path, names) -> list:
    """Create a fake gita registry: one directory with a .git marker per name."""
    root = tmp_path / "repos"
    paths = []
    for name in names:
        d = root / name
        (d / ".git").mkdir(parents=True)
        paths.append(str(d))
    return paths


def write_registry_csv(tmp_path: Path, paths) -> Path:
    csv_path = tmp_path / "repos.csv"
    csv_path.write_text("\n".join(paths) + "\n")
    return csv_path


def make_fake_run(skip_cwds):
    """collect.run replacement: resolvable repos get a valid github remote,
    skip_cwds fail repo_slug, and every gh call fails (unauthenticated)."""

    def fake_run(cmd, cwd=None, timeout=120):
        if cmd[0] == "git" and cmd[1] == "remote":
            if str(cwd) in skip_cwds:
                raise RuntimeError("not a github remote: bad-url")
            return f"git@github.com:acme/{Path(cwd).name}.git\n"
        if cmd[0] == "gh":
            raise RuntimeError("gh: not authenticated")
        raise AssertionError(f"unexpected command: {cmd}")

    return fake_run


def run_collector(tmp_path, monkeypatch, resolvable_names, skip_names):
    paths = make_registry(tmp_path, resolvable_names + skip_names)
    skip_paths = {str(tmp_path / "repos" / name) for name in skip_names}
    monkeypatch.setattr(collect, "run", make_fake_run(skip_paths))
    monkeypatch.setattr(collect, "GITA_CSV", write_registry_csv(tmp_path, paths))
    out_dir = tmp_path / "out"
    monkeypatch.setattr(
        sys,
        "argv",
        ["collect.py", "--no-git-fetch", "--out", str(out_dir)],
    )
    main()
    return paths, out_dir


def write_data_json_fixture(path: Path, generated_at: str, marker: str) -> str:
    """Write a minimal data.json-shaped fixture and return its exact text,
    so callers can assert byte-for-byte preservation later."""
    content = json.dumps({"generated_at": generated_at, "marker": marker}, indent=1)
    path.write_text(content)
    return content


def make_trash_dir(tmp_path: Path, *, dirs=(), files=()) -> Path:
    """Build tmp_path/dev/local/.trash/ with the given subdirectory and file
    names created directly inside it."""
    trash = tmp_path / "dev/local/.trash"
    trash.mkdir(parents=True)
    for name in dirs:
        (trash / name).mkdir()
    for name in files:
        (trash / name).write_text("")
    return trash


def make_git_repo(path: Path, commits: int) -> None:
    """A real repository with `commits` empty commits and origin/master at HEAD."""
    git = ["git", "-c", "user.name=t", "-c", "user.email=t@example.com", "-C", str(path)]
    path.mkdir()
    subprocess.run(git + ["init", "-q", "-b", "master"], check=True)
    for n in range(commits):
        subprocess.run(git + ["commit", "-q", "--allow-empty", "-m", f"c{n}"], check=True)
    subprocess.run(git + ["update-ref", "refs/remotes/origin/master", "HEAD"], check=True)
