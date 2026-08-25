# Python 3.10–3.14 Compatibility Table

Verified against Python 3.14, 2026-06-09. Python 3.10 reaches end-of-life in October 2026 and remains the correct floor until then.

## Added in 3.11 (unavailable on 3.10)

### New modules
| Module | Purpose | 3.10 alternative |
|--------|---------|-----------------|
| `tomllib` | TOML parsing | `tomli` (pip install) |
| `wsgiref.types` | WSGI type hints | define manually |

### New builtins/constants
| Feature | 3.10 alternative |
|---------|-----------------|
| `datetime.UTC` | `datetime.timezone.utc` |
| `ExceptionGroup` / `BaseExceptionGroup` | `exceptiongroup` backport |
| `except*` syntax | not available; use sequential except |
| `TaskGroup` (asyncio) | `anyio.create_task_group()` or backport |
| `asyncio.Runner` | `asyncio.run()` or manual loop |
| `asyncio.Barrier` | `anyio` or manual |

### datetime behavior changes
| Feature | 3.10 behavior | 3.11+ behavior |
|---------|--------------|----------------|
| `fromisoformat()` | rejects many ISO 8601 formats | accepts most ISO 8601 |
| `fromisoformat("...+0530")` | raises ValueError (no colon) | works |
| **Fix**: use `strptime(s, "%Y-%m-%dT%H:%M:%S%z")` on 3.10 |

### Typing additions
| Feature | 3.10 alternative |
|---------|-----------------|
| `Self` (PEP 673) | `TypeVar('T', bound='ClassName')` |
| `LiteralString` (PEP 675) | not available |
| `TypeVarTuple` (PEP 646) | `typing_extensions` |
| `Required`/`NotRequired` (PEP 655) | `typing_extensions` |
| `@dataclass_transform()` (PEP 681) | `typing_extensions` |

### Behavioral differences
| Behavior | 3.10 | 3.11+ |
|----------|------|-------|
| Context manager without protocol | `AttributeError` | `TypeError` |
| `int("1"*5000)` | works | `ValueError` (4300 digit limit) |
| `math.pow(0.0, -inf)` | `ValueError` | returns `inf` |
| Flag enum composites | canonical values | treated as aliases |

## Added in 3.12 (unavailable on 3.10, 3.11)

### New syntax
| Feature | 3.10/3.11 alternative |
|---------|----------------------|
| `type X = int` (PEP 695) | `X: TypeAlias = int` |
| `def foo[T](x: T)` (PEP 695) | explicit `TypeVar` |
| `class Foo[T]:` (PEP 695) | explicit `TypeVar` + `Generic[T]` |
| f-string quote reuse: `f"{','.join(x)}"` | use different quotes or variables |
| f-string backslashes: `f"{'\n'.join(x)}"` | assign to variable first |
| f-string nesting: `f"{f"{x}"}"` | avoid nesting |
| f-string comments in multiline | not allowed |

### Removed modules (existed in 3.10/3.11, gone in 3.12)
| Module | Alternative |
|--------|------------|
| `distutils` | `setuptools` |
| `asynchat` | `asyncio` |
| `asyncore` | `asyncio` |
| `imp` | `importlib` |
| `smtpd` | `aiosmtpd` |

### Deprecated in 3.12 (still works but warns)
| Feature | Alternative |
|---------|------------|
| `datetime.utcnow()` | `datetime.now(tz=UTC)` |
| `datetime.utcfromtimestamp()` | `datetime.fromtimestamp(tz=UTC)` |
| `typing.Hashable` | `collections.abc.Hashable` |
| `typing.Sized` | `collections.abc.Sized` |
| `typing.ByteString` | `bytes \| bytearray` |
| `sys.last_type/value/traceback` | `sys.last_exc` |
| `calendar.January/February` | `calendar.JANUARY/FEBRUARY` |
| `~True` (bitwise invert bool) | `not True` |
| `gen.throw(typ, val, tb)` 3-arg | `gen.throw(exception)` |
| `shutil.rmtree(onerror=...)` | `shutil.rmtree(onexc=...)` |
| `tarfile.extract()` without filter | specify `filter='data'` |

### Behavioral differences
| Behavior | 3.10/3.11 | 3.12 |
|----------|-----------|------|
| `isinstance(list[int], type)` | `True` | `False` |
| `isinstance()` with runtime protocols | calls `hasattr`/descriptors | uses `getattr_static` |
| Comprehension in traceback | separate frame | inlined |
| `locals()` in comprehension | only comprehension vars | includes outer scope |
| `__set_name__` exception | wrapped in `RuntimeError` | propagates directly |
| Invalid escape `"\d"` | `DeprecationWarning` | `SyntaxWarning` |

### Pydantic-specific (3.10)
| Issue | Details |
|-------|---------|
| Locally-defined models | Pydantic can't resolve forward refs for models defined inside functions on 3.10. Define at module level. |
| `list[X]` as type | `isinstance(list[X], type)` differs across versions. Always use `get_origin()` to check parameterized generics. |

## Added in 3.14 (unavailable on 3.10, 3.11, 3.12, 3.13)

