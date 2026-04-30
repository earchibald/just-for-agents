#!/usr/bin/env bash
set -euo pipefail

SCRIPT_DIR="$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")" && pwd)"
EXAMPLE_DIR="$SCRIPT_DIR"
REPO_ROOT="$(cd -- "$EXAMPLE_DIR/../.." && pwd)"
PI_AGENT_DIR="$HOME/.pi/agent"
PROJECT_PI_DIR="$REPO_ROOT/.pi"
EXT_DIR="$PROJECT_PI_DIR/extensions"
MODELS_TARGET="$PI_AGENT_DIR/models.json"
MODELS_SOURCE="$EXAMPLE_DIR/models.json"
CONSUMER_MODEL_ID="just-consumer-qwen3.6:latest"
RESEARCH_MODEL_ID="just-research-qwen3.6:latest"

require_cmd() {
  command -v "$1" >/dev/null 2>&1 || {
    echo "ERROR: missing required command: $1" >&2
    exit 1
  }
}

require_cmd python3
require_cmd npm
require_cmd ollama

mkdir -p "$PI_AGENT_DIR" "$EXT_DIR"

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

echo "==> Installing project-local Pi consumer files"
cp "$EXAMPLE_DIR/settings.json" "$PROJECT_PI_DIR/settings.json"
cp "$EXAMPLE_DIR/just-consumer.ts" "$EXT_DIR/just-consumer.ts"
cp "$EXAMPLE_DIR/package.json" "$EXT_DIR/package.json"
cp "$EXAMPLE_DIR/profile.json" "$PROJECT_PI_DIR/consumer-profile.json"

echo "==> Installing extension dependencies"
npm install --prefix "$EXT_DIR"

echo
echo "Done. Start Pi in this repo with:"
echo "  pi"
