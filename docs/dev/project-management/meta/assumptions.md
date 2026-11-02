## 1: Add a spy regression for host-separator link text in fresh_clone

- `_template_on_disk` writes `calc.py` with the content `inside\n`. Taken from the existing assertion at line 754, not from reading the helper.
- `trees.os` is the global `os` module, so the red check patched `os.sep` for the whole process. `monkeypatch` undid it, and `_host_form` saw the same patched value.
- Targets were compared as a dict and the type flag was ignored, because the task asked only for the name-to-target mapping.

## 2: Convert clone link text to the host separator in _copytree_links_typed

- The Windows-only test (task 1's regression) is the one this task targets. It is the only test in the commit, and nothing fails on this host.
- On Windows, `os.readlink` returns a relative target with the same separators it was created with, so converting `/` to the host separator gives the expected form.
- Call order across links is not part of the contract, so the strengthened test's comparison is `sorted(calls) == sorted(expected)`, which still counts duplicates. This matches the sibling typing test just above it.
- `same -> alias/calc.py` should be typed as a file (`False`), because its chain resolves to the regular file `calc.py`.
