# Task 6 - ddb / cap frontmatter size at the parse boundary

Stage A prospect 6. Verdict: **eligible**, at the narrowed `parser/` scope (see
"Scope narrowing").

Stage B first disqualified this candidate on `interface_pinned` and wrote it up
as `tasks/dq-cap-frontmatter-size.vetting.md`. Retry 1's Decision 1 gives every
prompt an interface-pins block, which closes the one gap, so the candidate is
re-admitted and that `dq-` note is superseded by this one (its substance is
folded in below, under "Why this needed pinning").

Kind: impl+test

Repo: `/Users/bob/git/src/github.com/doogat/ddb` (Rust)
PRD: `dev/local/prds/done/00169-poison-file-reindex-resilience-v1.md:175`

Commit run: `38577e7..b1bc2ed` (3 commits: `38577e7` test, `7d28653` feat,
`b1bc2ed` test tidy)
Parent of `<first>` (`38577e7^`): `e5ec64a`
Base sha (`HEAD` at vetting time): `8fe51c9d3fcee53a1ef14b2955083fd6a07977eb`

## Reverifiability

Working tree clean at `<base-sha>`: `git -C <src> status --porcelain` printed
nothing; control `git -C <src> status --porcelain --branch` printed
`## master...origin/master`.

Raw test command:

    cargo test --manifest-path <tree>/Cargo.toml -p ddb-core --lib parser

