#!/usr/bin/env bash
# Test harness for list-dep-prs.sh (macOS bash 3.2 compatible). Stubs `gh` on
# PATH with canned repos and PRs, pushes them through the real `--jq` filter the
# script hands to gh, and asserts on the script's stdout only.
set -u

LIST_SH="$(cd "$(dirname "$0")" && pwd)/list-dep-prs.sh"
[ -n "${1:-}" ] && LIST_SH="$1"

command -v jq >/dev/null 2>&1 || { echo "jq is required to run this suite"; exit 1; }

PASS_COUNT=0
FAIL_COUNT=0
PASS() { echo "PASS: $1"; PASS_COUNT=$((PASS_COUNT + 1)); }
FAIL() { echo "FAIL: $1 -- $2"; FAIL_COUNT=$((FAIL_COUNT + 1)); }

STUBDIR=$(mktemp -d)
trap 'rm -rf "$STUBDIR"' EXIT

# `repo list` sees only the account's own repo. `api user/repos` also sees the
# organization repo, which is where one of the dependency PRs lives.
cat > "$STUBDIR/gh" <<'STUB'
#!/bin/bash
JQ="."
REPO=""
PREV=""
for arg in "$@"; do
    [ "$PREV" = "--jq" ] && JQ="$arg"
    [ "$PREV" = "--repo" ] && REPO="$arg"
    PREV="$arg"
done
case "${2%%\?*}" in
    user/repos) API_REPOS=1 ;;
    *) API_REPOS=0 ;;
esac
if [ -n "${STUB_CALL_LOG:-}" ] && [ "$1" = "api" ] && [ "$API_REPOS" = "1" ]; then
    printf '%s\n' "$*" >> "$STUB_CALL_LOG"
fi
case "$1" in
    repo)
        [ "$2" = "list" ] && DATA='[{"nameWithOwner":"me/personal"}]' || { echo "stub gh: unexpected call: $*" >&2; exit 64; } ;;
    api)
        if [ "$API_REPOS" != "1" ]; then echo "stub gh: unexpected call: $*" >&2; exit 64; fi
        [ -n "${STUB_FAIL_API:-}" ] && { echo "gh: Bad credentials (HTTP 401)" >&2; exit 1; }
        if [ -n "${STUB_FAIL_REPO:-}" ]; then
            # A third repo, queried after the one that fails, proves the loop
            # keeps going instead of stopping at the first failure.
            DATA='[{"full_name":"me/personal"},{"full_name":"acme/org-repo"},{"full_name":"acme/third-repo"}]'
        else
            DATA='[{"full_name":"me/personal"},{"full_name":"acme/org-repo"}]'
        fi ;;
    pr)
        if [ -n "${STUB_FAIL_ALL_PRS:-}" ]; then
            echo "gh: rate limited (HTTP 403) for $REPO" >&2
            exit 1
        fi
        if [ -n "${STUB_FAIL_REPO:-}" ] && [ "$REPO" = "$STUB_FAIL_REPO" ]; then
            echo "gh: rate limited (HTTP 403) for $REPO" >&2
            exit 1
        fi
        case "$REPO" in
            me/personal)
                DATA='[{"number":1,"title":"Pin dependencies","author":{"login":"app/renovate","is_bot":true},"labels":[],"createdAt":"2026-10-01T00:00:00Z","url":"https://example.invalid/1"},
                       {"number":3,"title":"feat: add thing","author":{"login":"someone","is_bot":false},"labels":[],"createdAt":"2026-10-03T00:00:00Z","url":"https://example.invalid/3"}]' ;;
            acme/org-repo)
                DATA='[{"number":2,"title":"Bump jq from 1.6 to 1.7","author":{"login":"dependabot[bot]","is_bot":true},"labels":[],"createdAt":"2026-10-02T00:00:00Z","url":"https://example.invalid/2"},
                       {"number":4,"title":"Pin jq to 1.7","author":{"login":"dependabot[bot]","is_bot":true},"labels":[],"createdAt":"2026-10-04T00:00:00Z","url":"https://example.invalid/4"}]' ;;
            acme/third-repo)
                DATA='[{"number":5,"title":"Bump lodash from 4.1 to 4.2","author":{"login":"dependabot[bot]","is_bot":true},"labels":[],"createdAt":"2026-10-05T00:00:00Z","url":"https://example.invalid/5"}]' ;;
            *)
                DATA='[]' ;;
        esac ;;
    *)
        echo "stub gh: unexpected call: $*" >&2
        exit 64 ;;
