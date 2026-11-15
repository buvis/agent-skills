"""Custom ABAP identifier extraction, shared by check_run.py and the review
skill's check_trust.py. One home for the Z, Y and /NAMESPACE/ regexes."""
from __future__ import annotations

import re


def ident_pattern(min_len: int) -> "re.Pattern[str]":
    """Custom ABAP identifiers: Z-prefixed, Y-prefixed (must contain an
    underscore, so ordinary Y-words in prose do not match), and
    /NAMESPACE/NAME. The namespace branch is case-sensitive so file paths
    like /usr/bin never match."""
    n = min_len
    return re.compile(
        r"(?<![A-Za-z0-9_/])(?:"
        r"Z[A-Z0-9_]{%d,}"
        r"|Y(?=[A-Z0-9]*_)[A-Z0-9_]{%d,}"
        r"|(?-i:/[A-Z][A-Z0-9_]{1,9}/)[A-Z0-9_]{%d,}"
        r")(?![A-Za-z0-9_])" % (n, n, max(n, 3)), re.I)


def custom_idents(text: str, min_len: int) -> list[str]:
    """Upper-cased custom identifiers found in text."""
    return [m.upper() for m in ident_pattern(min_len).findall(text)]
