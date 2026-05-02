#!/usr/bin/env bash
set -euo pipefail

SCRIPT_DIR="$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")" && pwd)"
EXAMPLE_DIR="$SCRIPT_DIR"
REPO_ROOT="$(cd -- "$EXAMPLE_DIR/../.." && pwd)"
PI_AGENT_DIR="$HOME/.pi/agent"
MODELS_TARGET="$PI_AGENT_DIR/models.json"
MODELS_SOURCE="$EXAMPLE_DIR/models.json"
CONSUMER_MODEL_ID="just-consumer-qwen3.6:latest"
RESEARCH_MODEL_ID="just-research-qwen3.6:latest"

usage() {
  cat <<'EOF'
Usage: bash examples/pi-consumer/install.sh [--target <dir> | <dir>]

Build the local Pi consumer bundle from this just-for-agents checkout and reset
the selected target root to a fresh just-for-agents runtime install.

If no target is provided, the installer keeps the existing behavior and writes into
this checkout's root.
EOF
}

require_cmd() {
  command -v "$1" >/dev/null 2>&1 || {
    echo "ERROR: missing required command: $1" >&2
    exit 1
  }
}

resolve_target_root() {
  local target_input="$1"

  if [ -e "$target_input" ] && [ ! -d "$target_input" ]; then
    echo "ERROR: target exists but is not a directory: $target_input" >&2
    exit 1
  fi

  mkdir -p "$target_input"
  (
    cd -- "$target_input"
    pwd
  )
}

reset_target_jfa_state() {
  local target_root="$1"

  rm -rf \
    "$target_root/.pi" \
    "$target_root/.just-for-agents" \
    "$target_root/just_for_agents" \
    "$target_root/Justfile" \
    "$target_root/VERSION" \
    "$target_root/README.md" \
    "$target_root/CHANGELOG.md"
}

install_runtime_bundle() {
  local target_root="$1"

  cp "$REPO_ROOT/Justfile" "$target_root/Justfile"
  cp "$REPO_ROOT/VERSION" "$target_root/VERSION"
  cp "$REPO_ROOT/README.md" "$target_root/README.md"
  cp "$REPO_ROOT/CHANGELOG.md" "$target_root/CHANGELOG.md"
  cp -R "$REPO_ROOT/.just-for-agents" "$target_root/.just-for-agents"
  cp -R "$REPO_ROOT/just_for_agents" "$target_root/just_for_agents"
}

TARGET_ROOT="$REPO_ROOT"
if [ "$#" -gt 0 ]; then
  case "$1" in
    -h|--help)
      usage
      exit 0
      ;;
    --target)
      if [ "$#" -ne 2 ]; then
        echo "ERROR: --target expects exactly one directory argument" >&2
        usage >&2
        exit 1
      fi
      TARGET_ROOT="$(resolve_target_root "$2")"
      ;;
    *)
      if [ "$#" -ne 1 ]; then
        echo "ERROR: expected zero arguments, a single target directory, or --target <dir>" >&2
        usage >&2
        exit 1
      fi
      TARGET_ROOT="$(resolve_target_root "$1")"
      ;;
  esac
fi

PROJECT_PI_DIR="$TARGET_ROOT/.pi"
EXT_DIR="$PROJECT_PI_DIR/extensions"

require_cmd python3
require_cmd npm
require_cmd ollama

echo "==> Resetting just-for-agents state in $TARGET_ROOT"
reset_target_jfa_state "$TARGET_ROOT"
mkdir -p "$PI_AGENT_DIR" "$EXT_DIR"

echo "==> Installing just-for-agents runtime bundle into $TARGET_ROOT"
install_runtime_bundle "$TARGET_ROOT"

echo "==> Building Ollama model: $CONSUMER_MODEL_ID"
ollama create "$CONSUMER_MODEL_ID" -f "$EXAMPLE_DIR/Modelfile"

if [ -f "$EXAMPLE_DIR/ResearchModelfile" ]; then
  echo "==> Building Ollama model: $RESEARCH_MODEL_ID"
  ollama create "$RESEARCH_MODEL_ID" -f "$EXAMPLE_DIR/ResearchModelfile"
fi

if [ -f "$MODELS_TARGET" ]; then
  cp "$MODELS_TARGET" "$MODELS_TARGET.bak"
  echo "==> Backed up existing Pi model config to $MODELS_TARGET.bak"
fi

echo "==> Merging Pi model config"
python3 - "$MODELS_SOURCE" "$MODELS_TARGET" <<'PY'
import json
import os
import sys

source_path, target_path = sys.argv[1:3]
with open(source_path, "r", encoding="utf-8") as f:
    source = json.load(f)

if os.path.exists(target_path):
    with open(target_path, "r", encoding="utf-8") as f:
        target = json.load(f)
else:
    target = {}

source_ollama = source.setdefault("providers", {}).get("ollama", {})
providers = target.setdefault("providers", {})
ollama = providers.setdefault("ollama", {})

for key in ("baseUrl", "api", "apiKey", "compat"):
    if key not in ollama and key in source_ollama:
        ollama[key] = source_ollama[key]

existing_models = {}
for model in ollama.get("models", []):
    if isinstance(model, dict) and "id" in model:
        existing_models[model["id"]] = model

for model in source_ollama.get("models", []):
    if isinstance(model, dict) and "id" in model:
        existing_models[model["id"]] = {**existing_models.get(model["id"], {}), **model}

ollama["models"] = list(existing_models.values())

with open(target_path, "w", encoding="utf-8") as f:
    json.dump(target, f, indent=2)
    f.write("\n")
PY

echo "==> Installing project-local Pi consumer files into $TARGET_ROOT"
cp "$EXAMPLE_DIR/settings.json" "$PROJECT_PI_DIR/settings.json"
cp "$EXAMPLE_DIR/just-consumer.ts" "$EXT_DIR/just-consumer.ts"
cp "$EXAMPLE_DIR/package.json" "$EXT_DIR/package.json"
cp "$EXAMPLE_DIR/profile.json" "$PROJECT_PI_DIR/consumer-profile.json"

echo "==> Installing extension dependencies"
npm install --prefix "$EXT_DIR"

echo
echo "Done. Start Pi in the target workspace with:"
echo "  cd \"$TARGET_ROOT\" && pi"
