# GEMINI.md

## Guiding Principle
**RADICALLY SIMPLE**

## Project Mandates
- **Output is the API**: Use `just schema` as the primary machine-readable discovery surface. Use `just --list` for human-facing inspection, and avoid complex source parsing.
- **One Recipe per Tool Call**: Agent-facing invocations should execute exactly one validated recipe; if direct `just` argv remains exposed, prefer `just --one` to fail closed on accidental multi-recipe calls.
- **Use the Just LSP**: When working on Justfiles or recipes, prefer `just-lsp`/the Just LSP for navigation and refactors when it is available.
- **Documentation is Data**: Use standard `[doc()]` attributes to communicate with agents.
- **Zero Configuration**: A `Justfile` should be all that's needed to start.
- **Self-Skilling**: The agent must be able to extend the `Justfile` it is currently using.
- **Keep the Changelog Current**: If an agent changes the repo, it should update `CHANGELOG.md` before stopping.