Run once at `<base-sha>` against the source tree: **exit 0**,
`97 passed; 0 failed; 0 ignored; 0 measured; 1449 filtered out`. (Run with
`--quiet` appended for output brevity; the same 97 cases also pass inside the
unfiltered `-p ddb-core --lib` run recorded in `alt1`'s note.)

## Required files

- `ddb-core/src/parser/mod.rs` (impl)
- `ddb-core/src/parser/tests.rs` (test) - CHANGED by the task

Ancillary files: `ddb-core/src/indexer/tests/mod.rs` (changed by the same commit
run, kept at `<base-sha>`; see "Scope narrowing"), `CHANGELOG.md`

`multi_file`: 2 Required files, 1 `impl` + 1 `test` the task changed.

## History per Required file

    git -C <src> log --oneline --no-patch b1bc2ed..HEAD -- <each Required path>

Both printed nothing. Control: the whole history of the pair,
`git -C <src> log --oneline --no-patch -4 -- ddb-core/src/parser/mod.rs
ddb-core/src/parser/tests.rs`, prints `b1bc2ed`, `7d28653`, `38577e7`,
`6635e30` - the three newest are the task's own commits, so nothing has touched
either since. (The same range is non-empty in general: the unfiltered
`71e718d..HEAD` control in task 5's note lists four commits, and `b1bc2ed`
precedes `71e718d`.)

Verdicts:

- `ddb-core/src/parser/mod.rs`: `empty` -> `whole-file`
- `ddb-core/src/parser/tests.rs`: `empty` -> `whole-file`

`clean_history`: both clean. `<base-sha>` equals the end of the commit run for
`parser/tests.rs`, so the canonical copy cannot bind behaviour a later commit
introduced.

The third file the commit run touched, `ddb-core/src/indexer/tests/mod.rs`, has
four later commits (`0a9a9f5`, `a946357`, `6202bcb`, `f555cb5`), all adding
eviction tests clear of the frontmatter-cap cases, so a `surgical` revert was
available. It is not used - see below.

## Scope narrowing

Stage A listed three Required files. `ddb-core/src/indexer/tests/mod.rs` is
demoted to Ancillary and kept at `<base-sha>`, for one reason: **the gate never
runs it, so it cannot be load-bearing.**

`cargo test -p ddb-core --lib parser` passes `parser` to libtest as a name
filter, which matches the full test path. The two cases this task appended to
the indexer suite are `indexer::tests::rebuild_lenient_skips_the_over_cap_
frontmatter_path_and_warns` and
`indexer::tests::rebuild_strict_reports_err_naming_the_over_cap_frontmatter_path`;
neither the names nor the module path contain `parser`. The arithmetic
confirms it: `rg -c "#\[test\]"` counts exactly **97** in
`ddb-core/src/parser/tests.rs` and 164 in `ddb-core/src/indexer/tests/mod.rs`,
and the gate run reports exactly `97 passed`. The filter therefore selects the
parser module and nothing else.

Had the file stayed Required, the per-file `necessity` check would disqualify
it: reverting it alone leaves the gate green, because the gate does not execute
it. Demoting it is the honest call.

Consequence to record: the reverted tree carries two indexer tests that assert
cap behaviour the tree does not yet implement. They still **compile** - the task
appended them at end-of-file and they reference only pre-existing names
(`GitRepo`, `Index::rebuild`, `Index::rebuild_strict`,
`crate::types::ConsistencyWarning` and its four variants); the string
`MAX_FRONTMATTER_BYTES` appears there only inside a comment, never as an
identifier, so removing the constant does not break the build. They would fail
if run, and the gate never runs them. An engine that runs the full crate suite
on its own will see them; that reveals the intended behaviour, which the pins
block states anyway.

## Reverse patch

    git -C <src> diff b1bc2ed e5ec64a --output=<abs>/tasks/6-cap-frontmatter-size.reverse.patch -- ddb-core/src/parser/mod.rs ddb-core/src/parser/tests.rs

No hand-written hunk is needed: both files are `whole-file`.

`git -C /Users/bob/git/src/github.com/doogat/ddb apply --check -v <patch>`:
clean, both files.

What the revert removes, read off `git -C <src> diff e5ec64a b1bc2ed --
ddb-core/src/parser/mod.rs`: the `const MAX_FRONTMATTER_BYTES: usize = 256 *
1024;` declaration and its doc comment, plus the five-line guard at the head of
`parse_frontmatter`:

    if yaml.len() > MAX_FRONTMATTER_BYTES {
        return Err(DoogatError::Parse(format!(
            "frontmatter exceeds {MAX_FRONTMATTER_BYTES} byte cap ({} bytes)",
            yaml.len()
        )));
    }

and, from `parser/tests.rs`, the three cases named below.

Pretask: dea40bd2749e1edbb5f22e16a13ce53eecdc7a39

Necessity:
- `ddb-core/src/parser/mod.rs`: exit 101, first failure: `error[E0425]: cannot find value \`MAX_FRONTMATTER_BYTES\` in this scope` (compile error) - necessity holds.
- `ddb-core/src/parser/tests.rs`: n/a (test file - necessity is enforced at scoring by dropped/own/ablate)

## Pinned interface

The prompt's `Names the acceptance gate binds to` block reads, verbatim:

- Constant name `MAX_FRONTMATTER_BYTES`, value `256 * 1024` (262144), declared
  at module scope in `ddb-core/src/parser/mod.rs` so that
  `ddb-core/src/parser/tests.rs` reaches it through `use super::*`.
- The cap is enforced inside
  `pub fn parse_frontmatter(yaml: &str, path: &str) -> Result<DoogatMeta>`,
  against `yaml.len()`.
- Boundary: a frontmatter string of exactly `MAX_FRONTMATTER_BYTES` bytes still
  parses; one byte over returns `Err`.
- Error-message contract: the returned error's `to_string()` contains BOTH the
  cap as a decimal number AND the actual frontmatter byte length as a decimal
  number.
- The rejection stays an ordinary parse error, so the existing parse-error to
  `ConsistencyWarning::MalformedYaml` classification carries it into the lenient
  skip path; no new warning variant.

### Why this needed pinning

The canonical `parser/tests.rs` binds `MAX_FRONTMATTER_BYTES` by name eight
times across three cases -
`frontmatter_at_exactly_the_byte_cap_still_parses`,
`frontmatter_one_byte_over_the_cap_fails`,
`frontmatter_over_cap_error_states_cap_and_actual_size` - e.g.

    let pad_len = MAX_FRONTMATTER_BYTES - prefix.len();
    ...
    msg.contains(&MAX_FRONTMATTER_BYTES.to_string()),

`rg MAX_FRONTMATTER_BYTES` over the repo finds it defined once
(`ddb-core/src/parser/mod.rs`) and used only in `parser/mod.rs` and
`parser/tests.rs`, plus one comment in `indexer/tests/mod.rs`. Definer and user
are both Required, so the revert removes the name from the tree completely,
and the ledger line names neither the constant, nor its value, nor the error
wording. Without the pins block the engine would have to guess the identifier
exactly or the crate would not compile at gate time. Re-scoping cannot rescue
that (reverting `parser/mod.rs` while leaving `parser/tests.rs` alone will not
build; leaving `parser/tests.rs` unreverted hands over the answer key), which is
why the pins block is the only route - and it is now available.

Everything else the three canonical cases reach is already in the reverted tree:
`parse_frontmatter`, `DoogatMeta` and its `title` field, and the crate's
`Result`/error `to_string()`.

Canonical test files copied:

- `ddb-core/src/parser/tests.rs` ->
  `6-cap-frontmatter-size.canonical/ddb-core/src/parser/tests.rs`

## Notes

- Smallest ddb unit in the set: the impl side is one constant plus a five-line
  guard. It is in the manifest as the second Rust task, so tasks 5 and 6 keep
  the sample at two repos and two languages without paying `alt1`'s twelve-file,
  ten-minute gate.
- The gate is filtered (`--lib parser`), so it is fast, but it does NOT catch
  collateral damage elsewhere in the crate. `alt1` is the unit that does.
