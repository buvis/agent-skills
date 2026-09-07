#!/usr/bin/env bash
# Test harness for sonnet-run.sh (macOS bash 3.2 compatible). Stubs the
# `claude` binary on PATH and asserts on its OBSERVABLE argv/stdin/exit codes,
# never on sonnet-run.sh's internals. Modeled on
# use-codex/scripts/test_codex_run.sh.
set -u

SONNET_RUN_SH="$(cd "$(dirname "$0")" && pwd)/sonnet-run.sh"
[ -n "${1:-}" ] && SONNET_RUN_SH="$1"

# ── assert helpers ────────────────────────────────────────────────────────────
PASS_COUNT=0
FAIL_COUNT=0
PASS() { echo "PASS: $1"; PASS_COUNT=$((PASS_COUNT + 1)); }
FAIL() { echo "FAIL: $1 -- $2"; FAIL_COUNT=$((FAIL_COUNT + 1)); }

# True (exit 0) if FILE contains NEEDLE immediately followed by VALUE as
# consecutive argv tokens.
argv_has_pair() {
    local file="$1" needle="$2" value="$3" prev="" tok
    while IFS= read -r tok; do
        if [ "$prev" = "$needle" ] && [ "$tok" = "$value" ]; then
            return 0
        fi
        prev="$tok"
    done < "$file"
    return 1
}

# Echoes how many argv tokens in FILE are exactly NEEDLE (0 when none, empty
# when FILE is absent). Lets a case demand that an option appears ONCE, not
# merely somewhere - a duplicate the child CLI would resolve last-one-wins.
argv_count() {
    grep -cxF -- "$2" "$1" 2>/dev/null || true
}

# ── cleanup registry ──────────────────────────────────────────────────────────
_DIRS=()
cleanup() {
    local d
    for d in "${_DIRS[@]+"${_DIRS[@]}"}"; do
        rm -rf "$d"
    done
}
trap cleanup EXIT

WORK=$(mktemp -d)
_DIRS+=("$WORK")

# ── stub `claude` binary on PATH ──────────────────────────────────────────────
STUBDIR="$WORK/stub"
mkdir -p "$STUBDIR"

cat > "$STUBDIR/claude" <<'STUB'
#!/bin/bash
printf '%s\n' "$@" > "${CLAUDE_ARGV_FILE:?}"
cat > "${CLAUDE_STDIN_FILE:?}"
echo "stub-claude-ran"
exit "${STUB_EXIT_CODE:-0}"
STUB
chmod +x "$STUBDIR/claude"

# sonnet-run.sh re-prepends mise's own PATH ahead of ours whenever `mise` is
# reachable, which would put the real claude binary ahead of the stub.
# Excluding mise's location from the PATH we hand to sonnet-run.sh keeps that
# branch inert, so lookup always resolves to our stub.
RUN_PATH="$STUBDIR:/usr/bin:/bin"

# ── per-case fixtures ─────────────────────────────────────────────────────────
# Nothing prompt- or session-shaped is shared between cases: every case gets its
# own prompt text and its own uuid, so an implementation carrying baked-in
# literals cannot satisfy the assertions below - it has to forward the value it
# was handed. Prompt files are named neutrally and identically in shape
# (p1.txt, p2.txt, ...) so only a file's CONTENT can drive routing decisions.
PROMPT_SEQ=0
UUID_SEQ=0
MODEL_SEQ=0

# make_prompt <case> [leading-text] — writes a prompt unique to <case> and sets
# PROMPT_TEXT (the exact bytes) and PROMPT_F (the fixture path) for it.
make_prompt() {
    PROMPT_SEQ=$((PROMPT_SEQ + 1))
    PROMPT_TEXT="${2:-}say hi from sonnet, case $1"
    PROMPT_F="$WORK/p$PROMPT_SEQ.txt"
    printf '%s' "$PROMPT_TEXT" > "$PROMPT_F"
}

# new_uuid — echoes a fresh session id: uuidgen when the runner has it, a
# generated value otherwise.
new_uuid() {
    if command -v uuidgen > /dev/null 2>&1; then
        uuidgen | tr '[:upper:]' '[:lower:]'
        return 0
    fi
    UUID_SEQ=$((UUID_SEQ + 1))
    printf '%08x-%04x-4%03x-8%03x-%012x\n' \
        $((RANDOM * 32768 + RANDOM)) "$RANDOM" $((RANDOM % 4096)) $((RANDOM % 4096)) \
        $((RANDOM * 1073741824 + RANDOM * 32768 + RANDOM + UUID_SEQ))
}

