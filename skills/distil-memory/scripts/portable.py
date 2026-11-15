"""Transcript paths as they are written into published artefacts, and back.

Artefacts land in a public repository, so a path under the operator's home is
written home-relative (`~/...`, always with forward slashes) instead of with
the absolute home prefix. A path outside the home names no person and is
written unchanged. Readers expand `~/` deliberately at the point they open or
compare a path, and still accept the absolute records older runs wrote.

Stdlib only: docket.py's queue verbs import this and must stay light.
"""

from pathlib import Path

_HOME_MARK = "~/"


def portable_text(path: str) -> str:
    """`path` with the operator's home prefix replaced by `~/`.

    The home is matched by whole path components, so a sibling such as
    `<home>-other/x` is left alone. Text already home-relative, relative, or
    outside the home comes back unchanged.
    """
    if path.startswith(_HOME_MARK):
        return path
    candidate = Path(path)
    if not candidate.is_absolute():
        return path
    try:
        rest = candidate.relative_to(Path.home())
    except ValueError:
        return path
    return _HOME_MARK + rest.as_posix()


def local_path(text: str) -> Path:
    """The local path a serialized transcript reference names: `~/...` is
    expanded against this machine's home, anything else (a legacy absolute
    record, a relative path) is taken as written."""
    if text.startswith(_HOME_MARK):
        return Path.home() / text[len(_HOME_MARK) :]
    return Path(text)
