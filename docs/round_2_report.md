# Testing Report: Round 2

## Overview
Round 2 testing utilized the dogfooded `test-agent` infrastructure to evaluate advanced agent capabilities: multi-step workflows, environment isolation, error handling, and self-meta-extension.

## Methodology
Tests were executed autonomously by `gemini` agents in sandboxed environments (`/tmp/just-test-<name>`) using the `--yolo` flag. The agents were bootstrapped via `GEMINI.md` and the `just bootstrap` protocol.

## Test Cases & Results

| Test Case | Description | Result | Notes |
| :--- | :--- | :--- | :--- |
| **pipeline-test** | Chain `fetch`, `process`, and `report` tools. | **Pass** | Agent correctly managed intermediate file state (`data.csv`, `out.txt`). |
| **env-test** | Create and read a `.env` file via recipes. | **Pass** | Agent successfully isolated environment variables within `just` recipes. |
| **error-test** | Catch recipe failure and run a diagnosis tool. | **Pass** | Agent demonstrated the ability to respond to non-zero exit codes. |
| **meta-test** | Create a tool that itself uses `add-tool`. | **Pass** | Proven "Deep Self-Skilling". Revealed a minor string-matching bug in `_bridge` (fixed). |
| **lsp-test** | Discover and install `just-lsp` from manifest. | **Pass** | Agent successfully interpreted rules of engagement and used `install-lsp`. |

## Key Findings & Improvements
- **Automatic Trust**: Subagents were hitting an interactive "Trust this folder?" prompt. The `test-agent` recipe was updated to run `gemini --trust .` before the main command.
- **Exact Matching in Bridge**: The `_bridge` logic was improved from `startswith()` to exact list matching for protocol recipes, preventing unintended hiding of tools that share a prefix with internal recipes.
- **Robust Tool Creation**: Reconfirmed that sequential `echo` commands in `add-tool` are superior to `printf` for automated code generation.

## Next Steps
Prepare for Round 3, focusing on "API Stability" and "Concurrent Self-Skilling" (multiple agents or tasks competing for `Justfile` access).