# new_model — echoes a fresh model id, unique per case. No case passes a model
# name the wrapper could know in advance, so a value on argv can only have come
# from reading the one handed to -m.
new_model() {
    MODEL_SEQ=$((MODEL_SEQ + 1))
    printf 'nonce-model-%s-%s\n' "$MODEL_SEQ" "$RANDOM"
}

# A directory unrelated to any prompt file: -d must be read as its own option
# value, never derived from the prompt path.
ADD_DIR="$WORK/adddir"
mkdir -p "$ADD_DIR"

# run_sonnet <name> [args...] — runs sonnet-run.sh with SENTINEL data on the
# wrapper's own stdin; sets RC, STDOUT_F, STDERR_F, and per-test capture paths.
run_sonnet() {
    local name="$1"
    shift
    export CLAUDE_ARGV_FILE="$WORK/$name.argv"
    export CLAUDE_STDIN_FILE="$WORK/$name.stdin"
    STDOUT_F="$WORK/$name.stdout"
    STDERR_F="$WORK/$name.stderr"
    RC=0
    PATH="$RUN_PATH" bash "$SONNET_RUN_SH" "$@" \
        > "$STDOUT_F" 2> "$STDERR_F" <<< 'SENTINEL_STDIN_DATA' || RC=$?
}

# ══ T1: plain -f run (headless claude --print) ════════════════════════════════
make_prompt t1
run_sonnet t1 -f "$PROMPT_F"

# 1. Child stdin must be redirected to /dev/null. Without the guard the child
#    inherits the wrapper's stdin and reads SENTINEL_STDIN_DATA (the PRD 00040
#    hang class: a child blocking on inherited stdin stalls unattended runs).
if [ -f "$CLAUDE_STDIN_FILE" ] && [ ! -s "$CLAUDE_STDIN_FILE" ]; then
    PASS "claude child stdin is /dev/null"
else
    FAIL "claude child stdin is /dev/null" \
         "stub captured $(wc -c < "$CLAUDE_STDIN_FILE" 2>/dev/null | tr -d ' ' || echo '?') byte(s) of stdin; expected 0 (child inherited the wrapper's stdin instead of /dev/null)"
fi

# 2. Argv regression lock for the plain -f run (adding the stdin guard must
#    not perturb argv): claude --print --model sonnet <PROMPT>.
EXPECTED_ARGV_FILE="$WORK/t1.expected"
printf '%s\n' "--print" "--model" "sonnet" "$PROMPT_TEXT" > "$EXPECTED_ARGV_FILE"
if diff -q "$EXPECTED_ARGV_FILE" "$CLAUDE_ARGV_FILE" >/dev/null 2>&1; then
    PASS "plain -f argv is exactly: --print --model sonnet <PROMPT>"
else
    FAIL "plain -f argv is exactly: --print --model sonnet <PROMPT>" \
         "got: $(tr '\n' ' ' < "$CLAUDE_ARGV_FILE" 2>/dev/null || echo '<no claude invocation>')"
fi

# 3. Happy path exits 0 and surfaces the backend's output.
if [ "$RC" -eq 0 ] && grep -qF "stub-claude-ran" "$STDOUT_F"; then
    PASS "plain -f run exits 0 and passes claude stdout through"
else
    FAIL "plain -f run exits 0 and passes claude stdout through" \
         "rc=$RC; stdout: $(cat "$STDOUT_F")"
fi

# ══ T1b: hyphen-prefixed prompt content routes through stdin, not argv ═══════
# claude's own CLI rejects a positional prompt starting with "-" as an unknown
# option ("error: unknown option '- [ ] ...'"); a prompt sourced from a ledger
# checklist line hits this on every dispatch (2026-09-02, multi-file eval).
make_prompt t1b '- [ ] '
run_sonnet t1b -f "$PROMPT_F"
if [ "$RC" -eq 0 ]; then
    PASS "hyphen-prefixed prompt: dispatch exits 0"
else
    FAIL "hyphen-prefixed prompt: dispatch exits 0" "rc=$RC; stderr: $(cat "$STDERR_F")"
fi
if [ -f "$CLAUDE_ARGV_FILE" ] && ! grep -qF -- "$PROMPT_TEXT" "$CLAUDE_ARGV_FILE"; then
    PASS "hyphen-prefixed prompt: content is NOT on claude's argv"
