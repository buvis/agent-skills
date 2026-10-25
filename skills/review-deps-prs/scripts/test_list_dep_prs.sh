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
case "$1 $2" in
    "repo list")
        DATA='[{"nameWithOwner":"me/personal"}]' ;;
    "api user/repos")
        [ -n "${STUB_FAIL_API:-}" ] && { echo "gh: Bad credentials (HTTP 401)" >&2; exit 1; }
        DATA='[{"full_name":"me/personal"},{"full_name":"acme/org-repo"}]' ;;
    "pr list")
        case "$REPO" in
            me/personal)
                DATA='[{"number":1,"title":"Pin dependencies","author":{"login":"app/renovate","is_bot":true},"labels":[],"createdAt":"2026-10-01T00:00:00Z","url":"https://example.invalid/1"},
                       {"number":3,"title":"feat: add thing","author":{"login":"someone","is_bot":false},"labels":[],"createdAt":"2026-10-03T00:00:00Z","url":"https://example.invalid/3"}]' ;;
            acme/org-repo)
                DATA='[{"number":2,"title":"Bump jq from 1.6 to 1.7","author":{"login":"dependabot[bot]","is_bot":true},"labels":[],"createdAt":"2026-10-02T00:00:00Z","url":"https://example.invalid/2"},
                       {"number":4,"title":"Pin jq to 1.7","author":{"login":"dependabot[bot]","is_bot":true},"labels":[],"createdAt":"2026-10-04T00:00:00Z","url":"https://example.invalid/4"}]' ;;
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

echo ""
echo "SUMMARY: $PASS_COUNT passed, $FAIL_COUNT failed"

[ "$FAIL_COUNT" -eq 0 ]
