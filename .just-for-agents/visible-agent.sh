#!/usr/bin/env bash
set -euo pipefail

SESSION="just-for-agents-$1"
WINDOW_HINT="$2"
LABEL="$3"
RUNNER="$4"
WINDOW_BASE=$(python3 -c 'import re, sys; text = sys.argv[1]; slug = re.sub(r"[^a-z0-9]+", "-", text.lower()).strip("-"); print((slug or "task")[:24])' "$WINDOW_HINT")
WINDOW_NAME="${WINDOW_BASE}-$(date +%H%M)"

[ -x "$RUNNER" ] || { echo "ERROR: runner is not executable: $RUNNER" >&2; exit 1; }

if command -v tmux >/dev/null 2>&1; then
    RUN_ROOT="${TMPDIR:-/tmp}/just-for-agents"
    RUN_ID="$(date +%Y%m%d-%H%M%S)"
    LOG_FILE="$RUN_ROOT/$1-$RUN_ID.log"
    STATUS_FILE="$RUN_ROOT/$1-$RUN_ID.status"
    mkdir -p "$RUN_ROOT"
    RUNNER_Q=$(printf '%q' "$RUNNER")
    LOG_Q=$(printf '%q' "$LOG_FILE")
    STATUS_Q=$(printf '%q' "$STATUS_FILE")
    TMUX_CMD="set -uo pipefail; $RUNNER_Q 2>&1 | tee $LOG_Q; status=\${PIPESTATUS[0]}; printf '%s\n' \"\$status\" > $STATUS_Q; exit \"\$status\""
    TMUX_CMD_Q=$(printf '%q' "$TMUX_CMD")
    if tmux has-session -t "$SESSION" 2>/dev/null; then
        TARGET=$(tmux new-window -d -P -F '#{session_name}:#{window_index}' -t "$SESSION" -n "$WINDOW_NAME" "bash -lc $TMUX_CMD_Q")
    else
        TARGET=$(tmux new-session -d -P -F '#{session_name}:#{window_index}' -s "$SESSION" -n "$WINDOW_NAME" "bash -lc $TMUX_CMD_Q")
    fi
    tmux set-window-option -t "$TARGET" remain-on-exit on >/dev/null
    echo "$LABEL is running in tmux session '$SESSION', window '$WINDOW_NAME'." >&2
    ATTACH_CMD="tmux attach-session -t $SESSION"
    CLIENT_COUNT=$(tmux list-clients -t "$SESSION" 2>/dev/null | wc -l | awk '{print $1}' || printf '0\n')
    if [ "${TERM_PROGRAM:-}" = "iTerm.app" ] && [ "${CLIENT_COUNT:-0}" -eq 0 ] && command -v osascript >/dev/null 2>&1; then
        CC_ATTACH_CMD="tmux -CC attach-session -t $SESSION"
        CC_ATTACH_CMD_OSA=$(printf '%s' "$CC_ATTACH_CMD" | sed 's/\\/\\\\/g; s/"/\\"/g')
        if osascript \
            -e 'tell application id "com.googlecode.iterm2"' \
            -e 'activate' \
            -e "create window with default profile command \"$CC_ATTACH_CMD_OSA\"" \
            -e 'end tell' >/dev/null 2>&1; then
            echo "Opened iTerm2 tmux control-mode window for session '$SESSION'." >&2
        else
            echo "Unable to launch iTerm2 tmux control mode automatically." >&2
        fi
    fi
    echo "Attach with: $ATTACH_CMD" >&2
    echo "Focus this run with: tmux select-window -t $TARGET" >&2
    while [ ! -f "$STATUS_FILE" ]; do
        sleep 1
    done
    STATUS=$(cat "$STATUS_FILE")
    cat "$LOG_FILE"
    if [ "$STATUS" -ne 0 ]; then
        echo "$LABEL failed. Reattach to inspect: tmux attach-session -t $SESSION" >&2
        exit "$STATUS"
    fi
    exit 0
fi

echo "tmux not found. Running $LABEL directly..." >&2
"$RUNNER"
