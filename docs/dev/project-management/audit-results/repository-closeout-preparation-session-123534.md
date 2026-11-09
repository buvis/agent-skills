# Preparation custody addendum — session 20261030-123534

**Preparation PASS; Stage 1 remains BLOCKED.** Read this addendum with
[`repository-closeout-preparation.md`](repository-closeout-preparation.md).
It supplies this session's firsthand custody and verification evidence where
the concurrent completion account describes the same actions as external or
unattributed. It does not overwrite that account or claim ownership of its work.

## Concurrent documentation writes

This session began with `master` at
`0035e628f013bbe6147da9d78ac1a19d98c754b9`, one worktree, no stashes, a clean
index, and only the preparation plan untracked. It created ignored evidence
under `docs/dev/tmp/closeout-preparation-20261030-123534/`, inspected the plan's
inputs and wrote the initial preparation report with the 126-row appendix.

While this session remained active, another session replaced that report and
appended a preparation-completion entry to the execution record. The replacement
refers to a separate `closeout-preparation-completion-20261030` evidence directory.
This session did not create that directory or author that completion entry.
Two failed context-matching edits revealed the replacement; no forced overwrite
followed. Only this addendum and narrow cross-references are added afterward.

No concurrent production edit was observed. This session did not delegate work,
start another agent, invoke autopilot, or restart Claude. Its own supported
ownership check was `lsof -nP` against the four lock files, with no visible
holders. It did not repeat the earlier denied `ps` operation. Other account
statements about another process check describe that account's actions.
Runtime ownership remains partly unobservable; all locks remain unchanged.

## Worktree and branch custody resolved for this session

This session created `prep/closeout-20261030-inspect` and worktree
`docs/dev/tmp/closeout-preparation-20261030-123534/migration-inspection` at
`9249695b334f2a894bda8e016d974480cece918e` using `git worktree add -b`.
It used that checkout only for inspection and local tests; the tracked tree
stayed clean. It created no commits in that branch.

After saving evidence, this session removed its own worktree with
`git worktree remove`. Ordinary `git branch -d` declined because master does
not contain the migration. Before deleting the disposable alias, this session
verified both branch tips were identical and
`git rev-list --count feat/skill-migration-bundle..prep/closeout-20261030-inspect`
returned **0**. It then removed only its alias with `git branch -D`.
The original local and remote migration refs retain the full tip and history.
The inspection branch is therefore **absent**, not retained for recovery.
Recreate any future inspection from the original migration ref in a new owned
worktree after checking current ownership. Do not try to resume the removed alias.

Boundary evidence in this session's ignored directory:
`refs-before.txt` and `refs-after.txt` are byte-identical;
`worktrees-after.txt` lists only the original checkout;
`stashes-after.txt` is empty; `remote-heads-after.txt` matches all four entry heads.
All **62** hashes in the original preservation manifest match in
`preservation-check.json` and `preservation-after.json`.
PRD 00133 remains batch `202610271200`, build/build, 0/1 tasks; its state and
PRD hashes are unchanged. Original branches, private recovery files, active
migration references and all PRD lifecycle locations remain untouched.

## Firsthand measurements and provenance

All paths in this table are under this session's ignored evidence directory.
The capture helper records commands, exits, times, sizes and stdout hashes.
Its initial schema does not include cwd/SHA. The cwd/SHA bindings below come
from this session's actual invocations, ref capture, clean-tree checks and
absence of source/test/config edits, rather than inference from the filenames.

| Measurement | Cwd / tested input | Actual result |
|---|---|---|
| `uv run pytest`, `preparation-full-suite.log` | Original repository checkout; source tip `0035e628f013bbe6147da9d78ac1a19d98c754b9` | **4258 passed, 9 skipped, 2 warnings**, 419.28 s; invoked by this session at 12:40:54 UTC, completed 12:47:53 UTC |
| `uv run ruff check`, `uv run ruff format --check`, `uv run braid --check` | Same checkout and unchanged source tip | All exit 0; 15 formatted files; braid 131 current, 20 ignored, zero drift and zero mutations |
| Seven skill validators and changelog checker | Owned migration checkout at exact `9249695` head | All exit 0; `validate-*.log`, `migration-changelog.log` |
| Dependency-enabled seven-skill pytest command | Owned migration checkout at exact `9249695` head, explicit subprocess cwd | **29 passed, 7 subtests passed, zero skipped**, 5 SWIG warnings; 3.72 s pytest time; 12:39:05–12:39:19 UTC including environment setup; `migration-focused.log` |
| Four ABAP helper `--selftest` commands | Same migration checkout/head | Four exit 0; `selftest-*.log` |
| Disposable source/path/newline/publisher probes | Original checkout plus imported migration helper files, all external calls mocked | `diagnostic-probes.json`; local/platform-simulated evidence, no Windows pass or live publishing claim |

Runtime: macOS 27.0.1 arm64, Python 3.12.16, uv 0.13.6, Git 2.56.0,
Node 26.13.0. The nine full-suite skips retain the previously verified
classification: eight survey cases require optional tree-sitter support and
one case requires native Windows job objects. The two archive warnings remain
00157 defects. Migration stderr also records a SWIG shutdown warning.

The full-suite output SHA-256 is
`6e1c99fb1cbe38171b15b4ad345f0e5c97e009bf6c7433d31615f1f4760a46e7`.
This is a fresh local **baseline** run, not a corrected-candidate test.
The earlier Node build/freshness/60-test result and archive sentinel/warnings
probes were reused with unchanged inputs, not rerun. The exact meeting app
and template inputs also match the old Node PR; only other skill documentation
differs at that older base.

Complete native Windows baseline logs were retrieved by this session through
supported `gh run view RUN --job JOB --log` calls, with no shell redirection:

| Run / exact SHA | Job / captured UTC | Bytes / SHA-256 |
|---|---|---|
| 41032617118 / `6b52b2ab74388753dce2c89a76f2915e2cdae124` | 123985731931 / 12:35:55 | 432028 / `4c4ccca984db5335f71cc34ce51d923ee180fe18f84415465369aed6d0a1feeb` |
| 41030058506 / `9249695b334f2a894bda8e016d974480cece918e` | 123977391583 / 12:35:59 | 446035 / `61812d564099fb7567b41083e2e20cf08c6c84378abe03982d6716e94a853450` |

Every one of the 61 + 65 FAILED nodes matches an appendix row with a nonempty
assertion and traceback. The 19 group counts sum correctly in both runs.
There are 60 shared node IDs, one master-only and five migration-only nodes.
The recorded native times, totals, skips and Python 3.13.16 remain historical
hosted observations. No new Windows run was launched.

## Additional implementation requirements retained from inspection

The concurrent report preserves most of the initial packet. Carry these
additional findings and clarifications with it; none is implemented here.

| Item / owner | Evidence and proposed repair | Verification |
|---|---|---|
| C6, MEDIUM / compatibility owner | `explore-abap-solution/SKILL.md:19` says a manual check cannot replace the automated gate, but `:208` instructs manual PASS-shaped reconstruction if the helper is missing. Make absence explicitly INCOMPLETE/unverified with recovery guidance. | Read both sections together; validate the skill and run the research selftest. Missing helper must never become a claimed automated PASS. |
| C7, LOW / compatibility owner | `document-abap-solution/SKILL.md:91` forbids a separate solution.json, while `:111` still names it as a consistency input. Refer consistently to embedded solution data. | Inspect blueprint/entrypoint references, run full/research selftests and skill validator. |
| Q4–Q5 hypothesis refinement / archive owner | All affected safe chains contain relative targets with `/`; the simple file-to-file chain passes. Relative reparse-target separator handling is another supported hypothesis besides directory typing. `_lay_links` writes raw target text; tarfile also passes raw link text to `os.symlink`. | Native probe must compare raw and native-separator spellings, link type, creation order and actual resolved landing. Keep safe file/directory/dangling links; do not reject all links or call a broken fixture containment evidence. |
| Q3 source refinement / Windows owner | `eval_harness_run_helpers.py:110–118` logs Bash pwd; `:307–314` filters with a native path prefix, explaining the four empty observed lists. `test_eval_gates.py:57` logs the same incompatible spelling. | Native cwd logging or explicit MSYS conversion must retain exact execution counts/order, timestamps, separate trees and paths containing spaces. |
| Windows finding mapping | Already-held **00044** owns complete Windows suite closure and explicitly allows additional collected-test repairs. All B/P/D/G/U/S/Q matrix groups map to it; Q4–Q6 also share archive findings. | Keep its status unchanged now; leave target selection and task/lane routing to the installed workflow. No new identifier is allocated. |
| Archive valid controls / A2,A8,A9 | Test binary and CRLF blobs, executable files, safe dangling links, deterministic sealing, existing destination/ancestor links and later extraction/seal failure. Missing filter cannot cause blanket refusal of ordinary supported archives. | Both filter branches preserve exact bytes and supported links; refusal leaves sentinel content/metadata unchanged and removes only owned staging. Include a faithful no-filter API seam that cannot accept newer extraction keywords. |
| Publisher C2 replacement boundary | XML escaping fixes ampersand/quote names; regex replacement can separately reinterpret backslashes. | Test literal replacement behavior as well as XML attribute roundtrip, with mocked page data. No live edit. |

Primary documentation supports the Q4 investigation:
[CPython tarfile link creation](https://raw.githubusercontent.com/python/cpython/v3.13.16/Lib/tarfile.py)
passes link targets to the OS, and the
[CPython Windows tar-link issue](https://bugs.python.org/issue13702) discusses
relative target normalization. These support a native probe, not a proven repair.
[Python 3.13 os.path](https://docs.python.org/3.13/library/os.path.html#os.path.isabs)
documents the changed single-leading-slash rule behind Q6. Windows path
classification must not rely solely on host `isabs` for archive-format paths.

Separate dependency recommendations remain conditional merges. The
[setup-uv 10.3.3 release](https://github.com/astral-sh/setup-uv/releases/tag/v10.3.3)
changes manifest sourcing with fallback while retaining checksum checks;
its observed setup success is useful but not a corrected-base suite pass.
[Node 26.13.0](https://nodejs.org/en/blog/release/v26.13.0) is LTS; keep the
hosted Linux libatomic prerequisite in mind when validating the actual image.
The existing two low-severity npm findings do not authorize unrelated upgrades.

All three ordered diagnostic trees in the report were produced by this session
before the other account independently reproduced them. No synthetic commit
or semantic resolution was used. Every fixes-first candidate tree remains
unmeasured. For the future Windows proposal, use the report's final chosen ref
**`ci/closeout-stage-1-20261030`**, not the unhyphenated draft spelling from this
session's earlier report. The candidate SHA remains unknown; no branch push,
workflow dispatch, PR action or remote cleanup is authorized by preparation.

## Boundary

The reports and unchanged preparation plan remain local documentation. This
session makes no commit over concurrent uncommitted work. Raw evidence stays
ignored. The cleanup of this session's inspection worktree/alias is complete;
no further cleanup of the other session's evidence is warranted.

Same-stage handoff:
`docs/dev/tmp/handoff-closeout-stage-1-prepared-20261030-1258.md`.
The handoff names this addendum so the next session can reconcile custody before
execution. It preserves the quota reset, original state, concrete approval
boundary and mandatory fresh-session review gate. No implementation or Stage 2
work follows in this session.
