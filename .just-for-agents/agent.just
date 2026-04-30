[no-cd]
test-agent name prompt agent='gemini' model='':
    #!/usr/bin/env bash
    echo "--- SANDBOX SETUP ---"
    SANDBOX="/tmp/just-test-{{name}}"
    echo "Target: $SANDBOX"
    rm -rf "$SANDBOX"
    mkdir -p "$SANDBOX"
    cp Justfile "$SANDBOX/"
    [ -f VERSION ] && cp VERSION "$SANDBOX/"
    [ -d .just-for-agents ] && cp -R .just-for-agents "$SANDBOX/"
    echo "RADICALLY SIMPLE. Use ONLY 'just' recipes. Run 'just bootstrap' then 'just'." > "$SANDBOX/GEMINI.md"

    FULL_PROMPT="{{prompt}} Verify changes by running 'just schema' and ensure it succeeds."

    echo "--- EXECUTION: {{agent}} ({{model}}) ---"
    cd "$SANDBOX"

    case "{{agent}}" in
        gemini)
            MODEL_FLAG=""
            [ -n "{{model}}" ] && MODEL_FLAG="-m {{model}}"
            gemini $MODEL_FLAG -p "$FULL_PROMPT" --yolo
            ;;
        copilot)
            MODEL_FLAG=""
            [ -n "{{model}}" ] && MODEL_FLAG="--model {{model}}"
            copilot $MODEL_FLAG --yolo -p "$FULL_PROMPT"
            ;;
        opencode)
            MODEL_FLAG=""
            [ -n "{{model}}" ] && MODEL_FLAG="--model {{model}}"
            opencode run $MODEL_FLAG "$FULL_PROMPT" --dangerously-skip-permissions
            ;;
        *)
            echo "Error: Unknown agent adapter: {{agent}}"
            exit 1
            ;;
    esac
    echo "--- TEST COMPLETE ---"

[no-cd]
escalate prompt:
    #!/usr/bin/env bash
    set -euo pipefail
    command -v copilot >/dev/null 2>&1 || { echo "ERROR: copilot is not installed or not on PATH." >&2; exit 1; }
    COPILOT_BIN="$(command -v copilot)"
    PROMPT_TEXT="You are a Senior Creator Agent. A junior agent needs a skill upgrade: '{{prompt}}'.
    1. Examine the current Justfile.
    2. Use 'add-tool' to implement the missing capability.
    3. Ensure the new tool is robust and follows the project's RADICALLY SIMPLE principle.
    4. Verify the new tool appears in 'just schema'."
    RUNNER=$(mktemp "${TMPDIR%/}/just-for-agents-escalate.XXXXXX")
    trap 'rm -f "$RUNNER"' EXIT
    WORKDIR_Q=$(printf '%q' "$PWD")
    PROMPT_Q=$(printf '%q' "$PROMPT_TEXT")
    COPILOT_Q=$(printf '%q' "$COPILOT_BIN")
    printf '%s\n' \
        '#!/usr/bin/env bash' \
        'set -euo pipefail' \
        "cd $WORKDIR_Q" \
        "$COPILOT_Q -p $PROMPT_Q --yolo" > "$RUNNER"
    chmod +x "$RUNNER"
    bash ./.just-for-agents/visible-agent.sh escalate "{{prompt}}" "Senior Creator Agent (copilot)" "$RUNNER"
