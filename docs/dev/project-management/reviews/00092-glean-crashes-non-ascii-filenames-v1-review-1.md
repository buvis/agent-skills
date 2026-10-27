---
head_sha: 03712e4cc5c4307c8085490be68ab93b7d4c7560
reviewers: alice, blake, eve, bob
---

## Alice

**00092-glean-crashes-non-ascii-filenames-v1-c1**
- 🟡 The rename regression never checks which filename gets reported, even though its name promises it ("reports renamed non-ASCII path, not the original") and the task says "Assert exact reported filenames". It only asserts `ok` and `staged == 1`, then ends on a comment with no assertion under it. Fix: give the renamed file a credential, or a `never` ledger entry on the new name `.thé`, then assert `[h["path"] for h in body["hard"]] == [".thé"]`. | skills/glean/scripts/test_glean.py:380
- 🟡 The rename branch of the parser moves the index twice in a row (`i += 1; rows.append((added, fields[i + 1])); i += 2`). Reads more clearly as `rows.append((added, fields[i + 2])); i += 3`. Behavior is unchanged. | skills/glean/scripts/glean.py:236

## Blake

**00092-glean-crashes-non-ascii-filenames-v1-c1**
- 🟡 A carriage return in a staged filename still crashes check-staged with a traceback — the `git()` helper runs with `text=True`, translating `\r` to `\n`, so the path passed to `git show :<path>` names a file that does not exist. | skills/glean/scripts/glean.py:90
- 🟡 Same rename-test assertion gap Alice raised: the test proves only "no crash", never which path was reported. | skills/glean/scripts/test_glean.py:380
- ⚪ `git()` decodes git output with the locale text encoding; a non-UTF-8 filename (Linux) could raise UnicodeDecodeError. Inferred, not reproduced (macOS APFS rejects such names). | skills/glean/scripts/glean.py:90
- ⚪ The unmerged branch `agoge/authored-tests-2026-10-26` still holds its own strict-xfail test under the same function name; a later merge of that branch would XPASS(strict) or conflict. | skills/glean/scripts/test_glean.py:296
- ⚪ The staged-blob `git show` call runs with unguarded `check=True`; any failure surfaces as a raw traceback rather than a `glean:` error — the root cause behind the carriage-return crash above. | skills/glean/scripts/glean.py:252

## Eve

**00092-glean-crashes-non-ascii-filenames-v1-c1**

FIX:
- Same rename-test assertion gap as Alice/Blake above (verified — see Doubt lens below).
- PRD must-have "tabs, newlines, quotes in filenames" has no dedicated test; the only "unusual" case is a space plus a combining accent, which macOS precomposes away. | skills/glean/scripts/test_glean.py:357
- Several new tests (lines 320, 333, 345, 357, 370) omit `returncode`/`staged` assertions the task explicitly asked for.
- `git show :2:notes`-shaped filenames (`[0-3]:...`) still crash — git reads the leading digit as a stage number. Fix: `f":0:{path}"`. | skills/glean/scripts/glean.py:253
- Fix commit 03712e4 has no CHANGELOG entry despite `rules/changelog.md` treating one as blocking for a `fix` commit (card set `changelog: none`). | CHANGELOG.md:8
- Same rename-branch arithmetic simplification as Alice. | skills/glean/scripts/glean.py:236-238

VERIFY:
- Windows CI has not run these 7 new tests yet (master is 16 commits ahead of unpushed origin). Check: after push, `gh run list --workflow ci.yml --branch master --limit 1` then `gh run view <run-id> --log-failed`.

KNOWN:
- `glean.py scan` has the same quoted-path defect for untracked non-ASCII files (`ls-files -o` without `-z`) — out of this PRD's scope (check-staged only); needs a follow-up PRD.
- `--diff-filter=ACMR` lets a staged type-change (e.g. symlink replaced by a regular file) bypass the safety gate — predates this change, and the PRD's Solution section prescribed `ACMR` verbatim.
- `git()`'s locale-encoding decode could mangle non-UTF-8 filename bytes on Linux — predates this change; target platform (macOS/UTF-8) unaffected.
- The unmerged agoge branch still holds its own xfail test under the same name — reconciling it belongs to whoever retires that branch.

D1: pass
D2: pass
D3: pass
D4: pass
D5: pass

## Bob

**00092-glean-crashes-non-ascii-filenames-v1-c1**
- (First two codex CLI dispatches failed outright: codex's read-only sandbox blocked even reading the supplied context/diff files — `sandbox_apply: Operation not permitted`. One retry burned; substituted a `general-purpose` subagent running the same persona prompt per the lane's documented fallback.)
- 🔴→refuted: Last added test is truncated — no assertion on which path a rename reports. Victor traced the real `git diff --cached --numstat -z --diff-filter=ACMR` byte layout for a rename against the parser's index arithmetic and confirmed it reports the new path, not the old one; the claimed wrong-path failure mode does not exist in the code. Downgraded to a test-rigor gap (already captured above), not a live defect. | skills/glean/scripts/test_glean.py
- ⚪ Cannot statically verify: pytest run passes | N/A
- ⚪ Cannot statically verify: non-ASCII regression fails against prior code | N/A

(Carl/gemini lane: both the background dispatch and a foreground retry failed — the `copilot` backend (`gemini-3.8-flash`) reported "exceeded your monthly quota". Counted as failed after the one retry; no findings to report.)

Verdict: converged
Tests: 3975 passed, 9 skipped (fast-track batch suite)
codex_rung_guard: not fired