else
    FAIL "hyphen-prefixed prompt: content is NOT on claude's argv" \
         "argv: $(tr '\n' ' ' < "$CLAUDE_ARGV_FILE" 2>/dev/null || echo '<no claude invocation>')"
fi
if [ -f "$CLAUDE_STDIN_FILE" ] && [ "$(cat "$CLAUDE_STDIN_FILE")" = "$PROMPT_TEXT" ]; then
    PASS "hyphen-prefixed prompt: content reaches claude via stdin, byte-verbatim"
else
    FAIL "hyphen-prefixed prompt: content reaches claude via stdin, byte-verbatim" \
         "stdin capture: '$(cat "$CLAUDE_STDIN_FILE" 2>/dev/null || echo MISSING)'"
fi

# ══ T2: -m MODEL overrides the model ══════════════════════════════════════════
# The model is a value the caller chooses, so the case asks for one nothing
# could have baked in: a wrapper that emits a fixed model name on the mere
# presence of -m never carries this value through.
T2_MODEL=$(new_model)
make_prompt t2
run_sonnet t2 -m "$T2_MODEL" -f "$PROMPT_F"

# 4. -m: argv carries --model <the requested model> (and stays on the headless
# --print path).
if argv_has_pair "$CLAUDE_ARGV_FILE" "--model" "$T2_MODEL" && grep -qxF -- "--print" "$CLAUDE_ARGV_FILE"; then
    PASS "-m MODEL: argv carries --print and --model with the requested model"
else
    FAIL "-m MODEL: argv carries --print and --model with the requested model" \
         "asked for model '$T2_MODEL'; argv: $(tr '\n' ' ' < "$CLAUDE_ARGV_FILE" 2>/dev/null || echo '<no claude invocation>')"
fi

# ══ T3: -a maps to --permission-mode acceptEdits (NOT bypass) ═════════════════
make_prompt t3
run_sonnet t3 -a -f "$PROMPT_F"

# 5. -a: argv grants acceptEdits and NOTHING WIDER. The old mapping sent
# bypassPermissions, making the documented weaker flag a silent -y. Handing the
# child both modes is the same grant by another route - claude honours the last
# --permission-mode it is given - so the case demands exactly one such token,
# paired with acceptEdits, and no trace of bypassPermissions anywhere on argv.
T3_PERM_COUNT=$(argv_count "$CLAUDE_ARGV_FILE" "--permission-mode")
if [ "$T3_PERM_COUNT" = "1" ] \
   && argv_has_pair "$CLAUDE_ARGV_FILE" "--permission-mode" "acceptEdits" \
   && ! grep -qF -- "bypassPermissions" "$CLAUDE_ARGV_FILE" 2>/dev/null; then
    PASS "-a: argv grants acceptEdits only - one --permission-mode, no bypassPermissions"
else
    FAIL "-a: argv grants acceptEdits only - one --permission-mode, no bypassPermissions" \
         "--permission-mode token count=${T3_PERM_COUNT:-<no claude invocation>}; argv: $(tr '\n' ' ' < "$CLAUDE_ARGV_FILE" 2>/dev/null || echo '<no claude invocation>')"
fi

# ══ T3b: -y maps to --permission-mode bypassPermissions ═══════════════════════
make_prompt t3b
run_sonnet t3b -y -f "$PROMPT_F"

# 5b. -y: the mirror image of T3 - exactly one --permission-mode token, and the
# mode it carries is bypassPermissions. One token means the grant the child acts
# on is the one this flag asked for, not whatever a second copy would override
# it with.
T3B_PERM_COUNT=$(argv_count "$CLAUDE_ARGV_FILE" "--permission-mode")
if [ "$T3B_PERM_COUNT" = "1" ] \
   && argv_has_pair "$CLAUDE_ARGV_FILE" "--permission-mode" "bypassPermissions"; then
    PASS "-y: argv carries exactly one --permission-mode, and it is bypassPermissions"
else
    FAIL "-y: argv carries exactly one --permission-mode, and it is bypassPermissions" \
         "--permission-mode token count=${T3B_PERM_COUNT:-<no claude invocation>}; argv: $(tr '\n' ' ' < "$CLAUDE_ARGV_FILE" 2>/dev/null || echo '<no claude invocation>')"
fi

# ══ T4: -d DIR maps to --add-dir DIR ══════════════════════════════════════════
# The directory is unrelated to the prompt file's location, so the value can
# only come from reading the -d option itself.
make_prompt t4
run_sonnet t4 -d "$ADD_DIR" -f "$PROMPT_F"

