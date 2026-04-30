# just-for-agents helper layer

This directory is the first modularization step for the root `Justfile`.

- The root `Justfile` remains the stable public entrypoint and discovery surface.
- High-value helper implementations live here so the core Justfile stays smaller and easier for agents to reason about.
- Current extracted helpers:
  - `bridge.py`
  - `deskill.py`
  - `research-index.py`
  - `visible-agent.sh`

The next modularization step can split recipe groups into `.just` modules while preserving root-level compatibility.
