import os
import subprocess
import time


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


def _write_tree_shim(bin_dir, pid_dir, fast_repo_name="", fast_output="", tool="rg"):
    """Put a fake `tool` in bin_dir. Every run leaves shim-<pid> in pid_dir. A
    run whose cwd is named fast_repo_name prints fast_output and exits. Any
    other run forks a 10s `sleep` grandchild, leaves grandchild-<pid>, waits
    on it, and only then leaves finished-<pid> and exits 1 (no matches)."""
    script = "\n".join(
        [
            "#!/bin/sh",
            f': > "{pid_dir}/shim-$$"',
            f'if [ "$(basename "$(pwd -P)")" = "{fast_repo_name}" ]; then',
            f"  printf '%s' '{fast_output}'",
            "  exit 0",
            "fi",
            "sleep 10 &",
            f': > "{pid_dir}/grandchild-$!"',
            "wait",
            f': > "{pid_dir}/finished-$$"',
            "exit 1",  # "no matches" for both rg and ast-grep
            "",
        ]
    )
    shim = bin_dir / tool
    shim.write_text(script)
    shim.chmod(0o755)
    return shim


def _recorded_pids(pid_dir, role):
    return sorted(int(path.name.split("-")[1]) for path in pid_dir.glob(f"{role}-*"))


def _is_running(pid):
    # No `ps`: sandboxed runners may deny it. A killed shim that is our own
    # child can linger as a zombie, which signal 0 still reaches, so reap it
    # first; a zombie has already exited.
    try:
        if os.waitpid(pid, os.WNOHANG)[0] == pid:
            return False
    except ChildProcessError:
        pass
    try:
        os.kill(pid, 0)
    except ProcessLookupError:
        return False
    except PermissionError:
        return True
    return True


def _still_running_after(pids, grace):
    give_up = time.monotonic() + grace
    while True:
        running = [pid for pid in pids if _is_running(pid)]
        if not running or time.monotonic() >= give_up:
            return running
        time.sleep(0.05)
