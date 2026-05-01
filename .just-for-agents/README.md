# just-for-agents helper layer

This directory contains the modularized implementation layer for the root `Justfile`.

- The root `Justfile` remains the stable public entrypoint and discovery surface.
- High-value helper implementations and recipe partitions live here so the core Justfile stays smaller and easier for agents to reason about.
- Extracted helpers:
  - `bridge.py`
  - `deskill.py`
  - `research-index.py`
  - `visible-agent.sh`
- Recipe partitions:
  - `protocol.just`
  - `agent.just`
  - `research.just`
  - `utility.just`
  - `managed.just` (managed-overlay bootstrap/queue/inspect; backed by the top-level `just_for_agents/` Python package)

The next modularization step can decide whether to keep the root Justfile as a dispatcher or switch to a `mod`-based import structure once compatibility risk is acceptable.
