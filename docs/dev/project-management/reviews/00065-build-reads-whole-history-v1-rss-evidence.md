# PRD 00065 — post-change RSS evidence (bounded history retention)

## What this is

Observational evidence that `_load_history` in
`skills/brief-portfolio/scripts/build.py` no longer scales memory with
`history.jsonl` size, after the bounded-deque fix. This is **not** an exact
allocator-dependent equality against the PRD's pre-change numbers — those
numbers were taken with different (larger, more realistic) synthetic rows and
are quoted below for context only. The point of this measurement is the
shape of the curve (flat vs. growing with input size), not matching a
specific MB figure.

## HEAD sha

`0a66f5aa4b6407f6d13496cb5604bd34f5d08e48`

plus one uncommitted working-tree change to `build.py` at measurement time:
the same task's Piece 1 refactor, which rewrites `_load_history`'s bounded
window from a mutable `deque(maxlen=60)` + append loop into the PRD's
contract expression (`deque((...) for ... in enumerate(...) if ...)`)
constructed inside the `with` block. That refactor is behavior-preserving
(same one-pass scan, same 60-row bound, same physical line numbering); the
bounded-retention algorithm itself was already in place at this sha via an
earlier commit (`4f43c56`, "stream history.jsonl's tail through a bounded
deque instead of reading the whole file").

## Method

A throwaway harness at `dev/local/tmp/rss-measure-00065.py` (gitignored, not
committed) does, for each row count:

1. Write a synthetic `history.jsonl` with N rows, each row
   `{"at": "2026-09-26T00:00:00Z", "skipped": 0, "repos": {}}` — the shape
   the existing tests use.
2. Spawn a subprocess that loads `build.py` by path (avoids the two
   same-named `build.py` files elsewhere in this repo colliding via
   `sys.modules`), calls `_load_history(workdir)` against that file, and has
   the *child itself* report `resource.getrusage(resource.RUSAGE_SELF).ru_maxrss`.

Command actually run (from the repo root):

```
python3 dev/local/tmp/rss-measure-00065.py
```

**Unit**: this host is macOS (darwin), so `ru_maxrss` is **bytes**, not
kilobytes (Linux would report kilobytes for the same field).

## Result (two runs, to gauge noise)

| rows   | file bytes | run 1 peak RSS | run 2 peak RSS |
|--------|-----------:|---------------:|---------------:|
| 1 000  |     58 000 |   19.86–20.50 MB |        19.86 MB |
| 10 000 |    580 000 |   19.89–19.96 MB |        19.96 MB |

Raw run 1: `rows=1000 peak_rss_bytes=20496384 peak_rss_MB=20.50 file_bytes=58000`,
`rows=10000 peak_rss_bytes=19890176 peak_rss_MB=19.89 file_bytes=580000`.

Raw run 2: `rows=1000 peak_rss_bytes=19857408 peak_rss_MB=19.86 file_bytes=58000`,
`rows=10000 peak_rss_bytes=19955712 peak_rss_MB=19.96 file_bytes=580000`.

## Reading

Peak RSS is flat (~20 MB, +/- ~0.6 MB run-to-run noise, which is Python
interpreter/import baseline, not signal) across a 10x increase in row count
(1 000 -> 10 000) and a 10x increase in file size (58 KB -> 580 KB). It does
**not** grow with input size the way the PRD's PRE-change figures did (36 MB
at 1 000 rows vs. 119 MB at 10 000 rows, having read 2 922 890 and
29 238 890 bytes respectively — quoted from the PRD for comparison only;
those synthetic rows were far larger per-line than the compact rows used
here, so the byte-count columns are not directly comparable, only the
growth-vs-flat shape is). A flat curve as input scales 10x is the expected
signature of the 60-row bounded window: retention no longer tracks file
size. This is reported as observational evidence, not as a claim that any
of these MB figures are reproducible to the byte on another allocator or
Python build.
