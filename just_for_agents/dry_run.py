"""Dry-run execution for quarantined managed recipe requests."""

from __future__ import annotations

import json
import os
import shlex
import subprocess
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from .managed_paths import ManagedPaths
from .request_store import Request, RequestStore, RequestValidationError


class DryRunError(RuntimeError):
    """Raised when a managed request dry-run cannot be completed."""


def dry_run_dir(paths: ManagedPaths, request_id: str) -> Path:
    """Return the artifact directory for one request's dry-run output."""

    return paths.quarantine_requests_dir / request_id / "dry-run"


def dry_run_result_file(paths: ManagedPaths, request_id: str) -> Path:
    """Return the JSON result file for one request's dry-run output."""

    return dry_run_dir(paths, request_id) / "result.json"


def load_dry_run_result(paths: ManagedPaths, request_id: str) -> dict[str, Any] | None:
    """Load one request's dry-run result payload if it exists."""

    result_file = dry_run_result_file(paths, request_id)
    if not result_file.is_file():
        return None
    return json.loads(result_file.read_text(encoding="utf-8"))


def _relative_import(from_dir: Path, target: Path) -> str:
    return Path(os.path.relpath(target, start=from_dir)).as_posix()


def _candidate_file(paths: ManagedPaths, request: Request) -> Path:
    return paths.quarantine_requests_dir / request.request_id / "candidate.just"


def _tombstone_file(paths: ManagedPaths, request: Request) -> Path:
    return paths.quarantine_requests_dir / request.request_id / "tombstone.json"


def _strip_managed_include(root_justfile: Path) -> str:
    source = root_justfile.read_text(encoding="utf-8")
    filtered = [
        line
        for line in source.splitlines()
        if "managed/approved/includes/managed.just" not in line
    ]
    return "\n".join(filtered) + ("\n" if source.endswith("\n") else "")


def _approved_recipe_imports(paths: ManagedPaths, excluded: set[str]) -> list[Path]:
    return [
        recipe
        for recipe in sorted(paths.approved_recipes_dir.glob("*.just"))
        if recipe.stem not in excluded
    ]


def _write_session_justfile(paths: ManagedPaths, request: Request, target_dir: Path) -> tuple[Path, Path]:
    root_copy = target_dir / "root.just"
    root_copy.write_text(_strip_managed_include(paths.repo_root / "Justfile"), encoding="utf-8")

    session_justfile = target_dir / "session.just"
    lines = [f'import "{root_copy.name}"']
    for recipe in _approved_recipe_imports(paths, set(request.target_recipes)):
        lines.append(f'import "{_relative_import(target_dir, recipe)}"')

    candidate = _candidate_file(paths, request)
    if candidate.is_file():
        lines.append(f'import "{_relative_import(target_dir, candidate)}"')

    session_justfile.write_text("\n".join(lines) + "\n", encoding="utf-8")
    return root_copy, session_justfile


def _run_just_dry_run(paths: ManagedPaths, session_justfile: Path, recipe_name: str) -> dict[str, Any]:
    command = [
        "just",
        "--one",
        "--working-directory",
        str(paths.repo_root),
        "--justfile",
        str(session_justfile),
        "--dry-run",
        recipe_name,
    ]
    result = subprocess.run(command, capture_output=True, text=True, check=False)
    status = "passed" if result.returncode == 0 else "failed"
    preview = result.stdout + result.stderr
    return {
        "recipe_name": recipe_name,
        "status": status,
        "exit_code": result.returncode,
        "command": shlex.join(command),
        "preview": preview,
        "stdout": result.stdout,
        "stderr": result.stderr,
    }


def _skipped_recipe_result(recipe_name: str, reason: str) -> dict[str, Any]:
    return {
        "recipe_name": recipe_name,
        "status": "skipped",
        "exit_code": 0,
        "command": "",
        "preview": "",
        "stdout": "",
        "stderr": "",
        "reason": reason,
    }


def _summarize_recipe_result(result: dict[str, Any]) -> str:
    recipe_name = result["recipe_name"]
    status = result["status"]
    if status == "passed":
        return recipe_name
    if status == "failed":
        return f"{recipe_name} (exit {result['exit_code']})"
    return f"{recipe_name} ({result.get('reason', 'skipped')})"


