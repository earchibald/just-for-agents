"""Persistence for quarantined managed-recipe change requests.

A request is a single proposed mutation to the approved recipe footprint. It
lives under ``quarantine/requests/<request_id>/`` until an operator approves,
rejects, or supersedes it. This module owns request creation, listing, and
retrieval; it does not implement approval or projection — those land in
follow-up issues (JFA-82+).
"""

from __future__ import annotations

import json
from dataclasses import asdict, dataclass, field
from datetime import datetime, timezone
from pathlib import Path
from typing import Iterable

from .managed_paths import ManagedPaths

VALID_SOURCES = frozenset(
    {"escalation", "manual-add", "manual-edit", "manual-delete", "drift-import"}
)
VALID_STATUSES = frozenset({"quarantined", "approved", "rejected", "superseded"})


class RequestValidationError(ValueError):
    """Raised when a request payload violates the managed single-recipe contract."""


def _normalize_target_recipes(target_recipes: Iterable[str]) -> list[str]:
    if isinstance(target_recipes, str):
        raise RequestValidationError("target_recipes must be a list of recipe names")

    recipes = [recipe.strip() for recipe in target_recipes]
    if len(recipes) != 1:
        raise RequestValidationError(
            "managed requests must target exactly one recipe"
        )

    recipe_name = recipes[0]
    if not recipe_name:
        raise RequestValidationError("recipe name cannot be empty")
    if any(char.isspace() for char in recipe_name):
        raise RequestValidationError(
            f"recipe name must be one token, got {recipe_name!r}"
        )
    return [recipe_name]


@dataclass
class Request:
    """A single change request."""

    request_id: str
    source: str
    status: str
    created_at: str
    updated_at: str
    target_recipes: list[str]
    author_label: str = ""
    review_notes: str = ""
    risk_flags: list[str] = field(default_factory=list)
    dry_run_summary: str = ""

    def to_dict(self) -> dict:
        return asdict(self)

    @classmethod
    def from_dict(cls, data: dict) -> "Request":
        try:
            request_id = data["request_id"]
            source = data["source"]
            status = data["status"]
            created_at = data["created_at"]
            updated_at = data["updated_at"]
        except KeyError as exc:
            raise RequestValidationError(
                f"request payload is missing required field {exc.args[0]!r}"
            ) from exc

        if source not in VALID_SOURCES:
            raise RequestValidationError(
                f"unknown request source: {source!r} (expected one of {sorted(VALID_SOURCES)})"
            )
        if status not in VALID_STATUSES:
            raise RequestValidationError(
                f"unknown request status: {status!r} (expected one of {sorted(VALID_STATUSES)})"
            )

        return cls(
            request_id=request_id,
            source=source,
            status=status,
            created_at=created_at,
            updated_at=updated_at,
            target_recipes=_normalize_target_recipes(data.get("target_recipes", [])),
            author_label=data.get("author_label", ""),
            review_notes=data.get("review_notes", ""),
            risk_flags=list(data.get("risk_flags", [])),
            dry_run_summary=data.get("dry_run_summary", ""),
        )


class RequestStore:
    """Reads and writes quarantined requests under a :class:`ManagedPaths` root."""

    def __init__(self, paths: ManagedPaths) -> None:
        self._paths = paths

    @property
    def paths(self) -> ManagedPaths:
        return self._paths

    def request_dir(self, request_id: str) -> Path:
        return self._paths.quarantine_requests_dir / request_id

    def request_file(self, request_id: str) -> Path:
        return self.request_dir(request_id) / "request.json"

    def save(self, request: Request) -> Request:
        """Persist a request object back to disk."""

        validated = Request.from_dict(request.to_dict())
        directory = self.request_dir(request.request_id)
        directory.mkdir(parents=True, exist_ok=True)
        self.request_file(request.request_id).write_text(
            json.dumps(validated.to_dict(), indent=2, sort_keys=True) + "\n",
            encoding="utf-8",
        )
        return validated

    def create(
        self,
        *,
        source: str,
        target_recipes: Iterable[str],
        author_label: str = "",
        review_notes: str = "",
        risk_flags: Iterable[str] | None = None,
        now: datetime | None = None,
    ) -> Request:
        if source not in VALID_SOURCES:
            raise ValueError(
                f"unknown request source: {source!r} (expected one of {sorted(VALID_SOURCES)})"
            )

        moment = (now or datetime.now(timezone.utc)).replace(microsecond=0)
        request_id = self._allocate_request_id(moment)
        request = Request(
            request_id=request_id,
            source=source,
            status="quarantined",
            created_at=moment.isoformat(),
            updated_at=moment.isoformat(),
            target_recipes=_normalize_target_recipes(target_recipes),
            author_label=author_label,
            review_notes=review_notes,
            risk_flags=list(risk_flags or []),
            dry_run_summary="",
        )

        directory = self.request_dir(request_id)
        directory.mkdir(parents=True, exist_ok=False)
        return self.save(request)

    def get(self, request_id: str) -> Request | None:
        path = self.request_file(request_id)
        if not path.exists():
            return None
        return Request.from_dict(json.loads(path.read_text(encoding="utf-8")))

    def list_quarantined(self) -> list[Request]:
        root = self._paths.quarantine_requests_dir
        if not root.exists():
            return []
        out: list[Request] = []
        for child in sorted(root.iterdir()):
            request_path = child / "request.json"
            if not request_path.exists():
                continue
            request = Request.from_dict(json.loads(request_path.read_text(encoding="utf-8")))
            if request.status == "quarantined":
                out.append(request)
        return out

    def _allocate_request_id(self, moment: datetime) -> str:
        date_part = moment.strftime("%Y%m%d")
        prefix = f"req-{date_part}-"
        existing = (
            child.name
            for child in self._paths.quarantine_requests_dir.glob(f"{prefix}*")
            if child.is_dir()
        )
        used = 0
        for name in existing:
            tail = name[len(prefix):]
            if tail.isdigit():
                used = max(used, int(tail))
        return f"{prefix}{used + 1:03d}"
