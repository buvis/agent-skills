"""Export the pre-image of a fix commit for the sweep control check."""
import os
import subprocess
import time
from pathlib import PurePosixPath

REGULAR_FILE_MODES = (b"100644", b"100755")


def _git_output(repo, args, deadline_at, failure, stdin=None):
    """Run one read-only git command in `repo` and return its stdout bytes.
    Raises `subprocess.TimeoutExpired` once `deadline_at` (a
    `time.monotonic()` value) has passed, and `RuntimeError(failure: reason)`
    when git cannot run or exits non-zero."""
    remaining = deadline_at - time.monotonic()
    if remaining <= 0:
        raise subprocess.TimeoutExpired(["git", *args], 0)
    try:
        result = subprocess.run(
            ["git", "--no-optional-locks", "-C", str(repo), *args],
            input=stdin,
            capture_output=True,
            timeout=remaining,
        )
    except OSError as exc:
        raise RuntimeError(f"{failure}: {exc}") from exc
    if result.returncode != 0:
        reason = " ".join(result.stderr.decode(errors="replace").split())
        raise RuntimeError(f"{failure}: {reason}")
    return result.stdout


def _preimage_blobs(repo, commit, parent, deadline_at, failure):
    """`(blob id, path)` for each regular file `commit` changed, as it was in
    `parent`. Added files have no pre-image; symlinks and submodules are not
    files to search. Renames are split, so the old path is kept."""
    args = ["diff-tree", "-r", "-z", "--no-renames", "--no-abbrev", "--diff-filter=DMT"]
    raw = _git_output(repo, [*args, parent, commit], deadline_at, failure)
    fields = raw.split(b"\0")
    blobs = []
    for meta, path in zip(fields[0::2], fields[1::2]):
        old_mode, _new_mode, old_blob = meta.lstrip(b":").split(b" ")[:3]
        if old_mode in REGULAR_FILE_MODES:
            blobs.append((old_blob, os.fsdecode(path)))
    return blobs


def _export_preimage(repo, rev, dest, deadline_at):
    """Write every file `rev` changed, as it was in the first parent of `rev`,
    under `dest`. Uses only read-only git commands (rev-parse, diff-tree,
    cat-file), so the index, working tree and refs of `repo` never change.

    Raises `RuntimeError` with a one-line `sweep unverified: ...` message
    when `rev` does not resolve, has no parent, or cannot be exported, and
    `subprocess.TimeoutExpired` once `deadline_at` has passed."""
    where = f"control rev {rev} in {repo}"
    commit = _git_output(
        repo, ["rev-parse", "--verify", f"{rev}^{{commit}}"], deadline_at,
        f"sweep unverified: {where} does not resolve to a commit",
    ).decode().strip()
    parent = _git_output(
        repo, ["rev-parse", "--verify", f"{commit}^1"], deadline_at,
        f"sweep unverified: {where} has no parent, so it has no pre-image",
    ).decode().strip()
    failure = f"sweep unverified: could not export the pre-image of {where}"
    blobs = _preimage_blobs(repo, commit, parent, deadline_at, failure)
    if not blobs:
        return
    data = _git_output(
        repo, ["cat-file", "--batch"], deadline_at, failure,
        stdin=b"".join(blob + b"\n" for blob, _path in blobs),
    )
    pos = 0
    for _blob, rel in blobs:
        header_end = data.index(b"\n", pos)
        size = int(data[pos:header_end].split(b" ")[2])
        body = data[header_end + 1 : header_end + 1 + size]
        pos = header_end + 1 + size + 1
        if ".." in PurePosixPath(rel).parts:
            raise RuntimeError(f"{failure}: unsafe path {rel!r}")
        target = dest / rel
        try:
            target.parent.mkdir(parents=True, exist_ok=True)
            target.write_bytes(body)
        except OSError as exc:
            raise RuntimeError(f"{failure}: {exc}") from exc
