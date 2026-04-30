# GEMINI.md

## Guiding Principle
**RADICALLY SIMPLE**

## Project Mandates
- **Output is the API**: Leverage `just --list` for discovery. Avoid complex source parsing.
- **Use the Just LSP**: When working on Justfiles or recipes, prefer `just-lsp`/the Just LSP for navigation and refactors when it is available.
- **Documentation is Data**: Use standard `[doc()]` attributes to communicate with agents.
- **Zero Configuration**: A `Justfile` should be all that's needed to start.
- **Self-Skilling**: The agent must be able to extend the `Justfile` it is currently using.
- **Keep the Changelog Current**: If an agent changes the repo, it should update `CHANGELOG.md` before stopping.
