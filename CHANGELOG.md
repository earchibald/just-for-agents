# Changelog

All notable changes to this project will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.org/en/1.1.0/),
and this project aims to adhere to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [Unreleased]

### Added

- Added `docs/annexes/just_manual_audit.md` ledger and recorded section `1.6.3 Invoking Multiple Recipes` as suitable with caveats: multi-recipe argv and `--one` are upstream cautionary context only, while agent-facing integrations should continue to issue one validated recipe per tool call (JFA-6).

## [0.2.0] - 2026-04-30

### Fixed

- Fixed `@schema`, `@bootstrap`, and `@version` so recipe-level `@` no longer combines with step-level `@` and accidentally toggles command echoing back on.
- Fixed the research runner to emit validated absolute local-path inputs for each round and explicitly distinguish workspace paths from URL-only tool inputs before launching the agent.
- Fixed macOS temp-runner creation for research and escalation by switching to BSD-compatible `mktemp` templates.
- Fixed local research runs to stop auto-enabling Exa MCP, reducing wrong-tool selection against workspace file paths during autonomous repo analysis.
- Fixed the research harness to embed startup context directly in the prompt instead of front-loading raw local file paths, and tuned the Consumer to stop asking for another round after successful completion.
- Fixed local research launches to run `opencode` with `--pure`, disabling external plugins like Exa during repository-first research rounds.
- Fixed research launches to use a temporary opencode config with `.mcp` removed, preventing persisted Exa MCP settings from leaking into repository-first tmux research sessions.
- Fixed research guidance to hard-bound analysis to the repository root and ignore parent-directory `.claude`/`RTK` files that were contaminating autonomous rounds.
- Fixed research guidance to prefer non-bash local tools and to spell out the required `bash.description` field, and taught the Consumer to always pass research subjects via `subject_title`.

### Changed

- Started modularizing the root `Justfile` by moving helper implementations into `./.just-for-agents/` and splitting recipe bodies into focused external `protocol.just`, `agent.just`, `research.just`, and `utility.just` files while preserving the existing public recipe surface in the root file.

## [0.1.0] - 2026-04-30

### Added

- Added a `VERSION` file as the canonical project version source, plus a `just version` recipe and schema manifest version field for agent discovery.
- Added a visible tmux-backed agent runner for long-running Justfile workflows so research and escalation runs can execute in a named session and window with persisted output.
- Added automatic iTerm2 tmux control-mode launch for newly started visible-agent sessions, while keeping standard tmux attach commands available for later reattachment.
- Added an initial project changelog using the Keep a Changelog format.
- Added persistent agent guidance requiring `CHANGELOG.md` updates before an agent stops after making repo changes.
- Added a complete Pi consumer example bundle under `examples/pi-consumer/` for local project setup.

### Changed

- Strengthened autonomous research prompt guidance so research rounds proceed without pausing for clarification in normal batch runs.
- Changed `just research` so `rounds` means the number of **new** rounds to append during the current invocation instead of retrying from round 1.
- Updated the Consumer Agent guidance in both the live Pi extension and the reference example so research requests like "1 iteration" map directly to one additional round.
- Updated the user and annex documentation to describe the new tmux launch behavior and incremental research flow.

### Fixed

- Fixed the research flow so an existing `round_1.md` no longer causes a one-iteration request to skip work and ask whether round 2 should run.
- Fixed the autonomous research prompt so the launched agent proceeds without pausing to ask clarifying questions in normal batch runs.
- Fixed Consumer argument mapping so skipped optional parameters with defaults are filled automatically instead of incorrectly requiring positional co-passing.
- Fixed research prompt guidance to steer agents toward targeted reads and truncation recovery instead of degrading into meta-conversation.

[Unreleased]: https://github.com/earchibald/just-for-agents/compare/v0.2.0...HEAD
[0.2.0]: https://github.com/earchibald/just-for-agents/compare/v0.1.0...v0.2.0
[0.1.0]: https://github.com/earchibald/just-for-agents/releases/tag/v0.1.0
