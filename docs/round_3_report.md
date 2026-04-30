# Testing Report: Round 3

## Overview
Round 3 focused on "Lower-Intelligence" agents (Gemini Flash, Gemini Flash Lite, and Copilot Haiku) and introduced "Edge/Local" model testing via the `opencode` adapter with Gemma 4-31B.

## Methodology
Tests were executed in sandboxes using the `--yolo` flag. The `test-agent` recipe was upgraded to a unified bash script supporting `gemini`, `copilot`, and `opencode` adapters.

## Test Cases & Results

| Test Case | Agent / Model | Result | Notes |
| :--- | :--- | :--- | :--- |
| **flash-basic** | Gemini 2.5 Flash | **Pass** | Successfully created `list-all`. Headless `-p` mode verified. |
| **flash-params** | Gemini 2.5 Flash | **Pass** | Handled defaults and recovered from rate limits (429). |
| **lite-basic** | Gemini 2.0 Flash Lite | **Pass** | Verified text-only lightweight models follow the protocol. |
| **copilot-basic** | Claude Haiku 4.5 | **Pass** | Successfully added `check-os` using the `--yolo` flag. |
| **gemma-edge** | Gemma 4-31B (Opencode) | **Fail (Creator)**| Model struggled with precise file modification and nested quoting in the "Creator" role. |

## Key Findings & Pivot
- **The "Creator" Bar**: Successfully adding and removing tools requires high precision in quoting and syntax. Edge/Local models currently struggle with the "Self-Skilling" part of the loop.
- **The "Consumer" Vision**: While Edge models fail as **Creators**, they are excellent as **Consumers**. A local agent can use the `schema` to provide an NLP interface to existing tools.
- **Escalation Path**: We envision a workflow where a local "Consumer" agent executes known tools and escalates to a "Senior Architect" agent when a new capability (Creator role) is needed.
- **Guardrails**: Implementation of `RESTRICTED` recipe lists in `add-tool` and `remove-tool` now prevents agents from modifying the core protocol.

## Next Steps
- Formalize the "NLP Consumer" role for Edge models.
- Build an "Escalation" tool that allows an agent to request a "Skill Upgrade" from a more powerful model.
