# Commands and releases

## Common public interface

| Task and shim | Meaning |
|---|---|
| onboard | Explicit setup/repair; --sync only refreshes local integrations with installed tooling. |
| check | Applicable formatting checks, lint, types, security, tests/build verification without source rewrites. |
| format | Apply formatting. |
| run-tests | Execute tests, with documented selectors where supported. |
| build | Produce build/distribution artifacts. |
| develop | Run local development or watch mode. |
| release | Prepare and publish a selected version; preview with --dry-run where supported. |

Only create meaningful tasks. Keep specialized verb-first commands where useful.
Implement with the repository's native tools; CI calls these tasks or their same
constituent implementations. Do not duplicate validation logic or skip old release
checks when renaming callers. A missing backend must be a reported gap, not a
successful no-op task. Do not use bare test: the shell builtin wins over a PATH shim.

Add tools/ to project PATH using mise's [env] _.path = ["tools"]. Add _.file = ".env"
only when used. Integrate with existing mise files/includes rather than creating
competing authorities. Preserve pins, env and unrelated tasks. Verify the installed
mise syntax/capabilities before using optional features.

Each executable tools/<verb> shim anchors to its own checkout, forwards arguments
and preserves status, and invokes the same-named mise task. Example POSIX release shim:

```sh
#!/bin/sh
set -eu
repo_root=$(CDPATH= cd -- "$(dirname -- "$0")/.." && pwd)
cd "$repo_root"
exec mise run release -- "$@"
```

Use equivalent launchers on other supported platforms. Behavior belongs in mise
tasks or optional tools/lib/ helpers, which are not added to PATH. Tasks invoke native
tools or explicit helper paths, never their own public shim. For example a file-backed
release task points to tools/lib/release, not tools/release. Mark public shims executable.

Document mise activation for bare interactive commands. Hooks/CI use explicit shim
paths or mise run without interactive activation. Initial setup can use
`mise install && ./tools/onboard` once the repository's configuration is trusted;
follow the installed mise trust policy, never silently disable it.

## Release implementation contract

Keep one public task. Accept patch, minor, major or EXACT_VERSION; no arguments
print usage without publishing. Default to SemVer for released software, document
pre-1.0/public-contract rules, and use exact versions for justified alternatives.
Translate prerelease syntax to ecosystem requirements when needed.

Use one native version authority per released unit: manifest or tags. Compute the
version once; synchronize necessary metadata, locks, changelog and artifacts. Avoid
inventing a universal VERSION file. Independently released monorepo units accept
--component; require a selection when ambiguous. A single-version repo needs none.
Default single-unit tags to v<version> unless the repository has another convention.
Release only the selected component and explicitly documented dependent changes.

--dry-run must report version/files/checks/tag/destinations without repository or
remote mutation. State unsimulated stages. If unsupported, exit before any mutation;
never turn preview into a real release. Normal release prepares metadata, runs checks
and builds for that candidate, commits applicable release changes, tags that exact
commit and publishes directly or through CI. Existing branch/review/protection policy
still applies. A triggered CI run is pending until required destinations succeed.

Keep change entries under [Unreleased]; preparation creates the dated version section
and retains [Unreleased]. Derive published notes from it. Published versions/tags are
immutable. For partial failure, identify completed destinations and resume the exact
version/commit/artifacts rather than calculating another bump; verify matching outputs.

Document authority, version policy, tag/component rules, prerequisites, required checks,
destinations, preview limits and retry in docs/dev/procedures/release.md. Do not add
release tasks or CHANGELOG to a nonreleased repository such as personal dotfiles.
Creating a release adapter does not authorize invoking a real publication.
