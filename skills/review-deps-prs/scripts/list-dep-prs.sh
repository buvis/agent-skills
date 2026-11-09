#!/bin/bash
# List dependency update PRs across all repos the authenticated user has access to
# Detects by author (app/renovate, renovate[bot], app/dependabot, dependabot[bot]) and title patterns

set -e

# Every repo the token can reach: own, collaborator and organization repos.
# (`gh repo list` without an owner lists only the account's own repos.)
REPOS=$(gh api 'user/repos?per_page=100' --paginate --jq '.[].full_name') \
    || { echo "gh api user/repos failed; run 'gh auth status'" >&2; exit 1; }

if [ -z "$REPOS" ]; then
    echo "No repos found or gh not authenticated"
    exit 1
fi

echo "=== Dependency Update PRs ==="
echo ""

FAILED_REPOS=""

for REPO in $REPOS; do
    PRS=$(gh pr list --repo "$REPO" --state open --json number,title,author,labels,createdAt,url \
        --jq '.[] | select(
            (.author.login | test("^(app/)?(renovate|dependabot)(\\[bot\\])?$")) or
            (.title | test("^(chore\\(deps\\)|bump |update |\\[security\\])"; "i")) or
            (.title | test("^fix\\(deps\\)"; "i"))
        )' 2>/dev/null) && PR_STATUS=0 || PR_STATUS=$?
    if [ "$PR_STATUS" -ne 0 ]; then
        echo "gh pr list failed for $REPO" >&2
        FAILED_REPOS="$FAILED_REPOS $REPO"
        continue
    fi

    if [ -n "$PRS" ]; then
        echo "--- $REPO ---"
        echo "$PRS"
        echo ""
    fi
done

if [ -n "$FAILED_REPOS" ]; then
    exit 2
fi
