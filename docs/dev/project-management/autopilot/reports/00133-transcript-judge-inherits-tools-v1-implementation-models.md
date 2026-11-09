# Implementation model audit

PRD 00133, cycle 1, task 1 retains work baseline
`6b52b2ab74388753dce2c89a76f2915e2cdae124`.

Both contributing workers used observed `gpt-6.1-sol` / OpenAI at medium
effort, mapped from logical sonnet. Launcher: native Codex subagent.

| Role | Dispatch | Session | Contribution |
|---|---|---|---|
| Tess retry | `0a7461b9` | `01a1c2ad-42f0-7362-b4f4-aae159efdf17` | Tests, commit `c49d87c` |
| Ivan | `8ac49953` | `01a1c2af-58f0-75a1-8878-058d53313192` | Implementation, commit `ac18d34` |

`*-worker-metadata.jsonl` projects model, effort, turn and session identity
directly from each worker's raw session metadata and `turn_context`, retaining
the source filename, source line number and original line SHA-256. Private
working-directory and instruction fields are omitted from this public artifact.
These are extracted log fields, not worker self-reports or coordinator model
claims. `*-worker-results.jsonl` retains the contributing workers' final raw
response records. The JSON audit cites and hashes the metadata projection lines.

The first Tess dispatch `88c1fb32`, session
`01a1c2ac-acb5-7643-9c45-83bc56f6eb90`, exceeded its input budget before edits.
It contributed nothing and is excluded from implementation evidence. Its model
metadata and failed dispatch remain recorded. The older `054609d2` Tess dispatch
was already recorded lost during prior recovery; no PRD implementation from it
exists. Planning, coordinator and unrelated migration/closeout changes are not
PRD implementors. No repair or additional contributing model ran.

A late coordinator `build/resume` telemetry row automatically marked the live
Tess retry lost. Its later `ok` close, raw final result, test diff and commit
prove completion; both ledger events remain intact. This bookkeeping event was
not an implementation failure or a second worker attempt.

The source route was native sonnet; no unsupported-provider fallback was needed.
The host supports independent Anthropic review. No reviewer was dispatched:
the repository suite failed, so the fast-track red-gate rule parks the PRD.
The audit binds the failed attempt before the canonical stall reset; regenerate
it from retained evidence and new attempts before any future review.
