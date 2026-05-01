"""Managed-overlay git history and approval flow.

The managed overlay keeps its own git history rooted at
``.just-for-agents/managed/``. One approval decision == one commit. The
decision ledger (``history/decisions.jsonl``) and the live projection
(``approved/includes/managed.just``) are both staged into that commit so
the audit trail and the surface they describe stay locked together.
"""

from __future__ import annotations

import json
import shutil
import subprocess
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from .drift import ManagedDriftError, ensure_clean_managed_surface
from . import projection
from .managed_paths import ManagedPaths
from .request_store import Request, RequestStore


class ApprovalError(RuntimeError):
    """Raised when an approval cannot be applied."""


def _run_git(repo_dir: Path, *args: str) -> subprocess.CompletedProcess[str]:
    result = subprocess.run(
        ["git", *args],
        cwd=repo_dir,
        check=True,
        capture_output=True,
        text=True,
    )
    return result


def ensure_managed_repo(paths: ManagedPaths) -> Path:
    """Initialize the managed-overlay git repo. Idempotent.

    On first call this runs ``git init`` inside ``managed_root``, configures
    a local identity so commits succeed in hermetic environments, and seeds
    one "initialize managed overlay" commit over the governed approved/history
    files so later drift checks have a clean baseline.
    Returns the managed repo path.
    """

    repo_dir = paths.managed_root
    repo_dir.mkdir(parents=True, exist_ok=True)
    git_dir = repo_dir / ".git"

    if not git_dir.exists():
        _run_git(repo_dir, "init", "--quiet", "--initial-branch=main")
        _run_git(repo_dir, "config", "user.name", "just-for-agents managed overlay")
        _run_git(repo_dir, "config", "user.email", "managed-overlay@local")
        _run_git(repo_dir, "config", "commit.gpgsign", "false")
        _run_git(repo_dir, "add", "-A", "--", "approved", "history/decisions.jsonl")
        _run_git(repo_dir, "commit", "--allow-empty", "-m", "initialize managed overlay")

    return repo_dir


def append_decision(paths: ManagedPaths, entry: dict[str, Any]) -> None:
    """Append a single decision record as one JSON line."""

    paths.history_dir.mkdir(parents=True, exist_ok=True)
    line = json.dumps(entry, sort_keys=True) + "\n"
    with paths.decisions_log.open("a", encoding="utf-8") as fh:
        fh.write(line)


def commit_approval(
    paths: ManagedPaths,
    *,
    request_id: str,
    action: str,
    message: str | None = None,
) -> str:
    """Stage the governed approved/history surface and create one git commit.

    Returns the resulting short SHA.
    """

    repo_dir = ensure_managed_repo(paths)
    subject = message or f"approve {action} from {request_id}"
    _run_git(repo_dir, "add", "-A", "--", "approved", "history/decisions.jsonl")
    _run_git(repo_dir, "commit", "-m", subject)
    sha = _run_git(repo_dir, "rev-parse", "--short=7", "HEAD").stdout.strip()
    return sha


def _copy_candidate_to_approved(paths: ManagedPaths, request: Request) -> list[Path]:
    candidate = paths.quarantine_requests_dir / request.request_id / "candidate.just"
    if not candidate.is_file():
        raise ApprovalError(
            f"request {request.request_id} has no candidate.just to approve"
        )
    if not request.target_recipes:
        raise ApprovalError(
            f"request {request.request_id} has no target_recipes; cannot project"
        )

    paths.approved_recipes_dir.mkdir(parents=True, exist_ok=True)
    written: list[Path] = []
    for recipe_name in request.target_recipes:
        target = paths.approved_recipes_dir / f"{recipe_name}.just"
        shutil.copyfile(candidate, target)
        written.append(target)
    return written


def approve_request(
    paths: ManagedPaths,
    store: RequestStore,
    request_id: str,
    *,
    operator_label: str = "",
    rationale: str = "",
    now: datetime | None = None,
) -> dict[str, Any]:
    """Approve a quarantined request: project, commit, ledger.

    Returns the decision-ledger entry that was written.
    """

    request = store.get(request_id)
    if request is None:
        raise ApprovalError(f"unknown request: {request_id}")
    if request.status != "quarantined":
        raise ApprovalError(
            f"request {request_id} is {request.status!r}; only quarantined requests can be approved"
        )

    try:
        ensure_clean_managed_surface(paths)
    except ManagedDriftError as exc:
        raise ApprovalError(str(exc)) from exc

    ensure_managed_repo(paths)

    _copy_candidate_to_approved(paths, request)
    projection.write_include(paths)

    moment = (now or datetime.now(timezone.utc)).replace(microsecond=0)
    request.status = "approved"
    request.updated_at = moment.isoformat()
    store.request_file(request_id).write_text(
        json.dumps(request.to_dict(), indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )

    sha = commit_approval(paths, request_id=request_id, action="recipe")

    entry: dict[str, Any] = {
        "request_id": request_id,
        "decision": "approve",
        "operator_label": operator_label,
        "rationale": rationale,
        "timestamp": moment.isoformat(),
        "managed_commit": sha,
        "target_recipes": list(request.target_recipes),
    }
    append_decision(paths, entry)
    return entry
