# WIP 00015 backlog-review handoff

PRD 00015 is still in wip. Its Success Criteria requires:
> `uv run pytest skills/distil-memory/scripts -q` reports no failures and no xfailed tests.

That includes the strict expected failure
test_an_index_that_cannot_be_read_leaves_no_memory_file_behind in test_write.py,
owned by backlog00017. The active queue-corruption PRD cannot remove it within
its own scope. This is B16 in the backlog report: rework thrash/order break.

## Proposed replacement for the active owner

> `uv run pytest skills/distil-memory/scripts -q` exits 0 with no failures.
> The unreadable-queue and drained-queue regressions owned by this PRD pass
> without xfail markers. Unrelated strict expected failures remain outside
> this PRD's scope, including the index-publication regression owned by 00017.

Use the current test names and locations. During review the active session
split exit-code tests into test_docket_exit_codes.py; its unreadable next,
cursor, start, save and decide tests and drained-next control are present.
The suite-wide “no xfailed tests” predicate remains in the WIP document.

The review did not apply this replacement because the invoked
[review skill](../../../skills/review-prd-backlog/SKILL.md) says:
“Never touch wip/ or done/ contents.”

Apply it in the active PRD owner's session, then let that session complete its
normal review handoff. No queue code or WIP execution state is changed here.
