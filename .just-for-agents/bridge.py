#!/usr/bin/env python3
import json
import re
import subprocess
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
VERSION_FILE = ROOT / "VERSION"

MANIFEST = {
    "project": "just-for-agents",
    "version": VERSION_FILE.read_text().strip() if VERSION_FILE.exists() else None,
    "principle": "RADICALLY SIMPLE",
    "rules_of_engagement": [
        "MANDATORY: Use ONLY 'just' recipes for all system interactions.",
        "Use '@recipe:' or prefix individual lines with '@' to suppress command echoing, but do not combine both in the same recipe.",
        "Use curly-brace syntax for argument substitution.",
        "Documentation lives in [doc('@desc ...')] attributes.",
        "Agents stage managed recipe changes with 'managed-new', 'managed-edit', and 'managed-delete'; reserve 'add-tool' for protected protocol maintenance.",
        "Linux users: review https://github.com/terror/just-lsp before using install-lsp.",
    ],
}


def parse():
    output = subprocess.check_output(["just", "--list", "--unsorted"], cwd=ROOT).decode()
    recipes = []
    current_docs = {}
    param_docs = {}

    def add_doc(tag, content):
        if tag == "param":
            match = re.match(r"(\w+)(?:=(['\"].*?['\"]|\S+))?\s+(.*)", content)
            if match:
                p_name, p_default, p_desc = match.groups()
                param_docs[p_name] = {"desc": p_desc}
                if p_default:
                    param_docs[p_name]["default"] = p_default.strip("'\"")
        elif tag == "usage":
            current_docs.setdefault(tag, []).append(content)
        else:
            current_docs[tag] = content

    for line in output.splitlines():
        line = line.strip()
        if line.startswith("# @"):
            match = re.match(r"# @(\w+)\s+(.*)", line)
            if match:
                add_doc(match.group(1), match.group(2))
            continue
        if not line or line.startswith("Available recipes"):
            continue
        parts = line.split()
        if not parts:
            continue
        recipe_name = parts[0]
        if recipe_name in ["schema", "_bridge", "_deskilling", "bootstrap", "test-agent", "install-lsp"]:
            current_docs = {}
            param_docs = {}
            continue
        if "#" in line:
            recipe_part, comment_part = line.split("#", 1)
            match = re.search(r"@(\w+)\s+(.*)", comment_part)
            if match:
                add_doc(match.group(1), match.group(2))
            elif "desc" not in current_docs:
                current_docs["desc"] = comment_part.strip()
            recipe_part = recipe_part.strip()
        else:
            recipe_part = line.strip()
        if not recipe_part:
            continue
        parts = recipe_part.split()
        name = parts[0]
        params = []
        for parameter in parts[1:]:
            param_info = {"name": parameter, "required": True}
            if parameter.startswith("*"):
                param_info["name"] = parameter[1:]
                param_info["variadic"] = True
            if "=" in parameter:
                p_name, default = parameter.split("=", 1)
                param_info["name"] = p_name
                param_info["default"] = default.strip("'\"")
                param_info["required"] = False
            if param_info["name"] in param_docs:
                doc = param_docs[param_info["name"]]
                param_info["description"] = doc["desc"]
                if "default" in doc and "default" not in param_info:
                    param_info["default"] = doc["default"]
                    param_info["required"] = False
            params.append(param_info)
        recipes.append({"name": name, "parameters": params, "docs": current_docs})
        current_docs = {}
        param_docs = {}
    return {"manifest": MANIFEST, "tools": recipes}


print(json.dumps(parse(), indent=2))
