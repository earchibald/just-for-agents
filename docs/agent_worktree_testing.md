# Agent Worktree Testing Procedure

This procedure is for **agents** working a `just-for-agents` issue inside a git worktree (e.g. `.claude/worktrees/<issue-id>/`). It installs the project-local Pi Consumer Agent into the worktree, runs a small set of smoke tests against the local model, verifies the escalation loop, and cleans up any state that should not be committed.

The procedure is non-interactive end-to-end so it can be driven by another agent.

## 0. Assumptions

You are working inside the worktree directory. All commands assume the worktree root is the current working directory. Do not run any of this from the main checkout.

Required on the host:

- `pi` (`@mariozechner/pi-coding-agent`)
- `ollama` running locally (`ollama serve` if not already up)
- `just`, `npm`, `python3`

The base model `qwen3.6:latest` must already be pulled into Ollama. The installer rebuilds the `just-consumer-qwen3.6:latest` alias on every run from the local `examples/pi-consumer/Modelfile`, so prompt and SYSTEM-block changes take effect.

## 1. Verify prerequisites

```bash
command -v pi ollama just npm python3
ollama list | grep -q '^qwen3.6:latest' || echo "MISSING: qwen3.6:latest base model"
```

If any are missing, stop and report — do not attempt to install host-level dependencies from inside a worktree run.

## 2. Run the installer

```bash
bash examples/pi-consumer/install.sh
```

Expected outcomes:

- `~/.pi/agent/models.json` is updated (a `.bak` is written if it already existed); the Ollama provider entry is merged, not overwritten.
- `just-consumer-qwen3.6:latest` is rebuilt from the worktree's `examples/pi-consumer/Modelfile`.
- `.pi/settings.json`, `.pi/extensions/just-consumer.ts`, `.pi/extensions/package.json`, and `.pi/consumer-profile.json` are written into the worktree root.
- `npm install --prefix .pi/extensions` resolves `typebox`.

## 3. Smoke tests

Run each test with `pi --print --no-session` so the session is ephemeral and there is no TUI to drive. The Consumer extension activates on `session_start` whenever a `Justfile` is present in the cwd, which is true at the worktree root.

### 3.1 — Schema discovery (`just_schema`)

```bash
pi --print --no-session "Show me what tools are available here."
```

**Pass criteria:** the response lists recipes from the current `Justfile` (e.g. `version`, `add-tool`, `escalate`, `md5`, `research`). The agent should not invent recipes that are not in the schema.

### 3.2 — Recipe execution (`just_run`)

```bash
pi --print --no-session "Calculate the MD5 hash of the README.md file."
EXPECTED=$(md5 -q README.md)
echo "expected: $EXPECTED"
```

**Pass criteria:** the response contains `$EXPECTED`. This confirms `just_run` is wired up and that named-parameter → positional-argv mapping works for `md5(file)`.

### 3.3 — Escalation loop (`just_escalate`)

```bash
pi --print --no-session "Create a file called test.txt with the text 'hello'."
```

There is no existing recipe that writes a file, so the Consumer should call `just_escalate`, the Senior Creator Agent should add a recipe (e.g. `write-file` or similar), and the Consumer should then call it via `just_run`.

**Pass criteria:**

- `test.txt` exists in the worktree and contains `hello`.
- `git diff Justfile` shows a new recipe added by the Senior Agent.
- `git diff CHANGELOG.md` shows an `### Added` entry for the new recipe (the Senior Agent maintains the changelog).

If escalation hangs, check that `just escalate` can find a Senior Agent backend on this host. The escalation channel is independent of the Consumer wiring — flag and stop, do not retry blindly.

### 3.4 — Tool restriction is positive, not punitive

Read the system prompt actually used at runtime:

```bash
grep -n "Your only tools are\|toolset\|capability surface" examples/pi-consumer/just-consumer.ts examples/pi-consumer/Modelfile examples/pi-consumer/profile.json
```

**Pass criteria:** the agent-facing strings describe the four `just_*` tools as the entire toolset and do not contain admonishments like "Never use raw bash, edit, or write" — those tools are removed by `pi.setActiveTools(CONSUMER_TOOLS)` and should not appear in prompt text.

## 4. Cleanup before commit / PR

The smoke tests intentionally mutate the worktree (escalation rewrites `Justfile` and `CHANGELOG.md`, and writes `test.txt` plus a `.pi/` directory). None of that should land in the PR.

```bash
# Drop test artifacts that the Senior Agent or test commands created.
rm -f test.txt
git checkout -- Justfile CHANGELOG.md

# Drop the project-local Pi install. The installer is the source of truth;
# committing the installed copy duplicates state that already lives under examples/pi-consumer/.
rm -rf .pi/

# Confirm the working tree only contains your intended issue changes.
git status
```

If `git status` shows anything other than the files you deliberately changed for the issue, investigate before committing.

## 5. What this does not test

- The TUI experience (startup branding, `ctx.ui.notify`, status widget). These are user-visible only and require an interactive `pi` session.
- The `tool_call` defense-in-depth hook. Because `pi.setActiveTools` already removes `bash`, `edit`, and `write` from the active toolset, the model never sees those names and the hook is unreachable in normal operation. Exercising it requires a separate test that bypasses `setActiveTools`.
- Cross-host parity. The smoke tests assume the local Ollama daemon is responsive on this machine.

If your issue touches any of those areas, add an issue-specific test on top of this baseline rather than modifying the baseline itself.
