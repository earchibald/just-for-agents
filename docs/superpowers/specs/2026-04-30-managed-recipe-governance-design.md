# Managed Recipe Governance and Review Surface

## Summary

This spec defines a first-pass governance system for mutable `just-for-agents` recipes. The system introduces a managed overlay under `.just-for-agents/managed/`, a quarantine-to-approval workflow, and a hybrid operator experience: terminal-first queue and settings flows, with browser-based review screens for diffs, metadata, and dry-run results.

The goal is to ensure that managed non-core recipes are never exposed for normal use until a human approves them. Every approved change to the installed recipe footprint is recorded as its own git commit in the governed overlay history.

## Decisions captured from brainstorming

- Optimize for a **hybrid** operator surface: terminal-first workflow, browser assist for review and comparison.
- Require approval for **any change to managed recipes**, regardless of whether it originates from an agent or a human.
- Govern **managed non-core recipes only**. Core protocol/bootstrap internals stay outside the approval flow.
- Allow operators to **inspect, diff, edit, and dry-run quarantined changes** without exposing them as live recipes.
- Record **one git commit per approval decision**.
- Assume a **single local operator per workspace** for the first version.

## Goals

1. Make escalated recipe creation and recipe maintenance auditable and safe.
2. Keep quarantined changes executable for evaluation but unavailable as normal workspace tools.
3. Preserve a clean, discoverable live recipe surface so `just schema` and `just --list` only show approved managed recipes.
4. Provide a usable human control surface for queue management, recipe inspection, edits, approvals, rejections, and settings.
5. Detect and prevent uncontrolled drift between the approved recipe footprint and the live projection.

## Non-goals

- Multi-reviewer approvals, remote collaboration, or networked queue coordination.
- Governance of protected protocol recipes such as `schema`, `bootstrap`, `add-tool`, `remove-tool`, `install-lsp`, `test-agent`, and other core internals.
- A full browser application as the primary surface.
- General-purpose source control for the entire repository; this governs only the managed recipe footprint.

## Current context

The repository already has:

- A root `Justfile` that delegates to split recipe files under `./.just-for-agents/`.
- An `@escalate` recipe that launches a senior agent to add or modify capability.
- A documented expectation that repo changes update `CHANGELOG.md`.

Today, escalation effectively writes capability into the active recipe surface. The missing piece is a governed layer that treats agent output and manual edits as proposals that must be reviewed before publication.

## Proposed architecture

### 1. Governed overlay

Introduce a dedicated managed area under:

```text
.just-for-agents/managed/
  config/
    managed.toml
  quarantine/
    requests/<request-id>/
      request.json
      candidate.just
      metadata.json
      notes.md
      dry-run/
  approved/
    recipes/<recipe-name>.just
    includes/managed.just
  rejected/
    requests/<request-id>/
  history/
    decisions.jsonl
```

This directory is the mutable source of truth for governed recipes.

### 2. Live projection boundary

Only `approved/includes/managed.just` is included in the live Just surface. Quarantined files never appear in the include used by `just schema`, `just --list`, or normal recipe execution.

The root `Justfile` and current protocol files remain the stable shell around this system:

- protected core files continue to expose bootstrap and protocol behavior
- managed recipes are projected into the live surface through one generated include
- the generated include is rebuilt whenever an approval decision changes the approved set

### 3. Separate governed history

The first version should treat `.just-for-agents/managed/` as its own governed history root, backed by a dedicated git repository in that directory. This keeps approval history focused on the mutable recipe footprint instead of mixing it with the main repo's broader source history.

Each **approval decision** creates exactly one commit in the managed repo. Rejections are recorded in `history/decisions.jsonl` but do not need a git commit unless they change approved state.

## Operator surface

### Terminal-first dashboard

The primary operator experience is a terminal dashboard with three logical views:

1. **Queue** — pending quarantined requests, status, source, affected recipes, risk flags, and dry-run state
2. **Library** — currently approved managed recipes, latest approval metadata, and pending replacement requests
3. **Settings** — approval defaults, dry-run policy, diff preferences, direct-edit policy, and managed path configuration

The first version does not need a complex mouse-driven TUI. It should behave like a structured terminal application that can render list/detail screens, open an editor for changes, and launch browser review screens when visual comparison is better than plain text.

### Browser review companion

Use browser screens for:

- side-by-side recipe diffs
- approval summaries
- metadata and risk inspection
- dry-run output review
- settings pages where layout improves comprehension

The browser is a review aid, not the system of record. Final actions still occur through the terminal operator flow.

## Data model

### Change request

Each proposed mutation is represented as a **change request**:

- `request_id`
- `source` (`escalation`, `manual-add`, `manual-edit`, `manual-delete`, `drift-import`)
- `status` (`quarantined`, `approved`, `rejected`, `superseded`)
- `created_at`
- `updated_at`
- `target_recipes`
- `base_approved_commit`
- `author_label`
- `review_notes`
- `risk_flags`
- `dry_run_summary`

### Managed recipe record

Each approved recipe has a tracked record consisting of:

