[doc('@desc Generate a JSON tool schema from the Justfile
@usage Use this to get a machine-readable map of available tools.
@returns json')]
@schema:
    @just _bridge

[doc('@desc Bootstrap an agent into this workspace
@usage Run this when an agent first enters the project.')]
@bootstrap:
    @echo "AGENT INSTRUCTIONS:"
    @echo "1. This project uses 'just-for-agents'. Run 'just' to discover the API."
    @echo "2. Use 'add-tool' to persist new capabilities."
    @echo "3. Always prefix agent-facing documentation with '@tag' inside [doc('')]."
    @echo "4. Agents supporting LSPs should run 'just install-lsp' and use 'just-lsp'."
    @echo "5. You are now authorized to manage this Justfile as your primary toolset."

[doc("@desc Add a new tool to the Justfile
@param name The name of the new recipe
@param command The shell command to execute
@param desc A short description
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

[doc('@desc Request a skill upgrade from a Senior Agent
@param prompt The description of the missing capability or tool needed
@usage Use this when you identify a task that cannot be completed with existing tools.')]
@escalate prompt:
    #!/usr/bin/env bash
    echo "Escalating to Senior Agent (gemini)..."
    gemini -p "You are a Senior Creator Agent. A junior agent needs a skill upgrade: '{{prompt}}'. 
    1. Examine the current Justfile.
    2. Use 'add-tool' to implement the missing capability. 
    3. Ensure the new tool is robust and follows the project's RADICALLY SIMPLE principle.
    4. Verify the new tool appears in 'just schema'." --yolo

# Private de-skilling logic (Inlined Python)
_deskilling name:
    #!/usr/bin/env python3
    import os
    target = "{{name}}"
    with open('Justfile', 'r') as f:
        lines = f.readlines()
    
    new_lines = []
    skip = False
    for i, line in enumerate(lines):
        if "[doc(" in line and i + 1 < len(lines) and target + ":" in lines[i+1].split():
            skip = True
            continue
        if skip:
            if target + ":" in line.split():
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

    MANIFEST = {
        "project": "just-for-agents",
        "principle": "RADICALLY SIMPLE",
        "rules_of_engagement": [
            "MANDATORY: Use ONLY 'just' recipes for all system interactions.",
            "Prefix recipes or lines with '@' to suppress command echoing.",
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
md5 file:
    #!/usr/bin/env bash
    if command -v md5sum >/dev/null 2>&1; then
        md5sum "{{file}}"
    elif command -v md5 >/dev/null 2>&1; then
        md5 -r "{{file}}"
    else
        echo "ERROR: No md5 tool found." >&2
        exit 1
    fi
