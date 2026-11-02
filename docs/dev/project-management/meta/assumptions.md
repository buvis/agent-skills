## 1: Add a spy regression for host-separator link text in fresh_clone

- `_template_on_disk` writes `calc.py` with the content `inside\n`. Taken from the existing assertion at line 754, not from reading the helper.
- `trees.os` is the global `os` module, so the red check patched `os.sep` for the whole process. `monkeypatch` undid it, and `_host_form` saw the same patched value.
- Targets were compared as a dict and the type flag was ignored, because the task asked only for the name-to-target mapping.