def _build_summary(recipe_results: list[dict[str, Any]]) -> tuple[str, str]:
    if any(result["status"] == "failed" for result in recipe_results):
        failed = ", ".join(
            _summarize_recipe_result(result)
            for result in recipe_results
            if result["status"] == "failed"
        )
        return "failed", f"dry-run failed for {failed}"

    if recipe_results and all(result["status"] == "skipped" for result in recipe_results):
        skipped = ", ".join(_summarize_recipe_result(result) for result in recipe_results)
        return "skipped", f"dry-run skipped for {skipped}"

    passed = ", ".join(
        _summarize_recipe_result(result)
        for result in recipe_results
        if result["status"] == "passed"
    )
    return "passed", f"dry-run passed for {passed}"


def _aggregate_stream(recipe_results: list[dict[str, Any]], key: str) -> str:
    blocks: list[str] = []
    for result in recipe_results:
        value = result.get(key, "")
        if not value:
            continue
        header = f"$ {result['command']}" if result.get("command") else result["recipe_name"]
        blocks.append(f"{header}\n{value.rstrip()}")
    return ("\n\n".join(blocks) + "\n") if blocks else ""


def run_request_dry_run(
    paths: ManagedPaths,
    store: RequestStore,
    request_id: str,
    *,
    now: datetime | None = None,
) -> dict[str, Any]:
    """Run and persist a dry-run preview for one quarantined request."""

    try:
        request = store.get(request_id)
    except RequestValidationError as exc:
        raise DryRunError(str(exc)) from exc
    if request is None:
        raise DryRunError(f"unknown request: {request_id}")
    if request.status != "quarantined":
        raise DryRunError(
            f"request {request_id} is {request.status!r}; only quarantined requests support dry-run"
        )
    if not request.target_recipes:
        raise DryRunError(f"request {request_id} has no target_recipes to dry-run")

    dry_run_root = dry_run_dir(paths, request_id)
    dry_run_root.mkdir(parents=True, exist_ok=True)

    candidate = _candidate_file(paths, request)
    tombstone = _tombstone_file(paths, request)
    root_copy: Path | None = None
    session_justfile: Path | None = None

    if candidate.is_file():
        root_copy, session_justfile = _write_session_justfile(paths, request, dry_run_root)
        recipe_name = request.target_recipes[0]
        recipe_results = [_run_just_dry_run(paths, session_justfile, recipe_name)]
    elif tombstone.is_file():
        recipe_name = request.target_recipes[0]
        recipe_results = [
            _skipped_recipe_result(
                recipe_name,
                "delete request has no candidate recipe body",
            )
        ]
    else:
        raise DryRunError(
            f"request {request_id} has neither candidate.just nor tombstone.json to review"
        )

    status, summary = _build_summary(recipe_results)
    stdout_text = _aggregate_stream(recipe_results, "stdout")
    stderr_text = _aggregate_stream(recipe_results, "stderr")
    preview_text = _aggregate_stream(recipe_results, "preview")
    preview_path = dry_run_root / "preview.txt"
    stdout_path = dry_run_root / "stdout.txt"
    stderr_path = dry_run_root / "stderr.txt"
    preview_path.write_text(preview_text, encoding="utf-8")
    stdout_path.write_text(stdout_text, encoding="utf-8")
    stderr_path.write_text(stderr_text, encoding="utf-8")

    moment = (now or datetime.now(timezone.utc)).replace(microsecond=0)
    payload: dict[str, Any] = {
        "request_id": request_id,
        "generated_at": moment.isoformat(),
        "status": status,
        "summary": summary,
        "dry_run_dir": str(dry_run_root),
        "result_path": str(dry_run_result_file(paths, request_id)),
        "preview_path": str(preview_path),
        "stdout_path": str(stdout_path),
        "stderr_path": str(stderr_path),
        "root_justfile_path": str(root_copy) if root_copy else "",
        "session_justfile_path": str(session_justfile) if session_justfile else "",
        "recipe_results": recipe_results,
    }
    dry_run_result_file(paths, request_id).write_text(
        json.dumps(payload, indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )

    request.dry_run_summary = summary
    request.updated_at = moment.isoformat()
    store.save(request)
    return payload
