---
name: python-patterns
description: Use when writing, reviewing, or refactoring Python code. Covers idioms, naming, traps, toolchain, and security. Triggers on Python file edits, "pythonic", "PEP 8", "python best practices", "python idioms", "bandit".
compatibility: "Portable standalone compatibility copy of the strunk plugin skill for agents without that plugin; Claude Code uses the namespaced plugin skill."
---

# Python Patterns

Pick a side. These are the rulings, not a tutorial.

## Idioms that earn their place

| Rule | Why |
|------|-----|
| `X \| Y`, not `Union[X, Y]` | 3.10+ runtime syntax; clearer. On 3.9 it parses only under `from __future__ import annotations` and still breaks `get_type_hints`/`isinstance` — keep `Optional`/`Union` if you support 3.9. |
| `Protocol`, not `ABC`, for duck typing | Structural typing; no inheritance you don't control. |
| `@dataclass(frozen=True)` for immutable records, plain `dataclass` only when you must mutate, `NamedTuple` for lightweight immutable rows | Pydantic only when you need validation. |
| `raise New(...) from e` | Marks the explicit cause. A bare `raise New()` still chains implicitly ("During handling..."); use `from None` to suppress. |
| `@functools.wraps` on every decorator | Without it the wrapper loses `__name__`, `__doc__`, signature. |
| `pathlib.Path`, not `os.path` | One object, no string surgery. |

## Naming (PEP 8)

`snake_case` for modules, functions, variables. `CapWords` for classes. `UPPER_SNAKE_CASE` for constants. Leading `_` for internal names.

**Never name a `.py` file in kebab-case.** `my-script.py` is not importable (`import my-script` is a `SyntaxError`). Kebab-case belongs only in the `pyproject.toml` distribution name and the CLI command, both of which map to a `snake_case` module.

## Traps

```python
# Mutable default argument — shared across calls
def bad(items=[]): ...
def good(items=None):
    items = [] if items is None else items

# Bare except — swallows SystemExit, KeyboardInterrupt
try: ...
except Exception as e: ...        # name the exception

# __slots__ kills __dict__ and dynamic attributes — use only on fixed,
# memory-sensitive classes you won't extend.

# __double_leading is name-mangled to _Class__double_leading.
# Surprises you in subclasses, pickling, and monkey-patching.

if value is None: ...             # never == None
```

Avoid `from module import *`. Use `isinstance`, never `type(x) ==`.

## Toolchain

**black** to format, **isort** for imports, **ruff** to lint. Type annotations on every function signature — no exceptions for "obvious" returns.

## Resources and laziness

Context managers (`with`) for anything holding a resource. Generators for lazy iteration over anything you would otherwise materialize into a list.

## Security

- Read secrets with `os.environ["API_KEY"]`, never `.get()` — a missing secret must raise `KeyError` at startup, not surface as `None` at request time.
- `python-dotenv` loads a local `.env` in development only. Never commit one.
- `bandit -r src/` for static security analysis.
