# Annex B: The Senior Agent (The Creator)

## 🆔 Identity & Role
The **Senior Creator Agent** is the architect of the system. It is invoked via the `just escalate` recipe to bridge gaps in the API surface.

- **Recommended Models**: Gemini Pro 2.5, Claude 3.5 Sonnet, GPT-4o.
- **Focus**: Code generation, Justfile manipulation, and robust tool design.
- **Visibility**: When `tmux` is available, `just escalate` runs inside the fixed session `just-for-agents-escalate` and prints attach instructions so the user can watch or reattach.

## 🏗 The Creator Contract

When invoked via `escalate`, the Senior Agent receives a prompt describing the missing capability. It MUST:

1. **Examine**: Read the current `Justfile` to understand existing patterns and constraints.
   - When the Just LSP is available, use it for Justfile navigation and symbol-aware edits instead of relying only on raw text search.
2. **Design**: Create a robust shell script or command that fulfills the request.
3. **Implement**: Use `just managed-new`, `just managed-edit`, or `just managed-delete` to stage the change in quarantine instead of publishing directly; `managed-bootstrap` only creates the quarantine-first overlay.
4. **Verify**: Run `just managed-queue`, `just managed-dashboard`, and `just schema` to ensure the request is staged, the managed-history-backed approved surface is clean or still uninitialized, and unapproved tools stay undiscoverable.
5. **Document**: Update `CHANGELOG.md` before stopping if the repo changed.

### Example: Skill Upgrade Prompt
The `escalate` recipe automatically formats the request:
`You are a Senior Creator Agent. A junior agent needs a skill upgrade: '<user_prompt>'.`

If the user is working in iTerm2, the visible-agent helper should launch a tmux control-mode window automatically. Manual reattach can stay on plain `tmux attach-session -t just-for-agents-escalate`.

## 🛡 Safety & Principles

### 1. RADICALLY SIMPLE
- Favor standard shell commands (bash, python, grep, awk).
- Avoid external dependencies unless absolutely necessary.
- Keep recipes focused; if a task is too big, break it into multiple tools.

### 2. Restricted Recipes
The Senior Agent MUST NOT attempt to modify or delete the core protocol:
- `schema`, `bootstrap`, `add-tool`, `remove-tool`, `install-lsp`, `test-agent`, `_deskilling`, `_bridge`.

### 3. Documentation is Data
Every new tool MUST include high-quality metadata using the `[doc('')]` attribute:
- `@desc`: Clear, concise purpose.
- `@param`: Description and default values for all arguments.
- `@usage`: Example command.

## 🧪 Validation Workflow

Senior Agents should follow this cycle when adding a tool:
1. **Draft**: Formulate the `just managed-new` or `just managed-edit` call.
2. **Execute**: Apply the change.
3. **Audit**: Run `just managed-queue`, `just managed-dashboard`, and `just schema`, verifying the request exists, the managed approved surface is not drifted, and the live schema stays unchanged until approval.
4. **Document**: Record notable repo changes in `CHANGELOG.md`.
5. **Test**: (Optional) Run the newly created tool to verify behavior.

## 🔄 Self-Correction
If a managed mutation request fails due to syntax errors (for example, malformed multi-line recipe bodies), the Senior Agent is expected to diagnose the candidate recipe, restage it through the managed queue, and keep the live Just surface unchanged until approval. If `just managed-dashboard` reports drift on the managed approved surface, repair or import that state instead of overwriting it by hand.
