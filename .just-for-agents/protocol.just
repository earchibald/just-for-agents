[no-cd]
@schema:
    just --justfile ./.just-for-agents/protocol.just _bridge

[no-cd]
@bootstrap:
    echo "AGENT INSTRUCTIONS:"
    echo "1. This project uses 'just-for-agents'. Run 'just' to discover the API."
    echo "2. Use 'managed-new', 'managed-edit', and 'managed-delete' for governed recipe changes; reserve 'add-tool' for protected protocol maintenance."
    echo "3. Always prefix agent-facing documentation with '@tag' inside [doc('')]."
    echo "4. Agents supporting LSPs should run 'just install-lsp' and use 'just-lsp' for Justfile navigation and refactors."
    echo "5. Update CHANGELOG.md before stopping if you changed the repository."
    echo "6. You are now authorized to manage this Justfile as your primary toolset."

[no-cd]
@version:
    cat VERSION

[no-cd]
add-tool name command desc='' params='':
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

[no-cd]
remove-tool name:
    #!/usr/bin/env bash
    RESTRICTED="schema bootstrap add-tool remove-tool install-lsp test-agent _deskilling _bridge"
    if echo "$RESTRICTED" | grep -qw "{{name}}"; then
        echo "ERROR: '{{name}}' is a protected protocol recipe and cannot be deleted."
        exit 1
    fi
    just --justfile ./.just-for-agents/protocol.just _deskilling {{name}}

[no-cd]
install-lsp:
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

[private]
@_deskilling name:
    python3 ./deskill.py "{{name}}"

[private]
@_bridge:
    python3 ./bridge.py