# 6. -d: argv carries the pair --add-dir <DIR>.
if argv_has_pair "$CLAUDE_ARGV_FILE" "--add-dir" "$ADD_DIR"; then
    PASS "-d DIR: argv carries --add-dir DIR"
else
    FAIL "-d DIR: argv carries --add-dir DIR" \
         "argv: $(tr '\n' ' ' < "$CLAUDE_ARGV_FILE" 2>/dev/null || echo '<no claude invocation>')"
fi

# ══ T5: -o tees output to the file ════════════════════════════════════════════
T5_OUT="$WORK/t5.out"
make_prompt t5
run_sonnet t5 -f "$PROMPT_F" -o "$T5_OUT"

# 7. -o: output file receives the backend output.
if grep -qF "stub-claude-ran" "$T5_OUT" 2>/dev/null; then
    PASS "-o: output file contains the claude output"
else
    FAIL "-o: output file contains the claude output" \
         "rc=$RC; -o file contents: $(cat "$T5_OUT" 2>/dev/null || echo '<missing>')"
fi

# ══ T6: -s/--silent is accepted as a no-op ════════════════════════════════════
make_prompt t6
run_sonnet t6 -s -f "$PROMPT_F"

# 8. -s: run succeeds and no -s token leaks into claude's argv.
if [ "$RC" -eq 0 ] && ! grep -qxF -- "-s" "$CLAUDE_ARGV_FILE" 2>/dev/null && grep -qxF -- "--print" "$CLAUDE_ARGV_FILE" 2>/dev/null; then
    PASS "-s is accepted as a no-op (no -s token in claude argv)"
else
    FAIL "-s is accepted as a no-op (no -s token in claude argv)" \
         "rc=$RC; argv: $(tr '\n' ' ' < "$CLAUDE_ARGV_FILE" 2>/dev/null || echo '<no claude invocation>')"
fi

# ══ T7: missing prompt file -> stderr + non-zero + no dispatch ════════════════
run_sonnet t7 -f "$WORK/does-not-exist.txt"

# 9. Missing prompt file: non-zero exit.
if [ "$RC" -ne 0 ]; then
    PASS "missing prompt file exits non-zero"
else
    FAIL "missing prompt file exits non-zero" "rc=0"
fi

# 10. Missing prompt file: the error lands on stderr, not stdout.
if grep -q "not found" "$STDERR_F" 2>/dev/null && ! grep -q "not found" "$STDOUT_F" 2>/dev/null; then
    PASS "missing prompt file: error text is on stderr"
else
    FAIL "missing prompt file: error text is on stderr" \
         "stderr: $(cat "$STDERR_F") -- stdout: $(cat "$STDOUT_F")"
fi

# 11. Missing prompt file: claude is never invoked.
if [ ! -f "$CLAUDE_ARGV_FILE" ]; then
    PASS "missing prompt file: claude is never invoked"
else
    FAIL "missing prompt file: claude is never invoked" \
         "argv: $(tr '\n' ' ' < "$CLAUDE_ARGV_FILE")"
fi

# ══ T8: no prompt at all -> stderr + non-zero ═════════════════════════════════
run_sonnet t8

# 12. Missing prompt: non-zero exit with the error on stderr.
if [ "$RC" -ne 0 ] && grep -qi "prompt required" "$STDERR_F" 2>/dev/null; then
    PASS "missing prompt exits non-zero with the error on stderr"
else
    FAIL "missing prompt exits non-zero with the error on stderr" \
         "rc=$RC; stderr: $(cat "$STDERR_F") -- stdout: $(cat "$STDOUT_F")"
fi

# ══ T9: child exit code propagates ════════════════════════════════════════════
make_prompt t9
export STUB_EXIT_CODE=7
run_sonnet t9 -f "$PROMPT_F"
unset STUB_EXIT_CODE

# 13. Exit-code propagation: the wrapper's exit code equals the child's.
if [ "$RC" -eq 7 ]; then
    PASS "child exit code (7) propagates as sonnet-run.sh's own exit code"
else
    FAIL "child exit code (7) propagates as sonnet-run.sh's own exit code" \
         "got exit code $RC"
fi

# ══ T10: -S UUID pins the session id in prompt mode ═════════════════════════
# A caller that pins the session id can locate the transcript afterwards, so the
# uuid it asked for must reach claude verbatim as a two-token argv pair.
T10_UUID=$(new_uuid)
make_prompt t10
run_sonnet t10 -S "$T10_UUID" -f "$PROMPT_F"

