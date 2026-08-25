---
name: rust-patterns
description: Use when writing, reviewing, or refactoring Rust code. Covers ownership, errors, traits, naming, module layout, toolchain, security, and platform traps. Triggers on Rust file edits, "idiomatic rust", "cargo audit", "unsafe", "maturin".
compatibility: "Portable standalone compatibility copy of the strunk plugin skill for agents without that plugin; Claude Code uses the namespaced plugin skill."
---

# Rust Patterns

Pick a side. These are the rulings, not a tutorial.

## Core opinions

| Rule | Why |
|------|-----|
| Borrow, don't clone | Pass `&T` unless you must own. |
| Make illegal states unrepresentable | Model only valid states with enums. |
| `?` over `unwrap()` | Propagate; never panic in production paths. |
| Parse, don't validate | Convert unstructured input to typed structs at the boundary. |
| Newtype for type safety | Wrap primitives so arguments can't be swapped. |
| Iterators over loops | Declarative chains are clearer and often faster. |
| `#[must_use]` on `Result`-like returns | Force callers to handle them. |
| `Cow<'_, T>` for maybe-owned data | Skip allocation when borrowing suffices. |
| Exhaustive matching | No wildcard `_` on business-critical enums — the compiler should force new variants on you. |
| Minimal `pub` surface | `pub(crate)` for internals; re-export the public API from `lib.rs`. |

## Pick-a-side calls

- **Errors:** `thiserror` when callers must match on error variants (usually libraries); `anyhow` when errors are only reported or logged (usually apps). Not a hard split — they compose: `thiserror` types wrapped by `anyhow` at the boundary.
- **Polymorphism:** generics when types are known at compile time (no vtable); trait objects (`dyn`) for heterogeneous collections, plugins, or runtime-selected types.
- **API shape:** accept generic inputs (`impl IntoIterator`). Return a named concrete type from public library APIs (callers can't depend on `impl Trait` internals); `impl Iterator` is fine for app or internal code.
- **Builders:** once a struct mixes required and optional fields (3+), use a builder, not a 6-argument `new`.
- **Concurrency:** channels to pass values between independent tasks; `Arc<Mutex<T>>` only for short-lived shared mutable state.

## Unsafe

Every `unsafe` block gets a `// SAFETY:` comment above it stating the invariant and why it holds. No comment, no merge.

- Minimise `unsafe`; reach for a safe abstraction first.
- Never use `unsafe` to get past the borrow checker for convenience.
- Audit every `unsafe` block during review.

## Toolchain

`cargo fmt` before every commit; `cargo clippy -- -D warnings` (warnings are errors). 4-space indent, 100-column max — both rustfmt defaults worth stating because a 120-col override is the usual drift.

## Naming

| Kind | Case |
|------|------|
| functions, methods, variables, modules, crates | `snake_case` |
| types, traits, enums, type parameters | `PascalCase` |
| constants, statics | `SCREAMING_SNAKE_CASE` |
| lifetimes | short lowercase (`'a`, `'de`) |

Organize modules by **domain, not by type** — `auth/`, `orders/`, `db/`, each with its own `mod.rs`. Never a `models/` + `services/` + `handlers/` split.

## API surface

- `let` by default; `let mut` only where mutation is required.
- Take `&str`, not `String`; `&[T]`, not `Vec<T>` — in function parameters. "Pass `&T`" is not enough: `&String` and `&Vec<T>` still force the caller to own a heap allocation you never needed.
- `impl Into<String>` for constructors that must own a `String` — callers pass `&str` or `String` and neither allocates twice.
- Add context on the way up: `.with_context(|| format!("failed to read {path}"))?`. An error without the path it failed on is a bug report you cannot action.
- **Sealed traits** — put a `Sealed` supertrait in a private module to block external implementations of a trait you must stay free to extend.
- A repository is a **trait**, and it carries `Send + Sync` the moment it crosses a thread or an async runtime — which, for a repository, is always. `pub trait OrderRepository: Send + Sync`.

## Security

- Secrets come from the environment (`std::env::var`), never a `const` in source.
- Parameterized queries only: `sqlx::query("... WHERE name = $1").bind(&name)`. Never `format!` a value into SQL.
- `cargo audit` (known CVEs), `cargo deny check` (licenses + advisories), `cargo tree -d` (duplicate deps).
- Never return internal paths, stack traces, or database errors to a client. Log the detail server-side; return a generic message.

## Platform traps

**macOS + maturin:** after building a `.so`, `syspolicyd` can block it silently — Python hangs on import, then dies by SIGKILL with no error. Fix: `codesign -f -s - path/to/_core.*.so` after the build. When a native extension import hangs, check code signing first.
