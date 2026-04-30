# Handoff: just-for-agents

## 🚀 Project Vision: RADICALLY SIMPLE
This project transforms a standard `Justfile` into a discoverable, self-skilling API for AI agents.
- **Output is the API**: Use `just` (schema) for discovery.
- **Documentation is Data**: Use `[doc('')]` for tool metadata.
- **Single-File Core**: The entire framework (parser, protocol, tools) is encapsulated in the `Justfile`.

## 🛠 Current State
- **Core Implementation**: The `Justfile` contains an inlined Python bridge (`_bridge`) that parses `just --list` output into a machine-readable JSON schema.
- **Self-Skilling Loop**:
    - `add-tool`: Allows agents to append new recipes to the Justfile.
    - `remove-tool`: Allows agents to surgically delete recipes using an inlined Python script (`_deskilling`).
- **Guardrails**: Core protocol recipes (`schema`, `bootstrap`, `add-tool`, etc.) are protected from modification or deletion via strict `RESTRICTED` checks.
- **Testing Infrastructure**: A dogfooded `test-agent` recipe allows running autonomous tests in isolated sandboxes using `gemini`, `copilot`, or `opencode`.

## 📊 Testing History
Detailed reports are available in the `docs/` directory:
- **Round 1**: Validated the core loop and fixed the `sed`-based removal logic.
- **Round 2**: Proven multi-recipe workflows, environment isolation, and meta-extension.
- **Round 3**: Validated "Lower-Intelligence" models (Flash, Haiku). Discovered that Edge/Local models (Gemma) excel as **Consumers** but struggle as **Creators**.

## 🎯 Immediate Next Steps: The Escalation Path
The project has pivoted to a **Consumer vs. Creator** model:
1. **The Consumer**: A local/edge agent that uses the `schema` to provide an NLP interface to existing tools.
2. **The Creator**: A senior architect agent (like Gemini Pro) that implements new capabilities.
3. **Task**: Build an **Escalation Tool** recipe that allows a Consumer agent to identify a missing capability and request a "Skill Upgrade" from a Senior agent.

## 📂 Key Files
- `Justfile`: The single source of truth and API surface.
- `GEMINI.md`: Core project mandates.
- `docs/`: Testing reports and strategy.
- `tests/`: Versioned test protocols.