# 14. -S: argv carries the pair --session-id <uuid> on the headless --print path.
if [ "$RC" -eq 0 ] && argv_has_pair "$CLAUDE_ARGV_FILE" "--session-id" "$T10_UUID" && grep -qxF -- "--print" "$CLAUDE_ARGV_FILE" 2>/dev/null; then
    PASS "-S UUID: prompt-mode argv carries --print and --session-id <uuid>"
else
    FAIL "-S UUID: prompt-mode argv carries --print and --session-id <uuid>" \
         "rc=$RC; argv: $(tr '\n' ' ' < "$CLAUDE_ARGV_FILE" 2>/dev/null || echo '<no claude invocation>')"
fi

# ══ T10b: --session-id long form is equivalent ═══════════════════════════════
T10B_UUID=$(new_uuid)
make_prompt t10b
run_sonnet t10b --session-id "$T10B_UUID" -f "$PROMPT_F"

# 15. Long spelling produces the same argv pair as the short one.
if [ "$RC" -eq 0 ] && argv_has_pair "$CLAUDE_ARGV_FILE" "--session-id" "$T10B_UUID" && grep -qxF -- "--print" "$CLAUDE_ARGV_FILE" 2>/dev/null; then
    PASS "--session-id UUID: long form yields the same argv pair as -S"
else
    FAIL "--session-id UUID: long form yields the same argv pair as -S" \
         "rc=$RC; argv: $(tr '\n' ' ' < "$CLAUDE_ARGV_FILE" 2>/dev/null || echo '<no claude invocation>')"
fi

# ══ T11: resume mode drops --session-id ══════════════════════════════════════
# A resumed session already has an id; the pinned one must be suppressed rather
# than forwarded when the caller also asks to resume.
run_sonnet t11 -S "$(new_uuid)" -r

# 16. -r with -S: claude is dispatched with --resume and NO --session-id token.
if grep -qxF -- "--resume" "$CLAUDE_ARGV_FILE" 2>/dev/null && ! grep -qxF -- "--session-id" "$CLAUDE_ARGV_FILE" 2>/dev/null; then
    PASS "-r with -S: argv carries --resume and no --session-id token"
else
    FAIL "-r with -S: argv carries --resume and no --session-id token" \
         "rc=$RC; argv: $(tr '\n' ' ' < "$CLAUDE_ARGV_FILE" 2>/dev/null || echo '<no claude invocation>')"
fi

# ══ T11b: interactive mode drops --session-id ════════════════════════════════
make_prompt t11b
run_sonnet t11b -S "$(new_uuid)" -i -f "$PROMPT_F"

# 17. -i with -S: the prompt still reaches claude, the session id does not.
if grep -qxF -- "$PROMPT_TEXT" "$CLAUDE_ARGV_FILE" 2>/dev/null && ! grep -qxF -- "--session-id" "$CLAUDE_ARGV_FILE" 2>/dev/null; then
    PASS "-i with -S: argv carries the prompt and no --session-id token"
else
    FAIL "-i with -S: argv carries the prompt and no --session-id token" \
         "rc=$RC; argv: $(tr '\n' ' ' < "$CLAUDE_ARGV_FILE" 2>/dev/null || echo '<no claude invocation>')"
fi

# ══ T11c: continue mode drops --session-id ═══════════════════════════════════
run_sonnet t11c -S "$(new_uuid)" -c

# 18. -c with -S: claude is dispatched with --continue and NO --session-id token.
if grep -qxF -- "--continue" "$CLAUDE_ARGV_FILE" 2>/dev/null && ! grep -qxF -- "--session-id" "$CLAUDE_ARGV_FILE" 2>/dev/null; then
    PASS "-c with -S: argv carries --continue and no --session-id token"
else
    FAIL "-c with -S: argv carries --continue and no --session-id token" \
         "rc=$RC; argv: $(tr '\n' ' ' < "$CLAUDE_ARGV_FILE" 2>/dev/null || echo '<no claude invocation>')"
fi