esac
printf '%s' "$DATA" | jq -rc "$JQ"  # gh prints strings raw and objects compact
STUB
chmod +x "$STUBDIR/gh"

OUT="$STUBDIR/out.txt"
ERR="$STUBDIR/err.txt"
PATH="$STUBDIR:$PATH" bash "$LIST_SH" > "$OUT" 2> "$ERR"
EXIT=$?

# 1. Organization repos are enumerated: `gh repo list` alone never sees them.
if grep -qF -- "--- acme/org-repo ---" "$OUT"; then
    PASS "lists dependency PRs from an organization repo"
else
    FAIL "lists dependency PRs from an organization repo" "stdout: $(tr '\n' '|' < "$OUT")"
fi

# 2. gh reports bot authors as app/<name>; a renovate PR whose title matches no
#    pattern is still found by its author.
if grep -qF '"Pin dependencies"' "$OUT"; then
    PASS "detects a renovate PR by the app/renovate author login"
else
    FAIL "detects a renovate PR by the app/renovate author login" "stdout: $(tr '\n' '|' < "$OUT")"
fi

# 3. The older <name>[bot] login form keeps working: this title matches no
#    pattern, so only the author branch can select it.
if grep -qF '"Pin jq to 1.7"' "$OUT"; then
    PASS "detects a dependabot PR by the dependabot[bot] author login"
else
    FAIL "detects a dependabot PR by the dependabot[bot] author login" "stdout: $(tr '\n' '|' < "$OUT")"
fi

# 4. A human PR with a non-dependency title stays out.
if grep -qF '"feat: add thing"' "$OUT"; then
    FAIL "skips a non-dependency PR" "stdout: $(tr '\n' '|' < "$OUT")"
else
    PASS "skips a non-dependency PR"
fi

# 5. Clean exit.
if [ "$EXIT" -eq 0 ]; then
    PASS "exits 0 when repos are found"
else
    FAIL "exits 0 when repos are found" "exit: $EXIT -- stderr: $(tr '\n' '|' < "$ERR")"
fi

# 6. A failed repo enumeration (bad token, rate limit) stops with a message
#    on stderr instead of dying silently under `set -e`.
FAIL_ERR="$STUBDIR/fail_err.txt"
PATH="$STUBDIR:$PATH" STUB_FAIL_API=1 bash "$LIST_SH" > /dev/null 2> "$FAIL_ERR"
FAIL_EXIT=$?
if [ "$FAIL_EXIT" -ne 0 ] && grep -qF "gh api user/repos failed" "$FAIL_ERR"; then
    PASS "a failed gh api call exits non-zero with a message on stderr"
else
    FAIL "a failed gh api call exits non-zero with a message on stderr" "exit: $FAIL_EXIT -- stderr: $(tr '\n' '|' < "$FAIL_ERR")"
fi

# 7. One repo's PR lookup fails (rate limit, bad permissions) among three.
#    The failure must not be swallowed: exit code signals incomplete results,
#    the failed repo's name reaches a diagnostic, and repos queried both
#    before and after the failure keep their successful results.
PARTIAL_OUT="$STUBDIR/partial_out.txt"
PARTIAL_ERR="$STUBDIR/partial_err.txt"
PATH="$STUBDIR:$PATH" STUB_FAIL_REPO="acme/org-repo" bash "$LIST_SH" > "$PARTIAL_OUT" 2> "$PARTIAL_ERR"
PARTIAL_EXIT=$?

if [ "$PARTIAL_EXIT" -eq 2 ]; then
    PASS "exits 2 when one repository's PR lookup fails"
else
    FAIL "exits 2 when one repository's PR lookup fails" "exit: $PARTIAL_EXIT -- stderr: $(tr '\n' '|' < "$PARTIAL_ERR")"
fi

if grep -qF "acme/org-repo" "$PARTIAL_ERR"; then
    PASS "names the failed repository on stderr in the partial-failure case"
else
    FAIL "names the failed repository on stderr in the partial-failure case" "stderr: $(tr '\n' '|' < "$PARTIAL_ERR")"
fi

if grep -qF '"Pin dependencies"' "$PARTIAL_OUT"; then
    PASS "retains the earlier successful repository's results in the partial-failure case"
else
    FAIL "retains the earlier successful repository's results in the partial-failure case" "stdout: $(tr '\n' '|' < "$PARTIAL_OUT")"
