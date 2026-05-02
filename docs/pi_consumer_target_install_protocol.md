# Pi consumer target-install test protocol

## Goal

Validate that `examples/pi-consumer/install.sh <target>` can reset a scratch workspace into a runnable just-for-agents install, then launch Pi in that target and behave like the Consumer flow described in `docs/personal_power_agent.md`.

Target workspace used for live testing:

```bash
/Users/earchibald/scratch/014-jfa-testing
```

## Reset/install command

Run from the development checkout:

```bash
bash examples/pi-consumer/install.sh /Users/earchibald/scratch/014-jfa-testing
```

Expected reset semantics:

- remove prior just-for-agents state from the target: `.pi/`, `.just-for-agents/`, `just_for_agents/`, `Justfile`, `VERSION`, `README.md`, `CHANGELOG.md`
- re-seed the runtime bundle from the development checkout
- rebuild/refresh the Pi-local `.pi/` bundle in the target
- keep the Ollama model registration flow in `~/.pi/agent/models.json`

## Iteration log

### Iteration 1 — reproduce the broken target install

Command:

```bash
~/.config/superpowers/worktrees/just-for-agents/jfa-87-target-install-script/examples/pi-consumer/install.sh /Users/earchibald/scratch/014-jfa-testing
```

Observed result:

- only `.pi/` was installed into the target
- the target still had no `Justfile`
- `pi` in the target fell back to the default tool surface because the consumer extension had nothing to bootstrap

Conclusion:

- target-install support alone was not enough
- the installer must provision a runnable just-for-agents runtime, not only the Pi overlay

### Iteration 2 — install runtime bundle and verify startup

After redesigning the installer, the target now contains:

- `.just-for-agents/`
- `just_for_agents/`
- `Justfile`
- `VERSION`
- `README.md`
- `CHANGELOG.md`
- `.pi/`

Quick verification:

```bash
cd /Users/earchibald/scratch/014-jfa-testing
just schema | head
```

Observed result:

- `just schema` returns the expected just-for-agents manifest from the scratch workspace

### Iteration 3 — tmux Pi smoke test

Launch:

```bash
tmux new-session -d -s jfa87-pi-smoke -n consumer 'cd /Users/earchibald/scratch/014-jfa-testing && pi'
```

#### Check 1 — startup branding

Observed result:

- startup banner renders in tmux
- branding matches the Consumer profile
- the prompt text says the only tools are `just_schema`, `just_run`, `just_refresh`, and `just_escalate`

#### Check 2 — tool-surface restriction

Prompt sent via tmux:

```text
Before doing anything else, list the exact tool names available to you right now and nothing else.
```

Observed result:

```text
just_schema, just_run, just_escalate, just_refresh
```

Conclusion:

- the live Pi session is now using the just-only Consumer tool surface

#### Check 3 — `just_run` smoke

Prompt:

```text
Calculate the MD5 hash of the README.md file.
```

Expected hash:

```text
6448adce52a1bdd9141771b5822041c3
```

Observed result:

- Pi chose `just_run`
- the returned hash matched the shell-computed hash exactly

#### Check 4 — first `just_escalate` smoke

Prompt:

```text
Create a file called test.txt with the text 'hello'.
```

Observed result:

- Pi correctly chose `just_escalate`
- the visible-agent tmux session `just-for-agents-escalate` launched from the scratch install
- the first attempt exposed another missing runtime dependency: the target workspace also needed the in-tree `just_for_agents/` Python package, not only `.just-for-agents/`

Conclusion:

- the installer bundle had to grow beyond the Justfile wrappers

### Iteration 4 — add `just_for_agents/` to the target install

Installer refinement:

- reset and copy `just_for_agents/` alongside `.just-for-agents/`, `Justfile`, `VERSION`, `README.md`, `CHANGELOG.md`, and `.pi/`

Observed result:

- the escalation tmux session now progressed through managed request creation and dry-run/approval work instead of failing immediately on a missing module

### Iteration 5 — fix schema parsing for quoted defaults

Live failure uncovered after the request was approved:

- the Consumer refreshed schema after the new recipe appeared
- the bridge parsed a signature like `content='hello world'` with a naive whitespace split
- the Consumer then saw a bogus required parameter name (`world'`) and could not call the new recipe

Fix applied:

- `.just-for-agents/bridge.py` now uses shell-aware tokenization for `just --list` output instead of `split()`

### Iteration 6 — fresh end-to-end rerun after installer + bridge fixes

Fresh reset:

```bash
bash examples/pi-consumer/install.sh /Users/earchibald/scratch/014-jfa-testing
```

Fresh tmux run:

```bash
tmux new-session -d -s jfa87-pi-smoke -n consumer 'cd /Users/earchibald/scratch/014-jfa-testing && pi'
```

Observed result:

- startup branding still passed
- tool-surface restriction still passed
- `just_run` (`md5 README.md`) still passed
- `just_escalate` still launched correctly and staged a new quarantined request
- the remaining blocker moved deeper again: the latest request (`file-write`) is still failing during the managed dry-run stage before the user-level `test.txt` action completes

Current blocker snapshot:

- request: `req-20260502-001`
- target recipe: `file-write`
- current request status: `quarantined`
- current dry-run summary: `dry-run failed for file-write (exit 1)`

## Current status

### Passing

- target install resets and reseeds the scratch workspace
- Pi startup branding appears in tmux
- only the four `just_*` consumer tools are exposed
- `just_schema` works from the target install
- `just_run` works from the target install
- `just_escalate` launches the expected visible-agent tmux session from the target install
- schema refresh now handles quoted defaults with spaces correctly

### Still open

- complete the end-to-end escalation smoke so the scratch install can successfully add a new capability and create `test.txt`
- document/fix the managed dry-run failure uncovered by the latest live escalation session
