# Changelog

All notable changes to this project will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.org/en/1.1.0/),
and this project aims to adhere to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [Unreleased]

### Changed

- Reconciled discovery guidance across the repo so `just schema` (and bare `just` where it defaults to `schema`) is the primary machine-readable entry point, while `just --list` is documented as the human-facing inspection surface and current bridge input.

### Added

- Added `docs/annexes/just_manual_audit.md` ledger and recorded section `1.6.3 Invoking Multiple Recipes` as suitable with caveats: multi-recipe argv and `--one` are upstream cautionary context only, while agent-facing integrations should continue to issue one validated recipe per tool call (JFA-6).
- Added an `op-new` recipe that exposes the `obsidian op-new` primitive in this workspace, with schema docs for project, title, priority, and scope/body-mode issue creation.
- Added a design spec for a governed managed-recipe overlay with quarantine, human approval, git-backed audit history, and a hybrid terminal-plus-browser operator surface.
- Added the managed-overlay foundation: a new `just_for_agents/` Python package (`managed_paths`, `request_store`, and a `python -m just_for_agents` CLI), a `.just-for-agents/managed.just` partition, and root-level `managed-bootstrap`, `managed-queue`, and `managed-inspect` recipes so quarantined requests land in a single auditable layout discoverable via `just schema` (JFA-81).
- Added the approval core: `just_for_agents/projection.py` rebuilds `approved/includes/managed.just` deterministically, `just_for_agents/history.py` initializes a dedicated managed git repo and records one commit plus one decision-ledger entry per approval, and the new `managed-render-include` and `managed-approve` recipes plus an optional root-Justfile `import?` make approved managed recipes the only live include surface (JFA-82).
- Added quarantined mutation staging for managed recipes: `managed-new`, `managed-edit`, and `managed-delete` now create request artifacts through `just_for_agents/mutations.py`, `just escalate` stages candidate capability work into the queue instead of publishing directly, and README/testing coverage documents the managed review flow (JFA-83).
- Added dry-run/result capture plus browser-ready review and dashboard rendering for quarantined managed recipe requests, including new `managed-dry-run`, `managed-review`, and `managed-dashboard` operator commands on both the managed overlay and the public Just surface (JFA-84).
- Hardened the managed governance flow so bootstrap guidance now explains the quarantine-first posture, the dashboard/review surfaces report managed-history drift, and `managed-approve` / `managed-render-include` refuse to overwrite direct edits under the governed approved surface (JFA-85).
- Added a root `CLAUDE.md` with the repo mandates plus reusable guidance for working with the Obsidian CLI and obsidian-projects without carrying over OP plugin-development workflow details.

### Fixed

- Set the agent-facing `schema` recipe as the explicit `[default]` entrypoint so bare `just` deterministically returns the machine-readable discovery manifest without depending on recipe order, and documented `just --list` as the human-readable listing path.
- Fixed the Pi consumer installer and startup flow so `examples/pi-consumer/install.sh <target>` fully resets the target workspace's just-for-agents state, re-seeds the runtime bundle plus `.pi/` and `just_for_agents/`, and the consumer extension still enters just-only mode with an empty `just_schema` result if the target later loses its `Justfile`.
- Fixed `.just-for-agents/bridge.py` to parse `just --list` recipe signatures with quoted defaults correctly, so schema entries like `content='hello world'` no longer turn into bogus required parameters during live Consumer runs.
- Fixed agent-facing direct `just` integrations to fail closed on multi-recipe execution: managed request payloads now require exactly one target recipe, managed dry-runs shell out with `just --one`, and the Pi consumer example now wraps bootstrap/schema/run/escalate calls with the same single-recipe guardrail.

### Changed

- Clarified the README, consumer docs, concept notes, and agent guidance to prefer `just schema` for agent discovery, reserve `just --list` for human-facing inspection, and require exactly one validated recipe per tool call with `just --one` as the guardrail when raw `just` execution remains exposed.
- Documented the root-cwd contract for agent-facing `just` invocations, including why helper justfiles use `[no-cd]` and when callers should pass `--justfile` from outside the repo or worktree root.

## [0.3.0] - 2026-04-30

### Changed

- Started precomputing a richer research startup bundle by embedding a schema summary, research-directory snapshot, and core workspace file inventory directly in the research prompt so the agent has less reason to begin with generic discovery commands.
- Added repo-wide agent guidance to use the Just LSP for Justfile navigation and refactors when it is available.
- Split the local Qwen tuning into separate consumer and research roles, keeping `examples/pi-consumer/Modelfile` consumer-oriented and adding `examples/pi-consumer/ResearchModelfile` for autonomous research runs.
- Added `research-status` and `research-reset` recipes plus troubleshooting guidance so tmux/log inspection does not require repeated ad-hoc shell commands.
- Updated the example Pi installer to build both the consumer and research Ollama aliases so local setup matches the new split-model workflow.

### Fixed

- Fixed the startup-bundle path to use a portable research-directory snapshot loop instead of BSD-incompatible `find -maxdepth`, and escaped prompt text that was accidentally invoking shell command substitution.
- Fixed the research startup bundle to stop foregrounding `HANDOFF.md` and to explicitly forbid turning repo task lists into a new assignment or ending the round with a follow-up question.
- Fixed the generated research brief to stop suggesting bare repo filenames, and taught the prompt to treat previous-round file references as historical evidence instead of fresh path hints.
- Fixed research round finalization to validate the agent output and automatically retry once when a round ends conversationally instead of returning a real report.
- Fixed research round finalization to salvage substantive diagnosis by trimming conversational endings and normalizing the result when the model produced useful analysis but still lapsed into chat mode.
- Fixed macOS task-bundle temp-file creation by switching the attached prompt bundle to the BSD-safe `mktemp` template form without a suffix after the `X`s.
- Fixed the startup bundle to stop leaking concrete repo and round-file path hints into the isolated workspace, reducing failed reads against files that only exist in the original repository.
- Fixed the scratch-workspace startup bundle to present schema metadata as reference-only context so the research agent does not try to run `just` without a Justfile.
- Fixed research model resolution and temp opencode config generation so autonomous research can prefer a dedicated `just-research-qwen3.6:latest` Ollama model when it is installed.
- Changed research launches to attach the full task bundle as a file to `opencode run`, and fixed the attachment argument order so the task message is not misread as a file path.
- Changed the startup bundle to include recent round summaries instead of raw previous-round transcripts, reducing contamination from stale tool chatter and bad path references.
- Changed research launches to run in an isolated scratch workspace containing only `RESEARCH_TASK.md`, reducing repo-file drift during autonomous rounds.

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

[Unreleased]: https://github.com/earchibald/just-for-agents/compare/v0.3.0...HEAD
[0.3.0]: https://github.com/earchibald/just-for-agents/compare/v0.2.0...v0.3.0
[0.2.0]: https://github.com/earchibald/just-for-agents/compare/v0.1.0...v0.2.0
[0.1.0]: https://github.com/earchibald/just-for-agents/releases/tag/v0.1.0
