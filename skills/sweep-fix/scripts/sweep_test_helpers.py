import subprocess


def _make_repo(root):
    """Create a directory with a `.git` marker so it passes the repo check."""
    (root / ".git").mkdir(parents=True)
    return root


def _write_registry(path, rows):
    lines = "\n".join(rows)
    path.write_text(lines + "\n" if lines else "")


def _init_git_repo_with_tracked_files(root, tracked, untracked=()):
    root.mkdir(parents=True, exist_ok=True)
    subprocess.run(["git", "init", "-q"], cwd=str(root), check=True, capture_output=True)
    for rel in tracked:
        file_path = root / rel
        file_path.parent.mkdir(parents=True, exist_ok=True)
        file_path.write_text("content\n")
    subprocess.run(
        ["git", "-C", str(root), "add", *tracked], check=True, capture_output=True
    )
    for rel in untracked:
        file_path = root / rel
        file_path.parent.mkdir(parents=True, exist_ok=True)
        file_path.write_text("untracked\n")
    return root


def _plant_matches(repo, pattern, count, ext=".txt"):
    """Create `repo` with `count` files, each containing one line matching `pattern`."""
    repo.mkdir(parents=True, exist_ok=True)
    for i in range(count):
        (repo / f"match_{i:03d}{ext}").write_text(f"{pattern} line {i}\n")
    return repo


def _git_status_porcelain(repo):
    return subprocess.run(
        ["git", "-C", str(repo), "status", "--porcelain"],
        capture_output=True,
        text=True,
        check=True,
    ).stdout
