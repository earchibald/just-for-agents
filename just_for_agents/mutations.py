"""Quarantined request materialization for managed recipe mutations."""

from __future__ import annotations

import json
import shutil
from pathlib import Path

from .managed_paths import ManagedPaths
from .request_store import Request, RequestStore


class MutationError(RuntimeError):
    """Raised when a managed mutation request cannot be materialized."""


def render_candidate_recipe(
    recipe_name: str,
    command: str,
    *,
    desc: str = "",
    params: str = "",
) -> str:
    """Render one candidate managed recipe file."""

    name = recipe_name.strip()
    if not name:
        raise MutationError("recipe name cannot be empty")
    if not command:
        raise MutationError("recipe command cannot be empty")

    signature = name if not params.strip() else f"{name} {params.strip()}"
    lines: list[str] = []
    if desc:
        lines.append(f"[doc({json.dumps(f'@desc {desc}')})]")
    lines.append(f"{signature}:")
    for line in command.splitlines():
        lines.append(f"    {line}" if line else "    ")
    return "\n".join(lines) + "\n"


def approved_recipe_path(paths: ManagedPaths, recipe_name: str) -> Path:
    """Return the governed approved path for one recipe name."""

    return paths.approved_recipes_dir / f"{recipe_name}.just"


def _write_request_file(path: Path, payload: str) -> Path:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(payload, encoding="utf-8")
    return path


def create_new_request(
    paths: ManagedPaths,
    store: RequestStore,
    *,
    recipe_name: str,
    command: str,
    desc: str = "",
    params: str = "",
    author_label: str = "",
    review_notes: str = "",
) -> tuple[Request, Path]:
    """Create a quarantined manual-add request with a candidate recipe."""

    if approved_recipe_path(paths, recipe_name).exists():
        raise MutationError(f"recipe {recipe_name!r} is already approved; use edit instead")

    request = store.create(
        source="manual-add",
        target_recipes=[recipe_name],
        author_label=author_label,
        review_notes=review_notes,
    )
    candidate = store.request_dir(request.request_id) / "candidate.just"
    return request, _write_request_file(
        candidate,
        render_candidate_recipe(recipe_name, command, desc=desc, params=params),
    )


def create_edit_request(
    paths: ManagedPaths,
    store: RequestStore,
    *,
    recipe_name: str,
    author_label: str = "",
    review_notes: str = "",
) -> tuple[Request, Path]:
    """Create a quarantined manual-edit request from approved state."""

    approved = approved_recipe_path(paths, recipe_name)
    if not approved.is_file():
        raise MutationError(f"recipe {recipe_name!r} is not approved; cannot edit it")

    request = store.create(
        source="manual-edit",
        target_recipes=[recipe_name],
        author_label=author_label,
        review_notes=review_notes,
    )
    candidate = store.request_dir(request.request_id) / "candidate.just"
    shutil.copyfile(approved, candidate)
    return request, candidate


def create_delete_request(
    paths: ManagedPaths,
    store: RequestStore,
    *,
    recipe_name: str,
    author_label: str = "",
    review_notes: str = "",
) -> tuple[Request, Path]:
    """Create a quarantined manual-delete tombstone request."""

    approved = approved_recipe_path(paths, recipe_name)
    if not approved.is_file():
        raise MutationError(f"recipe {recipe_name!r} is not approved; cannot delete it")

    request = store.create(
        source="manual-delete",
        target_recipes=[recipe_name],
        author_label=author_label,
        review_notes=review_notes,
    )
    tombstone = store.request_dir(request.request_id) / "tombstone.json"
    return request, _write_request_file(
        tombstone,
        json.dumps(
            {
                "action": "delete",
                "recipe_name": recipe_name,
                "approved_path": approved.name,
            },
            indent=2,
            sort_keys=True,
        )
        + "\n",
    )
