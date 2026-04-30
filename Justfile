[doc('@desc Generate a JSON tool schema from the Justfile
@usage Use this to get a machine-readable map of available tools.
@returns json')]
@schema:
    just _bridge

[doc('@desc Bootstrap an agent into this workspace
@usage Run this when an agent first enters the project.')]
@bootstrap:
    echo "AGENT INSTRUCTIONS:"
    echo "1. This project uses 'just-for-agents'. Run 'just' to discover the API."
    echo "2. Use 'add-tool' to persist new capabilities."
    echo "3. Always prefix agent-facing documentation with '@tag' inside [doc('')]."
    echo "4. Agents supporting LSPs should run 'just install-lsp' and use 'just-lsp'."
    echo "5. Update CHANGELOG.md before stopping if you changed the repository."
    echo "6. You are now authorized to manage this Justfile as your primary toolset."

[doc('@desc Print the current project version
@usage Run this to display the current just-for-agents version.')]
@version:
    cat VERSION

[doc("@desc Add a new tool to the Justfile
@param name The name of the new recipe
@param command The shell command to execute
@param desc a short description
@param params Optional parameters (e.g. arg1 arg2=val)
@usage Use this to expand the agent API surface.")]
@add-tool name command desc='' params='':
    #!/usr/bin/env bash
    RESTRICTED="schema bootstrap add-tool remove-tool install-lsp test-agent _deskilling _bridge"
    if echo "$RESTRICTED" | grep -qw "{{name}}"; then
        echo "ERROR: '{{name}}' is a protected protocol recipe and cannot be modified."
        exit 1
    fi
    echo "" >> Justfile
    echo "[doc('@desc {{desc}}')]" >> Justfile
    echo "{{name}} {{params}}:" >> Justfile
    echo "    {{command}}" >> Justfile

[doc('@desc Remove a tool from the Justfile
@param name The name of the recipe to remove
@usage Use this to clean up unused or deprecated tools.')]
@remove-tool name:
    #!/usr/bin/env bash
    RESTRICTED="schema bootstrap add-tool remove-tool install-lsp test-agent _deskilling _bridge"
    if echo "$RESTRICTED" | grep -qw "{{name}}"; then
        echo "ERROR: '{{name}}' is a protected protocol recipe and cannot be deleted."
        exit 1
    fi
    just _deskilling {{name}}

[doc('@desc Install just-lsp for language server support
@usage Agents should run this to enable advanced Justfile analysis. MacOS is preferred; Linux requires documentation review.')]
@install-lsp:
    #!/usr/bin/env bash
    OS=$(uname)
    if [ "$OS" = "Darwin" ]; then
        if command -v brew >/dev/null; then
            echo "Installing just-lsp via Homebrew..."
            brew install terror/tap/just-lsp
        elif command -v cargo >/dev/null; then
            echo "Brew not found. Installing via Cargo..."
            cargo install just-lsp
        else
            echo "Error: Neither brew nor cargo found."
            exit 1
        fi
    elif [ "$OS" = "Linux" ]; then
        echo "CAUTION: just-lsp does not support all Linux distributions."
        echo "Please review https://github.com/terror/just-lsp before proceeding."
        if [ -f /etc/arch-release ] && command -v pacman >/dev/null; then
            echo "Arch Linux detected. Installing via pacman..."
            sudo pacman -S just-lsp
        elif command -v cargo >/dev/null; then
            echo "Installing via Cargo..."
            cargo install just-lsp
        else
            echo "Error: No supported package manager found for Linux."
            exit 1
        fi
    else
        echo "Error: Unsupported Operating System: $OS"
        exit 1
    fi

[doc("@desc Run an autonomous agent test in a sandbox
@param name The name of the test scenario
@param prompt The instruction to give the agent
@param agent The agent CLI to use (gemini, copilot, opencode)
@param model Optional model string (e.g. 'ollama/qwen3.6:latest' for opencode)
@usage just test-agent name='qwen-test' prompt='Say hello' agent='opencode' model='ollama/qwen3.6:latest'")]
@test-agent name prompt agent='gemini' model='':
    #!/usr/bin/env bash
    echo "--- SANDBOX SETUP ---"
    SANDBOX="/tmp/just-test-{{name}}"
    echo "Target: $SANDBOX"
    rm -rf "$SANDBOX"
    mkdir -p "$SANDBOX"
    cp Justfile "$SANDBOX/"
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

[private]
_visible-agent session_suffix window_hint label runner:
    #!/usr/bin/env bash
    set -euo pipefail
    SESSION="just-for-agents-{{session_suffix}}"
    WINDOW_BASE=$(python3 -c 'import re, sys; text = sys.argv[1]; slug = re.sub(r"[^a-z0-9]+", "-", text.lower()).strip("-"); print((slug or "task")[:24])' "{{window_hint}}")
    WINDOW_NAME="${WINDOW_BASE}-$(date +%H%M)"
    RUNNER="{{runner}}"
    LABEL="{{label}}"
    [ -x "$RUNNER" ] || { echo "ERROR: runner is not executable: $RUNNER" >&2; exit 1; }
    if command -v tmux >/dev/null 2>&1; then
        RUN_ROOT="${TMPDIR:-/tmp}/just-for-agents"
        RUN_ID="$(date +%Y%m%d-%H%M%S)"
        LOG_FILE="$RUN_ROOT/{{session_suffix}}-$RUN_ID.log"
        STATUS_FILE="$RUN_ROOT/{{session_suffix}}-$RUN_ID.status"
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

[doc('@desc Request a skill upgrade from a Senior Agent
@param prompt The description of the missing capability or tool needed
@usage Use this when you identify a task that cannot be completed with existing tools.')]
@escalate prompt:
    #!/usr/bin/env bash
    set -euo pipefail
    command -v copilot >/dev/null 2>&1 || { echo "ERROR: copilot is not installed or not on PATH." >&2; exit 1; }
    COPILOT_BIN="$(command -v copilot)"
    PROMPT_TEXT="You are a Senior Creator Agent. A junior agent needs a skill upgrade: '{{prompt}}'.
    1. Examine the current Justfile.
    2. Use 'add-tool' to implement the missing capability.
    3. Ensure the new tool is robust and follows the project's RADICALLY SIMPLE principle.
    4. Verify the new tool appears in 'just schema'."
    RUNNER=$(mktemp "${TMPDIR:-/tmp}/just-for-agents-escalate.XXXXXX.sh")
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
    just --quiet _visible-agent escalate "{{prompt}}" "Senior Creator Agent (copilot)" "$RUNNER"

# Private de-skilling logic (Inlined Python)
_deskilling name:
    #!/usr/bin/env python3
    import os, re
    target = "{{name}}"
    with open('Justfile', 'r') as f:
        lines = f.readlines()
    
    new_lines = []
    skip = False
    for i, line in enumerate(lines):
        # Match [doc( and ensure the next line starts with the target recipe name
        if "[doc(" in line and i + 1 < len(lines) and re.match(rf"^{target}(\s|:)", lines[i+1].strip()):
            skip = True
            continue
        if skip:
            # If we are in skip mode, continue skipping until we hit a non-indented line that isn't the target
            if re.match(rf"^{target}(\s|:)", line.strip()):
                continue
            if line.startswith('    '):
                continue
            skip = False
        new_lines.append(line)
        
    with open('Justfile', 'w') as f:
        f.writelines(new_lines)

# Private bridge logic (Inlined Python)
_bridge:
    #!/usr/bin/env python3
    import sys, json, re, subprocess
    from pathlib import Path

    VERSION = Path("VERSION").read_text().strip() if Path("VERSION").exists() else None

    MANIFEST = {
        "project": "just-for-agents",
        "version": VERSION,
        "principle": "RADICALLY SIMPLE",
        "rules_of_engagement": [
            "MANDATORY: Use ONLY 'just' recipes for all system interactions.",
            "Use '@recipe:' or prefix individual lines with '@' to suppress command echoing, but do not combine both in the same recipe.",
            "Use curly-brace syntax for argument substitution.",
            "Documentation lives in [doc('@desc ...')] attributes.",
            "Agents can extend the API using the 'add-tool' recipe.",
            "Linux users: review https://github.com/terror/just-lsp before using install-lsp."
        ]
    }

    def parse():
        output = subprocess.check_output(["just", "--list", "--unsorted"]).decode()
        recipes = []
        current_docs = {}
        param_docs = {}
        
        def add_doc(tag, content):
            if tag == "param":
                match = re.match(r"(\w+)(?:=(['\"].*?['\"]|\S+))?\s+(.*)", content)
                if match:
                    p_name, p_default, p_desc = match.groups()
                    param_docs[p_name] = {"desc": p_desc}
                    if p_default: param_docs[p_name]["default"] = p_default.strip("'\"")
            elif tag == "usage":
                if tag not in current_docs: current_docs[tag] = []
                current_docs[tag].append(content)
            else:
                current_docs[tag] = content

        for line in output.splitlines():
            line = line.strip()
            if line.startswith("# @"):
                match = re.match(r"# @(\w+)\s+(.*)", line)
                if match: add_doc(match.group(1), match.group(2))
                continue
            if line and not line.startswith("Available recipes"):
                parts = line.split()
                if not parts: continue
                recipe_name = parts[0]
                if recipe_name in ["schema", "_bridge", "_deskilling", "bootstrap", "test-agent", "install-lsp"]:
                    current_docs = {}; param_docs = {}
                    continue
                if "#" in line:
                    recipe_part, comment_part = line.split("#", 1)
                    match = re.search(r"@(\w+)\s+(.*)", comment_part)
                    if match: add_doc(match.group(1), match.group(2))
                    elif "desc" not in current_docs: current_docs["desc"] = comment_part.strip()
                    recipe_part = recipe_part.strip()
                else: recipe_part = line.strip()
                if not recipe_part: continue
                parts = recipe_part.split()
                name = parts[0]
                params = []
                for p in parts[1:]:
                    param_info = {"name": p, "required": True}
                    if p.startswith("*"): param_info["name"] = p[1:]; param_info["variadic"] = True
                    if "=" in p:
                        p_name, default = p.split("=", 1)
                        param_info["name"] = p_name
                        param_info["default"] = default.strip("'\"")
                        param_info["required"] = False
                    if param_info["name"] in param_docs:
                        doc = param_docs[param_info["name"]]
                        param_info["description"] = doc["desc"]
                        if "default" in doc and "default" not in param_info:
                            param_info["default"] = doc["default"]; param_info["required"] = False
                    params.append(param_info)
                recipes.append({"name": name, "parameters": params, "docs": current_docs})
                current_docs = {}; param_docs = {}
        return {"manifest": MANIFEST, "tools": recipes}

    print(json.dumps(parse(), indent=2))

[doc("@desc Add an Ollama model to the opencode configuration
@param model The name of the model in ollama (e.g. qwen3.6:latest)
@param display_name Optional display name for the model
@usage just opencode-add-ollama-model qwen3.6:latest 'Qwen 3.6'")]
opencode-add-ollama-model model display_name='':
    #!/usr/bin/env bash
    if ! ollama list | grep -qw "{{model}}"; then
        echo "ERROR: Model '{{model}}' not found in ollama. Please run 'ollama pull {{model}}' first."
        exit 1
    fi
    CONFIG="$HOME/.config/opencode/opencode.json"
    [ ! -f "$CONFIG" ] && { echo "Error: opencode config not found at $CONFIG"; exit 1; }
    DNAME="{{display_name}}"
    [ -z "$DNAME" ] && DNAME="{{model}}"
    jq --arg m "{{model}}" --arg n "$DNAME" '.provider.ollama.models += {($m): {"name": $n}}' "$CONFIG" > "$CONFIG.tmp" && mv "$CONFIG.tmp" "$CONFIG"
    echo "SUCCESS: Added {{model}} to opencode configuration."
    opencode models ollama

[doc("@desc Configure opencode to use Exa's unauthenticated remote MCP endpoint
@usage just opencode-enable-exa-mcp")]
opencode-enable-exa-mcp:
    #!/usr/bin/env bash
    command -v jq >/dev/null 2>&1 || { echo "ERROR: jq is required." >&2; exit 1; }
    CONFIG_DIR="$HOME/.config/opencode"
    CONFIG="$CONFIG_DIR/opencode.json"
    mkdir -p "$CONFIG_DIR"
    [ -f "$CONFIG" ] || printf '{}\n' > "$CONFIG"
    jq '.mcp = (.mcp // {}) | .mcp.exa = {"type": "remote", "url": "https://mcp.exa.ai/mcp", "enabled": true}' "$CONFIG" > "$CONFIG.tmp" && mv "$CONFIG.tmp" "$CONFIG"
    echo "SUCCESS: Configured opencode to use Exa MCP without an API key."
    jq '.mcp.exa' "$CONFIG"

[doc("@desc Find files >1MB in a directory and create a timestamped zip archive.
@param dir The directory to search (defaults to '.')
@usage just archive-large dir='downloads'")]
archive-large dir='.':
    #!/usr/bin/env bash
    command -v zip >/dev/null 2>&1 || { echo >&2 "ERROR: zip is not installed."; exit 1; }
    FILES=$(find "{{dir}}" -maxdepth 1 -type f -size +1M)
    if [ -z "$FILES" ]; then echo "No files larger than 1MB found."; exit 0; fi
    zip "archive_$(date +%Y%m%d_%H%M%S).zip" $FILES



[doc("@desc Calculate the MD5 hash of a file (cross-platform)
@param file The path to the file to hash
@usage just md5 path/to/file.txt")]
@md5 file:
    #!/usr/bin/env bash
    if command -v md5sum >/dev/null 2>&1; then
        md5sum "{{file}}"
    elif command -v md5 >/dev/null 2>&1; then
        md5 "{{file}}"
    else
        echo "ERROR: No md5 tool found." >&2
        exit 1
    fi

[no-cd]
[doc("@desc Dispatch a research agent for autonomous multi-round research
@param subject_title The title of the research subject
@param rounds Number of new research rounds to run in this invocation (default 3)
@param source Initial source or context
@param subject_id Optional slug for the research directory
@param model Optional provider/model string or Ollama model name. Leave empty to auto-detect a usable local model.
@usage just research subject_title='Edge caching strategies' rounds='10'
@usage just research subject_title='Edge caching strategies' rounds='10' model='qwen3.6:latest'")]
research subject_title rounds='3' source='' subject_id='' model='':
    #!/usr/bin/env bash
    set -euo pipefail
    command -v opencode >/dev/null 2>&1 || { echo "ERROR: opencode is not installed or not on PATH." >&2; exit 1; }
    OPENCODE_BIN="$(command -v opencode)"
    just --quiet opencode-enable-exa-mcp >/dev/null
    SUBJECT_TITLE="{{subject_title}}"
    ROUNDS="{{rounds}}"
    SOURCE="{{source}}"
    SUB_ID="{{subject_id}}"
    REQUESTED_MODEL="{{model}}"
    case "$SUBJECT_TITLE" in subject_title=*) SUBJECT_TITLE="${SUBJECT_TITLE#subject_title=}" ;; esac
    case "$ROUNDS" in rounds=*) ROUNDS="${ROUNDS#rounds=}" ;; esac
    case "$SOURCE" in source=*) SOURCE="${SOURCE#source=}" ;; esac
    case "$SUB_ID" in subject_id=*) SUB_ID="${SUB_ID#subject_id=}" ;; esac
    case "$REQUESTED_MODEL" in model=*) REQUESTED_MODEL="${REQUESTED_MODEL#model=}" ;; esac
    case "$ROUNDS" in
        ''|*[!0-9]*)
            echo "ERROR: rounds must be a non-negative integer." >&2
            exit 1
            ;;
    esac
    if [ -z "$SUB_ID" ]; then
        SUB_ID=$(echo "$SUBJECT_TITLE" | tr '[:upper:]' '[:lower:]' | sed 's/[^a-z0-9]/-/g' | sed 's/--*/-/g' | sed 's/^-//;s/-$//')
    fi
    RDIR="docs/research/$SUB_ID"
    mkdir -p "$RDIR"
    BRIEF="$RDIR/brief.md"
    ROOT_CONTEXT=$(for path in README.md concept.md HANDOFF.md GEMINI.md Justfile; do [ -e "$path" ] && printf -- '- %s\n' "$path"; done)
    MISSING_CONTEXT=$(for path in AGENTS.md RTK.md; do [ ! -e "$path" ] && printf -- '- %s\n' "$path"; done)
    EXISTING_ROUNDS=$(find "$RDIR" -maxdepth 1 -type f -name 'round_*.md' | sort)
    LAST_EXISTING_ROUND=$(printf '%s\n' "$EXISTING_ROUNDS" | sed -nE 's#^.*/round_([0-9]+)\.md$#\1#p' | sort -n | tail -1)
    [ -n "$LAST_EXISTING_ROUND" ] || LAST_EXISTING_ROUND=0
    TARGET_LAST_ROUND=$((LAST_EXISTING_ROUND + ROUNDS))
    {
        echo "# Research Brief: $SUBJECT_TITLE"
        echo
        echo "- Subject ID: $SUB_ID"
        echo "- Existing completed rounds: $LAST_EXISTING_ROUND"
        echo "- Requested new rounds this invocation: $ROUNDS"
        echo "- Target last round after this invocation: $TARGET_LAST_ROUND"
        if [ -n "$SOURCE" ]; then
            if [ -f "$SOURCE" ]; then
                echo "- Provided source file: $SOURCE"
            else
                echo "- Provided source text: inline"
            fi
        else
            echo "- Provided source: none"
        fi
        echo
        echo "## Existing rounds"
        if [ -n "$EXISTING_ROUNDS" ]; then
            printf '%s\n' "$EXISTING_ROUNDS" | sed 's#^#- #'
        else
            echo "- none"
        fi
        echo
        echo "## Suggested local repo context"
        if [ -n "$ROOT_CONTEXT" ]; then
            printf '%s\n' "$ROOT_CONTEXT"
        else
            echo "- none"
        fi
        echo
        echo "## Missing common files"
        if [ -n "$MISSING_CONTEXT" ]; then
            printf '%s\n' "$MISSING_CONTEXT"
        else
            echo "- none"
        fi
        echo
        echo "## Research constraints"
        echo "- Use only files that actually exist."
        echo "- Do not assume AGENTS.md or RTK.md exist."
        echo "- External web/search tools are optional; if they fail, continue with local analysis and note the limitation."
        echo
        echo "## Provided source"
        if [ -n "$SOURCE" ]; then
            if [ -f "$SOURCE" ]; then
                cat "$SOURCE"
            else
                printf '%s\n' "$SOURCE"
            fi
        else
            echo "No source was provided."
        fi
    } > "$BRIEF"
    if [ -n "$REQUESTED_MODEL" ]; then
        MODEL=$(just --quiet research-model "$REQUESTED_MODEL")
    else
        MODEL=$(just --quiet research-model)
    fi
    echo "Using model: $MODEL"
    r=$((LAST_EXISTING_ROUND + 1))
    while [ "$r" -le "$TARGET_LAST_ROUND" ]; do
        RFILE="$RDIR/round_$r.md"
        echo "Starting Research Round $r for $SUBJECT_TITLE..."
        PREV_ROUND="none"
        if [ "$r" -gt 1 ] && [ -f "$RDIR/round_$((r-1)).md" ]; then
            PREV_ROUND="$RDIR/round_$((r-1)).md"
        fi
        INVOCATION_ROUND=$((r - LAST_EXISTING_ROUND))
        printf -v PROMPT '%s\n' \
            "Research Subject: $SUBJECT_TITLE" \
            "Round: $r (invocation round $INVOCATION_ROUND of $ROUNDS)" \
            "Brief file: $BRIEF" \
            "Previous round file: $PREV_ROUND" \
            "" \
            "Task:" \
            "- Operate fully autonomously in this non-interactive batch run." \
            "- Do not ask clarifying questions, request confirmation, or pause to describe your plan." \
            "- If context is incomplete or ambiguous, make the best reasonable assumption, note it in the report, and continue." \
            "- Read the brief file and any existing research round files that are relevant." \
            "- Prefer `just --list`, `just schema`, targeted searches, and partial file reads over reading very large files end-to-end." \
            "- If a file read is truncated, incomplete, or too large, recover by re-reading only the relevant sections instead of abandoning the round." \
            "- If repository context degrades, continue with the best evidence you have and record the limitation; do not switch into a conversational 'what would you like me to do next?' mode." \
            "- Produce a comprehensive Markdown report for this round." \
            "- Use local repository context first. External web/search tools are optional. If network, search, or fetch tools fail due to auth, payment, timeout, 404, or transport errors, continue with local analysis and record those limitations instead of aborting the round." \
            "- Do not assume AGENTS.md or RTK.md exist." \
            "- Return only the final Markdown report with no preamble, progress updates, or side commentary, then finish with a final line exactly in this format:" \
            "SUMMARY: <one-sentence summary of findings>" \
            "" \
            "Suggested sections:" \
            "1. Overview" \
            "2. Findings" \
            "3. Recommendations" \
            "4. Limitations" \
            "5. Next questions for another round"
        set +e
        RUNNER=$(mktemp "${TMPDIR:-/tmp}/just-for-agents-research.XXXXXX.sh")
        WORKDIR_Q=$(printf '%q' "$PWD")
        MODEL_Q=$(printf '%q' "$MODEL")
        PROMPT_Q=$(printf '%q' "$PROMPT")
        OPENCODE_Q=$(printf '%q' "$OPENCODE_BIN")
        printf '%s\n' \
            '#!/usr/bin/env bash' \
            'set -euo pipefail' \
            "cd $WORKDIR_Q" \
            "$OPENCODE_Q run -m $MODEL_Q $PROMPT_Q --dangerously-skip-permissions" > "$RUNNER"
        chmod +x "$RUNNER"
        RESULT=$(just --quiet _visible-agent research "$SUBJECT_TITLE round $r" "Research Agent (opencode)" "$RUNNER")
        STATUS=$?
        set -e
        rm -f "$RUNNER"
        if [ "$STATUS" -ne 0 ]; then
            printf -v RESULT '%s\n' \
                "# Research Round $r: $SUBJECT_TITLE" \
                "" \
                "## Status" \
                "" \
                "The research agent exited with status $STATUS." \
                "" \
                "## Captured Output" \
                "" \
                "\`\`\`" \
                "$RESULT" \
                "\`\`\`" \
                "" \
                "SUMMARY: Research round failed with exit status $STATUS."
        else
            case "$RESULT" in
                *"SUMMARY:"*) ;;
                *)
                    printf -v RESULT '%s\n\n%s\n' "$RESULT" "SUMMARY: Research round complete."
                    ;;
            esac
        fi
        printf '%s\n' "$RESULT" > "$RFILE"
        SUMM=$(printf '%s\n' "$RESULT" | awk -F'SUMMARY: ' '/SUMMARY:/ {summary=$2} END {print summary}')
        [ -z "$SUMM" ] && SUMM="Research round complete."
        echo "Saved $RFILE"
        echo "Summary: $SUMM"
        r=$((r + 1))
    done
    just --quiet _research-index

[private]
_research-index:
    #!/usr/bin/env python3
    from pathlib import Path
    import re

    root = Path("docs/research")
    root.mkdir(parents=True, exist_ok=True)
    index = root / "index.md"
    lines = ["# Research Index", ""]

    for subject_dir in sorted(path for path in root.iterdir() if path.is_dir()):
        round_files = []
        for candidate in subject_dir.glob("round_*.md"):
            match = re.match(r"round_(\d+)\.md$", candidate.name)
            if match:
                round_files.append((int(match.group(1)), candidate))
        round_files.sort(key=lambda item: item[0])
        if not round_files:
            continue

        title = subject_dir.name.replace("-", " ")
        brief = subject_dir / "brief.md"
        if brief.exists():
            match = re.search(r"^# Research Brief: (.+)$", brief.read_text(), re.MULTILINE)
            if match:
                title = match.group(1).strip()

        lines.append(f"## {title} ({subject_dir.name})")
        for round_number, round_file in round_files:
            summary = "Research round complete."
            for line in round_file.read_text().splitlines():
                if line.startswith("SUMMARY:"):
                    summary = line.split("SUMMARY:", 1)[1].strip() or summary
            lines.append(f"- [Round {round_number}]({round_file.as_posix()}): {summary}")
        lines.append("")

    index.write_text("\n".join(lines).rstrip() + "\n")

[doc('@desc List all research subjects')]
list-research :
    #!/usr/bin/env bash
    find docs/research -mindepth 1 -maxdepth 1 -type d 2>/dev/null | while read -r dir; do
        if [ -f "$dir/brief.md" ] || find "$dir" -maxdepth 1 -type f -name 'round_*.md' | grep -q .; then
            basename "$dir"
        fi
    done

[doc("@desc Resolve a usable model for the research recipe
@param requested Optional provider/model string or Ollama model name
@usage just research-model
@usage just research-model requested='qwen3.6:latest'
@usage just research-model requested='openai/gpt-4.1'")]
research-model requested='':
    #!/usr/bin/env bash
    set -euo pipefail
    REQUESTED="{{requested}}"
    case "$REQUESTED" in
        requested=*|model=*)
            REQUESTED="${REQUESTED#*=}"
            ;;
    esac
    OLLAMA_MODELS=""
    OLLAMA_READY=0
    if command -v ollama >/dev/null 2>&1; then
        if OLLAMA_MODELS=$(ollama list 2>/dev/null | awk 'NR > 1 {print $1}'); then
            OLLAMA_READY=1
        fi
    fi

    has_ollama_model() {
        [ "$OLLAMA_READY" -eq 1 ] || return 1
        printf '%s\n' "$OLLAMA_MODELS" | grep -Fxq -- "$1"
    }

    if [ -n "$REQUESTED" ]; then
        if has_ollama_model "$REQUESTED"; then
            printf 'ollama/%s\n' "$REQUESTED"
            exit 0
        fi
        if [[ "$REQUESTED" == */* ]]; then
            printf '%s\n' "$REQUESTED"
            exit 0
        fi
        if [ "$OLLAMA_READY" -ne 1 ]; then
            echo "ERROR: Ollama is unavailable. Pass a full provider/model string such as model='openai/gpt-4.1'." >&2
            exit 1
        fi
        echo "ERROR: Ollama model '$REQUESTED' was not found. Use 'ollama list' to inspect local models or pass model='provider/name'." >&2
        exit 1
    fi

    if [ "$OLLAMA_READY" -ne 1 ]; then
        echo "ERROR: No model specified and Ollama is unavailable. Pass model='provider/name' or start Ollama." >&2
        exit 1
    fi

    for candidate in qwen3.6:latest qwen-3.6:latest just-consumer-qwen3.6:latest llama3.2:latest; do
        if has_ollama_model "$candidate"; then
            printf 'ollama/%s\n' "$candidate"
            exit 0
        fi
    done

    for candidate in $OLLAMA_MODELS; do
        case "$candidate" in
            *embed*|*embedding*)
                continue
                ;;
        esac
        printf 'ollama/%s\n' "$candidate"
        exit 0
    done

    echo "ERROR: No usable Ollama model found. Install a chat model or pass model='provider/name'." >&2
    exit 1
