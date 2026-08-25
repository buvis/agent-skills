#!/bin/bash
# List sessions that have persisted tasks for the current project.
#
# Output (stdout, always JSON):
#   {"sessions": [{sessionId, summary, modified, taskCount}, ...]}  sorted newest first
#   {"error": "<code>", ...}                                        on a skip/failure
#
# Error codes — benign skips (caller stays silent):
#   no_project_data | no_tasks_dir | no_index
# Error codes — LOUD (caller must report; Claude Code's on-disk layout drifted
# and this script needs updating, otherwise restore silently does nothing):
#   index_unreadable | schema_unexpected
#
# This script reads Claude Code internals: sessions-index.json's .entries[]
# (each {sessionId, summary, modified}) and ~/.claude/tasks/<sessionId>/*.json.
# Those are undocumented and may change — hence the schema checks below.

set -e

PROJECT_PATH="${1:-$(pwd)}"
TASKS_DIR="$HOME/.claude/tasks"
# Encode path: /Users/you/foo.bar -> -Users-you-foo-bar
PROJECT_DIR="$HOME/.claude/projects/$(echo "$PROJECT_PATH" | sed 's|^/|-|' | tr '/.' '-')"
INDEX_FILE="$PROJECT_DIR/sessions-index.json"

[[ -d "$PROJECT_DIR" ]] || { echo '{"error": "no_project_data"}'; exit 1; }
[[ -d "$TASKS_DIR" ]]   || { echo '{"error": "no_tasks_dir"}'; exit 1; }
[[ -f "$INDEX_FILE" ]]  || { echo '{"error": "no_index"}'; exit 1; }

# --- Fail loud if the index schema we depend on has drifted ---
if ! jq -e . "$INDEX_FILE" >/dev/null 2>&1; then
    echo '{"error": "index_unreadable", "detail": "sessions-index.json is not valid JSON; update list-task-sessions.sh"}'
    exit 1
fi
if ! jq -e '.entries | type == "array"' "$INDEX_FILE" >/dev/null 2>&1; then
    echo '{"error": "schema_unexpected", "detail": "sessions-index.json has no .entries array; Claude Code layout changed, update list-task-sessions.sh"}'
    exit 1
fi
# Entries exist but none carry the fields we read -> the entry shape changed.
if jq -e '(.entries | length) > 0 and ([.entries[] | select(.sessionId and .modified)] | length == 0)' "$INDEX_FILE" >/dev/null 2>&1; then
    echo '{"error": "schema_unexpected", "detail": "sessions-index.json entries lack sessionId/modified; layout changed, update list-task-sessions.sh"}'
    exit 1
fi

# Emit one session object per index entry (sorted newest first), keeping only
# those with at least one task file. taskCount comes from the shell, not jq.
jq -c '.entries | sort_by(.modified) | reverse | .[]
       | {sessionId, summary: (.summary // "No summary"), modified}' "$INDEX_FILE" \
| while read -r session; do
    session_id=$(echo "$session" | jq -r '.sessionId')
    count=$(ls -1 "$TASKS_DIR/$session_id"/*.json 2>/dev/null | wc -l | tr -d ' ')
    [[ "$count" -gt 0 ]] && echo "$session" | jq -c --argjson c "$count" '.taskCount = $c'
done \
| jq -s '{sessions: .}'
