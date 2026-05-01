"""Drift detection for the managed-history-backed approved surface.

Only the approved recipe footprint counts as governed drift state:
``approved/recipes/*.just`` plus the generated ``approved/includes/managed.just``.
Quarantine requests, the decision ledger, operator dashboards, and config
remain outside this signal so normal review work does not look like drift.
"""

from __future__ import annotations

import subprocess
from dataclasses import dataclass
from pathlib import Path

from .managed_paths import ManagedPaths
from .projection import render_include

_GOVERNED_PATHS = ("approved",)


@dataclass(frozen=True)
class ManagedSurfaceStatus:
    """Status of the governed managed approved surface."""

    status: str
    summary: str
    details: tuple[str, ...] = ()
    changed_paths: tuple[str, ...] = ()

    @property
    def has_drift(self) -> bool:
        return self.status == "drifted"

    def to_dict(self) -> dict[str, object]:
        return {
            "status": self.status,
            "summary": self.summary,
            "details": list(self.details),
            "changed_paths": list(self.changed_paths),
        }


class ManagedDriftError(RuntimeError):
    """Raised when the governed managed surface has drifted."""


def _run_git(repo_dir: Path, *args: str) -> subprocess.CompletedProcess[str]:
    return subprocess.run(
        ["git", *args],
        cwd=repo_dir,
        check=True,
        capture_output=True,
        text=True,
    )


def _read_text(path: Path) -> str:
    if not path.is_file():
        return ""
    return path.read_text(encoding="utf-8")


def _governed_status_paths(paths: ManagedPaths) -> tuple[str, ...]:
    result = _run_git(
        paths.managed_root,
        "status",
        "--porcelain=1",
        "--untracked-files=all",
        "--",
        *_GOVERNED_PATHS,
    )
    changed: list[str] = []
    for line in result.stdout.splitlines():
        payload = line[3:].strip()
        if not payload:
            continue
        if " -> " in payload:
            changed.extend(part.strip() for part in payload.split(" -> "))
        else:
            changed.append(payload)
    return tuple(sorted(dict.fromkeys(changed)))


def _seeded_without_history(paths: ManagedPaths) -> ManagedSurfaceStatus | None:
    approved_files = sorted(
        path.relative_to(paths.managed_root).as_posix()
        for path in paths.approved_recipes_dir.glob("*.just")
        if path.is_file()
    )
    include_matches = _read_text(paths.approved_include_file) == render_include(paths)

    changed_paths = list(approved_files)
    details: list[str] = []
    if approved_files:
        details.append(
            "approved recipes exist even though the managed history repo has not been initialized"
        )
    if not include_matches:
        changed_paths.append("approved/includes/managed.just")
        details.append("approved/includes/managed.just no longer matches approved/recipes/")

    if changed_paths:
        return ManagedSurfaceStatus(
            status="drifted",
            summary=(
                "managed history drift detected: governed approved state exists "
                "outside the managed git history"
            ),
            details=tuple(details),
            changed_paths=tuple(sorted(dict.fromkeys(changed_paths))),
        )
    return None


def managed_surface_status(paths: ManagedPaths) -> ManagedSurfaceStatus:
    """Report whether the governed managed approved surface is clean, new, or drifted."""

    if not (paths.managed_root / ".git").exists():
        seeded_without_history = _seeded_without_history(paths)
        if seeded_without_history is not None:
            return seeded_without_history
        return ManagedSurfaceStatus(
            status="uninitialized",
            summary=(
                "managed history is uninitialized; bootstrap stays quarantine-first "
                "until the first approval"
            ),
        )

    try:
        changed_paths = list(_governed_status_paths(paths))
    except (subprocess.CalledProcessError, FileNotFoundError) as exc:
        return ManagedSurfaceStatus(
            status="drifted",
            summary=(
                "managed history drift detected: the managed git repo is unreadable "
                "and needs repair before more approvals"
            ),
            details=(str(exc),),
        )

    if _read_text(paths.approved_include_file) != render_include(paths):
        changed_paths.append("approved/includes/managed.just")

    if changed_paths:
        return ManagedSurfaceStatus(
            status="drifted",
            summary="managed history drift detected on the governed approved surface",
            details=(
                "restore the approved files from the managed repo or import the "
                "change into a formal request before approving or re-rendering",
            ),
            changed_paths=tuple(sorted(dict.fromkeys(changed_paths))),
        )

    return ManagedSurfaceStatus(
        status="clean",
        summary="managed approved surface matches the last approved commit",
    )


def ensure_clean_managed_surface(paths: ManagedPaths) -> ManagedSurfaceStatus:
    """Raise if the governed managed surface has drifted."""

    status = managed_surface_status(paths)
    if status.has_drift:
        message = status.summary
        if status.changed_paths:
            message = f"{message}: {', '.join(status.changed_paths)}"
        raise ManagedDriftError(message)
    return status