# ══ T12: -S alongside -m and -d keeps every pair intact ═══════════════════
# Three value-taking options in one command line: an option parser that consumes
# the wrong argument would cross the values over and still dispatch. Two DECOYS
# make the crossing visible, both sitting AFTER -S on the command line so the
# session id is not the last uuid-looking thing a caller could scavenge:
#   - the model value is itself a uuid, so it is indistinguishable from a
#     session id by shape alone;
#   - the -d directory carries a third uuid inside its path, for the same reason
#     at a looser resolution.
# Only reading the value that follows -S yields the uuid the caller pinned.
T12_UUID=$(new_uuid)
T12_MODEL=$(new_uuid)
T12_DECOY_UUID=$(new_uuid)
T12_ADD_DIR="$WORK/adddir-$T12_DECOY_UUID"
mkdir -p "$T12_ADD_DIR"
make_prompt t12
run_sonnet t12 -S "$T12_UUID" -m "$T12_MODEL" -d "$T12_ADD_DIR" -f "$PROMPT_F"

# 19. Each value-taking option keeps its own value: one --session-id, carrying
# the uuid that followed -S rather than the decoy, while the decoy travels on
# --add-dir where it was sent and the model is the one that was asked for.
T12_SID_COUNT=$(argv_count "$CLAUDE_ARGV_FILE" "--session-id")
if [ "$T12_SID_COUNT" = "1" ] \
   && argv_has_pair "$CLAUDE_ARGV_FILE" "--session-id" "$T12_UUID" \
   && argv_has_pair "$CLAUDE_ARGV_FILE" "--model" "$T12_MODEL" \
   && argv_has_pair "$CLAUDE_ARGV_FILE" "--add-dir" "$T12_ADD_DIR"; then
    PASS "-S with -m and -d: argv carries --session-id, --model and --add-dir with their own values"
else
    FAIL "-S with -m and -d: argv carries --session-id, --model and --add-dir with their own values" \
         "rc=$RC; asked for session id '$T12_UUID' (decoy uuid '$T12_DECOY_UUID' belongs to --add-dir) and model '$T12_MODEL'; --session-id token count=${T12_SID_COUNT:-<no claude invocation>}; argv: $(tr '\n' ' ' < "$CLAUDE_ARGV_FILE" 2>/dev/null || echo '<no claude invocation>')"
fi

# ══ T13: hyphen-prefixed prompt keeps --session-id on argv ════════════
# The stdin-routing branch (T1b) builds its own argv; the session id must
# survive it instead of being dropped with the positional prompt.
T13_UUID=$(new_uuid)
make_prompt t13 '- [ ] '
run_sonnet t13 -S "$T13_UUID" -f "$PROMPT_F"

# 20. Hyphen-prefixed prompt with -S: content still goes via stdin, verbatim.
if [ -f "$CLAUDE_STDIN_FILE" ] && [ "$(cat "$CLAUDE_STDIN_FILE")" = "$PROMPT_TEXT" ]; then
    PASS "hyphen-prefixed prompt with -S: content still reaches claude via stdin"
else
    FAIL "hyphen-prefixed prompt with -S: content still reaches claude via stdin" \
         "rc=$RC; stdin capture: '$(cat "$CLAUDE_STDIN_FILE" 2>/dev/null || echo MISSING)'"
fi

# 21. Hyphen-prefixed prompt with -S: argv carries the pair, not the prompt.
if argv_has_pair "$CLAUDE_ARGV_FILE" "--session-id" "$T13_UUID" && ! grep -qF -- "$PROMPT_TEXT" "$CLAUDE_ARGV_FILE" 2>/dev/null; then
    PASS "hyphen-prefixed prompt with -S: argv carries --session-id <uuid> and not the prompt"
else
    FAIL "hyphen-prefixed prompt with -S: argv carries --session-id <uuid> and not the prompt" \
         "rc=$RC; argv: $(tr '\n' ' ' < "$CLAUDE_ARGV_FILE" 2>/dev/null || echo '<no claude invocation>')"
fi

# ══ T14: -h usage mentions -S/--session-id ═══════════════════════════
run_sonnet t14 -h

# 22. Help text documents both spellings on one option line of the usage block.
# Anchored to the start of a line so an unrelated "-Something" elsewhere in the
# help cannot stand in for the documented option.
if [ "$RC" -eq 0 ] && grep -qE '^[[:space:]]*-S[,[:space:]].*--session-id' "$STDOUT_F" 2>/dev/null; then
    PASS "-h: usage text documents -S/--session-id"
else
    FAIL "-h: usage text documents -S/--session-id" \
         "rc=$RC; stdout: $(cat "$STDOUT_F" 2>/dev/null || echo '<empty>')"
fi

# ══ summary ═══════════════════════════════════════════════════════════════════
echo ""
echo "SUMMARY: $PASS_COUNT passed, $FAIL_COUNT failed"

[ "$FAIL_COUNT" -eq 0 ]
