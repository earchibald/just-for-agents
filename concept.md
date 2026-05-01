# just-for-agents: Concept & Architecture

## 1. Vision
Transform the `Justfile` from a simple command runner into a structured, discoverable, and self-mutating API surface for AI agents.

## 2. The "Agentic Schema" (Provisional)
We use the `[doc('...')]` attribute to provide structured metadata. This is required because standard `#` comments in `just` are limited to single-line summaries.

### Documentation Standards
- **Multi-line Blocks**: All agent-specific metadata must live inside `[doc('...')]`.
- **Quote Safety**: Use single quotes `[doc('...')]` to wrap the block, and double quotes for internal strings (or vice versa), being careful not to terminate the attribute prematurely.
- **Metadata Tags**:
    - `@desc`: High-level summary.
    - `@param <name> <description>`: Argument definitions.
    - `@usage <context>`: Semantic guidance for the LLM.
    - `@returns <format>`: Expected output structure.

### Example
```just
# bootstrap lister
@list:
  just --list --unsorted

[doc('@desc List all active containers
@param profile The deployment profile (default: "dev")
@usage Use this to verify the system state after a deploy.
@returns table')]
list-containers profile="dev":
    docker ps --filter "label=profile={{profile}}"
```

## 3. The Discovery Loop (Output-Based)
Instead of parsing the `Justfile` source directly, the agent should prefer the exported discovery surface. Running `just schema` (or bare `just` when it defaults to `schema`) yields the machine-readable contract. Internally, the bridge currently derives that manifest from `just --list --unsorted`, which remains useful for human-facing inspection and implementation plumbing.

### Discovery Flow
1. **Reflection**: The bridge runs `just --list --unsorted`.
2. **Scanning**: The bridge scans the output for lines starting with `    # @`.
3. **Mapping**: These lines are mapped to the recipe immediately following them.
4. **Registration**: The bridge emits `just schema`, and agents register tools from that machine-readable manifest, using `@usage` as the primary selection criteria.

## 4. Technical Components
- **API Bridge**: A utility that runs `just --list`, parses the `# @tag` metadata, and emits the JSON schema exposed via `just schema` (e.g., OpenAI Tool Specs).
- **Execution Wrapper**: A thin layer that captures `stdout`, `stderr`, and exit codes, re-formatting them into "Agent-Friendly" responses.
- **Protocol Recipes**: A set of standardized recipes (e.g., `list`, `schema`, `validate`) that define the agent's interaction with the workspace.

## 5. Open Questions
- Should we support "private" recipes (prefixed with `_`) that the agent *uses* but doesn't *expose* as top-level tools?
- How do we handle environment variables that recipes might depend on?
