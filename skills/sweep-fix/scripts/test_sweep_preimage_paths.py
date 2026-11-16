"""Pre-image exports reject paths that can leave their destination on either OS."""

import time
from pathlib import Path

import pytest

import sweep_preimage


@pytest.mark.parametrize(
    "rel",
    ["../escape.py", r"..\escape.py", r"C:\escape.py", r"\escape.py",
     "C:escape.py", r"dir\..\..\escape.py", r"\\server\share\escape.py"],
)
def test_export_rejects_paths_unsafe_on_windows_or_posix(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch, rel: str,
) -> None:
    blob = b"a" * 40
    body = b"untrusted content\n"
    outputs = iter([
        b"b" * 40 + b"\n",
        b"c" * 40 + b"\n",
        b":100644 100644 " + blob + b" " + b"d" * 40 + b" M\0"
        + rel.encode() + b"\0",
        blob + b" blob " + str(len(body)).encode() + b"\n" + body + b"\n",
    ])

    def git_output(*args: object, **kwargs: object) -> bytes:
        return next(outputs)

    monkeypatch.setattr(sweep_preimage, "_git_output", git_output)
    dest = tmp_path / "preimage"
    dest.mkdir()

    with pytest.raises(RuntimeError, match="unsafe path"):
        sweep_preimage._export_preimage(tmp_path, "HEAD", dest, time.monotonic() + 10)

    assert list(dest.iterdir()) == []
    assert not (tmp_path / "escape.py").exists()
