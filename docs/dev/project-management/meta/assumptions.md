# Assumptions ledger — PRD 00131-crafted-template-archive-escapes-directory-v1

## 1: Fix build_template's duplicate-member/symlink-ancestor containment preflight

- `./escape` and `escape` count as "normalize to the same path" (Tess).
- On refusal, `dest` may exist but must be empty, as in the existing tests (Tess).
- The safe-seal test with a crafted archive is fine to keep, as the accept case that matches the refusal tests (Tess).
- The helper returns `None`, not the link map the design docstring mentions, because nothing uses that map (Ivan; the design review log raised this too — not acted on further since it does not affect correctness).
- Hardlink members are not handled separately; no test covers them (Ivan — matches the design's own "Likely next change 1" scoping note).

## 2: Cover finding 42: explicit safe extraction removes the omitted-filter deprecation warning

- Interpreted "the specific omitted-filter deprecation warning" as the message tarfile actually raises on this repo's pinned Python (3.12.16): "Python 3.14 will, by default, filter extracted tar archives and reject files or modify their metadata. Use the filter argument to control this behavior." Matched on a literal prefix substring (Ivan).
- Interpreted "treats ... as an error" as scoped per-branch: the `filter="data"` branch must never raise it (regression detector), while the compatibility branch is expected to raise it (explicit documentation of known, currently-accepted behavior) — rather than expecting zero warnings on both branches, since direct experimentation showed the compatibility branch genuinely triggers the warning under the current, correct implementation (Ivan).
- Reused the existing safe-link crafted-archive fixture shape (`pkg` dir + file + an internal symlink `escape -> pkg`) from `test_build_template_seals_a_crafted_archive_with_unique_safe_members` to satisfy "confirm safe-link controls still pass, including the compatibility path," rather than inventing a new archive shape (Ivan).

## 3/4 (rework, cycle 1): [D1] skills/use-qwen/scripts/test_eval_tree_links.py

- Fixing the pre-existing `test_build_template_seals_a_safe_tree_with_or_without_tar_data_filter[without-data-filter]` failure (same root-cause `delattr` bug, not explicitly named in either finding) was treated as in scope, since the task's own verification command runs the whole file and both findings are framed as "fix the unsafe `data_filter`-hiding approach" (Ivan).
- Dropped the `warnings.catch_warnings`/`filterwarnings("error")` instrumentation in the renamed compatibility-path test entirely, rather than keeping it and expecting no exception, because keeping `filterwarnings("error")` would turn the real (on Python 3.13) `DeprecationWarning` into a hard test failure there — incompatible with this project's 3.10/3.13 CI matrix (Ivan).
