# Changelog

All notable changes to this project will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.org/en/1.1.0/),
and this project aims to adhere to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [Unreleased]

### Fixed

- Fixed `@schema`, `@bootstrap`, and `@version` so recipe-level `@` no longer combines with step-level `@` and accidentally toggles command echoing back on.
- Fixed the research runner to emit validated absolute local-path inputs for each round and explicitly distinguish workspace paths from URL-only tool inputs before launching the agent.

### Changed

- Started modularizing the root `Justfile` by moving helper implementations into `./.just-for-agents/` while preserving the existing public recipe surface in the root file.

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

[Unreleased]: https://github.com/earchibald/just-for-agents/compare/v0.1.0...HEAD
[0.1.0]: https://github.com/earchibald/just-for-agents/releases/tag/v0.1.0
