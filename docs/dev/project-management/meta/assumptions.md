## Task 1: Hoist the duplicate git rev-parse into collect_repo for collect_branches and collect_local

- Used the synthetic path "/repos/acme/widget" (not tmp_path) for both new tests, matching most of this file's existing collect_repo tests - local hygiene collectors already tolerate a nonexistent path by returning defaults rather than raising (demonstrated by other tests using the same path). (Tess)
- For the failure-path test, checked "prds" in result rather than pinning its exact value, since the task only asked to prove "at least one field ... is still present," not its shape. (Tess)
- Used RuntimeError("git: fatal error") for the injected rev-parse failure, per the task's suggestion ("any exception collect_repo's other except clauses already catch, e.g. RuntimeError"). (Tess)
- Making `current` a required positional parameter (not defaulted) on `collect_branches`/`collect_local` is safe because no caller outside collect.py invokes them directly (verified via `rg -n`); the task's tests only exercise these through `collect_repo`. (Ivan)
- The "57 lines / style-limit violation" referred to the Functions under 50 lines rule (coding-style.md), not a literal failing pytest test - no test needed changes, none exist for line-count. (Ivan, style-fix dispatch)
- Extracting to private module-level functions (rather than nested closures) was the right shape since `_current_branch_resolver` already needed to return a closure regardless. (Ivan, style-fix dispatch)
