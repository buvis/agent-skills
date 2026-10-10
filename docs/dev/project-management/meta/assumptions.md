## 1: Make memory and pointer publication idempotent while preserving 00017's guarded rollback

- `published` returns the bool singletons, so the tests use `is True` / `is False`. (Tess)
- A non-UTF-8 file is enough to trigger "unreadable" for both the target and the index; no chmod-based OSError case. (Tess)
- On a second run of an identical new entry, `main` prints `MEMORY.md: unchanged` as its second stdout line, since `append_pointer` returns None and `main` is unchanged. (Tess)
- An atomic replace changes the inode on APFS, so an unchanged inode and mtime prove no write. (Tess)
- An update with a changed description and no index line for its stem takes the same append path as a new entry. (Tess, strengthen)
- Added two helpers not named in the design, `_holds_text` and `_index_lines`, each with two callers, so `write_memory` and `published` share one read and refusal. (Ivan)
- `published` does not run the `existing_text` envelope check; the design requires it only for `append_pointer`. (Ivan)
- `published` parses the description before checking files, so a malformed `file_text` raises ProposalError even when the target is absent. (Ivan)

## 2: Guard a null kind in write.py main

- "Reason on stderr" means the `str(exc)` of the caught error; the test takes the expected text from `proposal.updated_name(kind)` rather than hardcoding wording. (Tess)
- Kinds 42, [] and {} are in-contract, since the contract catches `AttributeError`, not only `None`. (Tess)
- Patching `pathlib.Path` write/replace/unlink to fail counts as mocking the filesystem boundary. (Tess)

## 3: Let decide re-decide a kept entry with --name and --file, and add unpublished

- Took the `write.write_memory`/`append_pointer`/`published` signatures and the `"update <stem>"` kind format from `test_write.py`, outside the dispatch read list. (Tess)
- The `<store>` in `cannot check the store <store>: ` is the `--store` string exactly as given. (Tess)
- The WriteError for an unreadable index or target names the file's path. (Tess)
- The acceptance-named decide tests live in `test_docket_cli.py` as CLI tests; the function-level versions in `test_docket.py` carry different names. (Tess)
- `write.WriteError` is not one of the envelope-fault types, so the fault handler cannot swallow it. (Ivan)
- A faulted envelope gets its own group keyed by the tuple `("unreadable envelope", id)`, which can never equal a string stem. (Ivan)

## 4: Rewrite SKILL.md steps 5 to 7 and add collision-rename and pointer-retry integration tests

- `write.main` may return its exit code or raise SystemExit, so the test helper handles both. (Tess)
- The collision message is checked loosely: stderr contains `shared-memory.md` and `already exists`. (Tess)
- `session_decided` after the rename is not checked; only `cursor` is. (Tess)
- "List every id still printed, with its write's stderr" means every confirmed id; declined ids go in their own list. (Ivan)
- A store-check failure (exit 1, empty stdout) is reported inside the sitting report and does not block it; only exit 2 blocks the report. (Ivan)
- No guidance on re-asking about a declined id in later passes; the contract is silent. (Ivan)