fi

# acme/third-repo is queried only after acme/org-repo fails (api order is
# me/personal, acme/org-repo, acme/third-repo), and its name shares the
# "acme/" prefix with the failed repo, so a substring match on the failed
# name alone could not account for this result appearing too.
if grep -qF -- "--- acme/third-repo ---" "$PARTIAL_OUT" && grep -qF '"Bump lodash from 4.1 to 4.2"' "$PARTIAL_OUT"; then
    PASS "keeps querying and keeps results for repositories after the failed one"
else
    FAIL "keeps querying and keeps results for repositories after the failed one" "stdout: $(tr '\n' '|' < "$PARTIAL_OUT")"
fi

if grep -qF -- "--- acme/org-repo ---" "$PARTIAL_OUT"; then
    FAIL "omits the failed repository's own heading from the partial-failure output" "stdout: $(tr '\n' '|' < "$PARTIAL_OUT")"
else
    PASS "omits the failed repository's own heading from the partial-failure output"
fi

# 8. Every repository's PR lookup fails. An empty "Dependency Update PRs"
#    section must not read as "no updates" -- it must fail loudly, exit 2,
#    and name every failed repository.
ALLFAIL_OUT="$STUBDIR/allfail_out.txt"
ALLFAIL_ERR="$STUBDIR/allfail_err.txt"
PATH="$STUBDIR:$PATH" STUB_FAIL_ALL_PRS=1 bash "$LIST_SH" > "$ALLFAIL_OUT" 2> "$ALLFAIL_ERR"
ALLFAIL_EXIT=$?

if [ "$ALLFAIL_EXIT" -eq 2 ]; then
    PASS "exits 2 when every repository's PR lookup fails"
else
    FAIL "exits 2 when every repository's PR lookup fails" "exit: $ALLFAIL_EXIT -- stderr: $(tr '\n' '|' < "$ALLFAIL_ERR")"
fi

if grep -qF "me/personal" "$ALLFAIL_ERR" && grep -qF "acme/org-repo" "$ALLFAIL_ERR"; then
    PASS "names every failed repository on stderr in the all-failed case"
else
    FAIL "names every failed repository on stderr in the all-failed case" "stderr: $(tr '\n' '|' < "$ALLFAIL_ERR")"
fi

if grep -qF '"Pin dependencies"' "$ALLFAIL_OUT" || grep -qF '"Bump jq from 1.6 to 1.7"' "$ALLFAIL_OUT"; then
    FAIL "produces no PR results when every repository's lookup failed" "stdout: $(tr '\n' '|' < "$ALLFAIL_OUT")"
else
    PASS "produces no PR results when every repository's lookup failed"
fi

# 9. The repository enumeration call sets an explicit page size via the
#    query string and keeps pagination and GET semantics, so a large account
#    doesn't pay default-size extra round trips, and no field-adding flag
#    silently flips the request to a POST.
CALL_LOG_A="$STUBDIR/calls_a.txt"
: > "$CALL_LOG_A"
PATH="$STUBDIR:$PATH" STUB_CALL_LOG="$CALL_LOG_A" bash "$LIST_SH" > /dev/null 2>/dev/null

RECORDED_A="$(tr '\n' '|' < "$CALL_LOG_A")"

if [ -s "$CALL_LOG_A" ] && grep -qF "user/repos?per_page=100" "$CALL_LOG_A"; then
    PASS "repository enumeration requests the literal user/repos?per_page=100 query string"
else
    FAIL "repository enumeration requests the literal user/repos?per_page=100 query string" "recorded: $RECORDED_A"
fi

if grep -qF -- "--paginate" "$CALL_LOG_A"; then
    PASS "repository enumeration keeps pagination alongside the explicit page size"
else
    FAIL "repository enumeration keeps pagination alongside the explicit page size" "recorded: $RECORDED_A"
fi

if grep -qE -- "(^| )(-f|-F|--field|--raw-field|--input|-X|--method)( |$)" "$CALL_LOG_A"; then
    FAIL "repository enumeration stays a GET request (no field-adding or method-override flags)" "recorded: $RECORDED_A"
else
    PASS "repository enumeration stays a GET request (no field-adding or method-override flags)"
fi

echo ""
echo "SUMMARY: $PASS_COUNT passed, $FAIL_COUNT failed"

[ "$FAIL_COUNT" -eq 0 ]