### New syntax
| Feature | pre-3.14 alternative |
|---------|----------------------|
| `t"..."` template strings (PEP 750) — `t` prefix returns `string.templatelib.Template` preserving static parts and interpolations separately | No backport; use f-strings or explicit string building |
| `SyntaxWarning` for `return`/`break`/`continue` leaving a `finally` block (PEP 765) | Code that does this already silently misbehaves on all versions; warning is new in 3.14 |

### New modules
| Module | Purpose | pre-3.14 alternative |
|--------|---------|----------------------|
| `annotationlib` | Introspect deferred annotations (PEP 749); `Format.VALUE`, `Format.FORWARDREF`, `Format.STRING` | `typing.get_type_hints()` |
| `compression` | Package re-exporting `lzma`, `bz2`, `gzip`, `zlib` under canonical names (old names not deprecated) | Import from original module names |
| `compression.zstd` | Zstandard compression/decompression (PEP 784) | `zstandard` PyPI package |
| `concurrent.interpreters` | Multiple Python interpreters in same process for true multi-core parallelism (PEP 734) | `multiprocessing` for parallelism |
| `string.templatelib` | Runtime types for t-string objects (`Template`, `Interpolation`) | No equivalent |

### Removed APIs
| Removed | Deprecated since | Alternative |
|---------|-----------------|-------------|
| `ast.Bytes`, `ast.Ellipsis`, `ast.NameConstant`, `ast.Num`, `ast.Str` | 3.8 (warnings since 3.12) | `ast.Constant`; replace `visit_Num` etc. with `visit_Constant` |
| `ast.Constant.n`, `ast.Constant.s` | 3.12 | `ast.Constant.value` |
| `asyncio` child watcher API (`AbstractChildWatcher`, `FastChildWatcher`, `PidfdChildWatcher`, `SafeChildWatcher`, `ThreadedChildWatcher`, `get_child_watcher()`, `set_child_watcher()`) | 3.12 | Child watcher concept removed; no direct replacement |
| `pkgutil.get_loader()`, `pkgutil.find_loader()` | 3.12 | `importlib.util.find_spec()` |

### Behavioral changes
| Behavior | Before 3.14 | In 3.14 | Safe fallback |
|----------|------------|---------|---------------|
| Annotations evaluation | Eager at definition time (unless `from __future__ import annotations`) | Deferred by default — stored in annotate functions, evaluated only on demand | Use `typing.get_type_hints()` for runtime access on all versions |
| `asyncio.get_event_loop()` with no current loop | Implicitly created a new loop | Raises `RuntimeError` | Use `asyncio.run()` instead |
| `multiprocessing` default start method on Linux/non-macOS Unix | `'fork'` | `'forkserver'` | Explicitly call `multiprocessing.set_start_method('fork')` or `get_context('fork')` |
| `ProcessPoolExecutor` default start method (Linux/non-macOS Unix) | `'fork'` | `'forkserver'` | Pass `mp_context=multiprocessing.get_context('fork')` |
| `functools.partial` in class body | Not a method descriptor | Now a method descriptor — behaves like a bound method | Wrap with `staticmethod()` to preserve old behavior |
| `typing.Union` / `types.UnionType` identity | Two separate types; cached, `Union[int,str] is Union[int,str]` was `True` | `types.UnionType` is alias for `typing.Union`; unions no longer cached | Use `==` not `is` for union comparison on all versions |
| `repr(Union[int, str])` | `"typing.Union[int, str]"` | `"int \| str"` | Don't rely on repr for type comparison |

### Typing additions
| Feature | pre-3.14 alternative |
|---------|----------------------|
| `annotationlib` with `Format.VALUE`, `Format.FORWARDREF`, `Format.STRING` for controlled annotation evaluation | `typing.get_type_hints()` |

## Removed in 3.13 (work on 3.11/3.12 but emit warnings there)

PEP 594 "dead battery" modules: `aifc`, `audioop`, `cgi`, `cgitb`, `chunk`, `crypt`, `imghdr`, `mailcap`, `msilib`, `nis`, `nntplib`, `ossaudiodev`, `pipes`, `sndhdr`, `spwd`, `sunau`, `telnetlib`, `uu`, `xdrlib`.

Also removed in 3.13: `lib2to3` / `2to3` (deprecated 3.11) — manual migration.

## Safe patterns across 3.10–3.14

```python
# TOML parsing
try:
    import tomllib
except ModuleNotFoundError:
    import tomli as tomllib

# UTC timezone
from datetime import timezone
UTC = timezone.utc  # works everywhere

# ISO format parsing
from datetime import datetime
def parse_iso(s: str) -> datetime:
    try:
        return datetime.fromisoformat(s)
    except ValueError:
        return datetime.strptime(s, "%Y-%m-%dT%H:%M:%S%z")

# Type checking parameterized generics
from typing import get_origin
def is_generic(tp) -> bool:
    return get_origin(tp) is not None

# Self type (with future annotations)
from __future__ import annotations
from typing import TypeVar
T = TypeVar('T', bound='MyClass')
class MyClass:
    def method(self: T) -> T: ...
```