- recipe name
- file path under `approved/recipes/`
- enabled/disabled status
- current approval request ID
- approved timestamp
- latest managed commit

### Decision ledger

`history/decisions.jsonl` stores append-only review records:

- request ID
- decision (`approve`, `reject`, `supersede`)
- operator label
- timestamp
- rationale
- resulting managed commit, if any

## Core workflows

### 1. Escalated creation

1. An agent or existing escalation path produces a candidate recipe change.
2. Instead of writing directly into the live recipe surface, the system creates `quarantine/requests/<id>/`.
3. The operator reviews the candidate, edits it if needed, and runs dry-runs inside the quarantine context.
4. On approval, the candidate is copied into `approved/recipes/`, the generated include is rebuilt, the ledger is appended, and a commit is created in the managed repo.
5. The live Just surface now exposes the approved recipe.

### 2. Manual add/edit/delete

All human-authored mutations go through the same request model. The operator does not edit approved files directly as a normal workflow; instead they create a request, review it, and then approve it.

Because v1 assumes a single local operator, the same person may author and approve a request. That self-approval must still be recorded explicitly in the decision ledger rather than treated as an implicit publish.

- **Add** creates a new candidate recipe request
- **Edit** clones the current approved version into a new request
- **Delete** creates a tombstone request whose approval removes the recipe from `approved/recipes/` and regenerates the include

### 3. Quarantine dry-run

Dry-runs execute only against the quarantined request context. They may call the candidate recipe and supporting helpers, but the live include remains unchanged until approval.

Dry-run output is written back into `quarantine/requests/<id>/dry-run/` so the operator can review it later.

### 4. Rejection

Rejecting a request preserves the request directory and decision record for audit, marks the request rejected, and leaves the approved footprint unchanged.

### 5. Supersession

If a new request replaces an older still-pending request for the same recipe, the older request is marked `superseded` rather than silently disappearing.

## Safety and drift rules

### Protected boundary

Governance applies only to managed non-core recipes. Protected protocol/bootstrap recipes stay outside this system and continue to be maintained by existing repo practices.

### No direct live edits

Direct edits under `approved/` are treated as drift. The system should detect them and refuse to publish or expose ambiguous state until the operator either:

1. imports the change into a formal request, or
2. restores approved state from the managed history

### No quarantine leakage

Quarantined recipes must never appear in:

- `just schema`
- `just --list`
- generated live include files
- the default recipe execution path

### Fail closed

If include generation, ledger writing, or managed commit creation fails, the live surface remains on the last known approved state.

## Git and audit model

The governed history exists to answer: "What recipe footprint was installed at this workspace, and why?"

Rules:

- one approval decision -> one managed git commit
- commit message references the request ID and action
- decision ledger entry and git commit must agree on the resulting state
- live projection is regenerated from approved state, not from ad hoc working-tree edits

Suggested commit shapes:

- `approve recipe foo from request req-20260430-001`
- `approve edit to recipe foo from request req-20260430-014`
- `approve deletion of recipe foo from request req-20260430-019`

## Integration with existing just-for-agents flows

### Escalation changes

`just escalate` should stop writing capability directly into the active Just surface. Instead it becomes a producer of quarantined requests for human review.

### Discovery changes

`just schema` and `just --list` continue to be the discovery contract. They must reflect:

- protected stable recipes
- approved managed recipes
- never quarantined requests

### Management commands

The governance surface should expose a focused command set for the operator. Exact command names can be planned later, but the design expects capabilities equivalent to:

- list queue
- inspect request
- edit request
- run quarantine dry-run
- approve request
- reject request
- list approved recipes
- create manual request
- detect/import drift
- open settings

## Error handling

- If request materialization fails, no partial live changes are made; the request stays absent or explicitly marked failed.
- If dry-run fails, the request remains quarantined with a visible failure summary.
- If approval steps succeed except for the final commit, the system must roll back projection changes or mark the state broken and refuse publication until repaired.
- If the managed repo is missing or corrupted, the operator surface should switch to a repair-oriented mode instead of pretending approvals are possible.

## Testing strategy

The implementation plan should cover:

1. request creation for add/edit/delete flows
2. projection rules that expose only approved recipes
3. quarantine dry-run isolation
4. one-commit-per-approval behavior
5. rejection and supersession handling
6. drift detection for direct edits under `approved/`
7. compatibility with `just schema`
8. terminal workflow coverage for queue/library/settings operations

## Phasing

### Phase 1

- managed directory structure
- request creation and storage
- approval/rejection flow
- approved include generation
- managed git history
- terminal queue and inspect flow
- browser diff/review screens

### Phase 2

- richer settings panel
- drift import helpers
- recipe library management views
- stronger risk analysis and dry-run reporting

### Deferred

- multi-reviewer policy
- remote queue synchronization
- role-based permissions

## Recommendation

Build the first version as a **governed overlay with a terminal-first operator dashboard and browser review companion**. This is the smallest design that cleanly satisfies quarantine, approval, audit, and live-surface isolation without overcommitting to a heavy UI framework too early.
