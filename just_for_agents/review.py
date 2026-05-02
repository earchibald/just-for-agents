"""HTML review and dashboard rendering for managed recipe requests."""

from __future__ import annotations

import difflib
import json
import tomllib
from datetime import datetime, timezone
from html import escape
from pathlib import Path
from typing import Any

from .dry_run import load_dry_run_result
from .drift import ManagedSurfaceStatus, managed_surface_status
from .managed_paths import ManagedPaths
from .request_store import Request, RequestStore, RequestValidationError


class ReviewError(RuntimeError):
    """Raised when a managed review page cannot be rendered."""


def request_review_file(paths: ManagedPaths, request_id: str) -> Path:
    """Return the request-scoped HTML review file path."""

    return paths.quarantine_requests_dir / request_id / "review.html"


def dashboard_file(paths: ManagedPaths) -> Path:
    """Return the managed operator dashboard HTML file path."""

    return paths.managed_root / "dashboard.html"


def _read_text(path: Path) -> str:
    if not path.is_file():
        return ""
    return path.read_text(encoding="utf-8")


def _decision_rows(paths: ManagedPaths) -> list[dict[str, Any]]:
    if not paths.decisions_log.is_file():
        return []
    rows: list[dict[str, Any]] = []
    for line in paths.decisions_log.read_text(encoding="utf-8").splitlines():
        if line.strip():
            rows.append(json.loads(line))
    return rows


def _latest_approval_by_recipe(paths: ManagedPaths) -> dict[str, dict[str, Any]]:
    latest: dict[str, dict[str, Any]] = {}
    for row in _decision_rows(paths):
        if row.get("decision") != "approve":
            continue
        for recipe_name in row.get("target_recipes", []):
            latest[recipe_name] = row
    return latest


def _pending_requests_by_recipe(store: RequestStore) -> dict[str, list[str]]:
    pending: dict[str, list[str]] = {}
    for request in _list_quarantined(store):
        for recipe_name in request.target_recipes:
            pending.setdefault(recipe_name, []).append(request.request_id)
    return pending


def _get_request(store: RequestStore, request_id: str) -> Request | None:
    try:
        return store.get(request_id)
    except RequestValidationError as exc:
        raise ReviewError(str(exc)) from exc


def _list_quarantined(store: RequestStore) -> list[Request]:
    try:
        return store.list_quarantined()
    except RequestValidationError as exc:
        raise ReviewError(str(exc)) from exc


def _dry_run_state(paths: ManagedPaths, request_id: str, summary: str) -> str:
    result = load_dry_run_result(paths, request_id)
    if result is not None:
        return result["status"]
    return "pending" if not summary else "recorded"


def _settings_rows(paths: ManagedPaths) -> list[tuple[str, str, str]]:
    payload = tomllib.loads(paths.config_file.read_text(encoding="utf-8"))
    rows: list[tuple[str, str, str]] = []
    for section_name in sorted(payload):
        section = payload[section_name]
        if not isinstance(section, dict):
            rows.append(("", section_name, str(section)))
            continue
        for key in sorted(section):
            rows.append((section_name, key, str(section[key])))
    return rows


def _page(title: str, body: str) -> str:
    return f"""<!DOCTYPE html>
<html lang="en">
<head>
  <meta charset="utf-8">
  <title>{escape(title)}</title>
  <style>
    body {{ font-family: -apple-system, BlinkMacSystemFont, sans-serif; margin: 2rem auto; max-width: 1100px; padding: 0 1rem; line-height: 1.5; color: #1f2933; }}
    h1, h2, h3 {{ color: #102a43; }}
    table {{ border-collapse: collapse; width: 100%; margin: 1rem 0 2rem; }}
    th, td {{ border: 1px solid #d9e2ec; padding: 0.5rem 0.75rem; text-align: left; vertical-align: top; }}
    th {{ background: #f0f4f8; }}
    pre {{ background: #f8fafc; border: 1px solid #d9e2ec; padding: 1rem; overflow-x: auto; }}
    .summary {{ background: #f0f4f8; border-left: 4px solid #486581; padding: 0.75rem 1rem; margin: 1rem 0 2rem; }}
    .status-pill {{ display: inline-block; padding: 0.15rem 0.5rem; border-radius: 999px; background: #d9e2ec; }}
    .surface-status {{ padding: 0.75rem 1rem; margin: 1rem 0 2rem; border-left: 4px solid #486581; background: #f0f4f8; }}
    .surface-status.uninitialized {{ border-left-color: #486581; }}
    .surface-status.clean {{ border-left-color: #2f855a; background: #f0fff4; }}
    .surface-status.drifted {{ border-left-color: #d69e2e; background: #fffbea; }}
    .diff {{ overflow-x: auto; }}
    .diff table {{ font-family: ui-monospace, SFMono-Regular, monospace; font-size: 0.9rem; }}
  </style>
</head>
<body>
{body}
</body>
</html>
"""


def _managed_surface_html(status: ManagedSurfaceStatus) -> str:
    details = (
        "<ul>{items}</ul>".format(
            items="".join(f"<li>{escape(detail)}</li>" for detail in status.details)
        )
        if status.details
        else ""
    )
    changed_paths = (
        "<p><strong>Changed paths:</strong></p><ul>{items}</ul>".format(
            items="".join(
                f"<li><code>{escape(path)}</code></li>" for path in status.changed_paths
            )
        )
        if status.changed_paths
        else ""
    )
    return (
        f'<div class="surface-status {escape(status.status)}">'
        f"<strong>Managed history:</strong> {escape(status.status)}<br>"
        f"{escape(status.summary)}"
        f"</div>{details}{changed_paths}"
    )


def _managed_surface_lines(status: ManagedSurfaceStatus) -> list[str]:
    lines = ["Managed history", "---------------", f"{status.status}\t{status.summary}"]
    lines.extend(status.details)
    if status.changed_paths:
        lines.append("Paths: " + ", ".join(status.changed_paths))
    return lines


def write_request_review(
    paths: ManagedPaths,
    store: RequestStore,
    request_id: str,
    *,
    now: datetime | None = None,
) -> dict[str, Any]:
    """Render and persist one request's HTML review page."""

    request = _get_request(store, request_id)
    if request is None:
        raise ReviewError(f"unknown request: {request_id}")
    surface_status = managed_surface_status(paths)

    request_dir = store.request_dir(request_id)
    review_path = request_review_file(paths, request_id)
    review_path.parent.mkdir(parents=True, exist_ok=True)
    candidate = _read_text(request_dir / "candidate.just")
    tombstone = _read_text(request_dir / "tombstone.json")
    approved_snapshots = {
        recipe_name: _read_text(paths.approved_recipes_dir / f"{recipe_name}.just")
        for recipe_name in request.target_recipes
    }
    dry_run = load_dry_run_result(paths, request_id)

    diff_html = ""
    if candidate and len(request.target_recipes) == 1:
        recipe_name = request.target_recipes[0]
        approved = approved_snapshots.get(recipe_name, "")
        if approved:
            diff_html = difflib.HtmlDiff(wrapcolumn=88).make_table(
                approved.splitlines(),
                candidate.splitlines(),
                fromdesc=f"approved/{recipe_name}.just",
                todesc="candidate.just",
                context=True,
                numlines=3,
            )

    dry_run_html = "<p>No dry-run has been recorded yet.</p>"
    if dry_run is not None:
        rows = "".join(
            f"<tr><td>{escape(result['recipe_name'])}</td><td>{escape(result['status'])}</td><td>{result['exit_code']}</td></tr>"
            for result in dry_run["recipe_results"]
        )
        details = "".join(
            "<h3>{name}</h3><p><strong>Status:</strong> {status}</p>{reason}<p><strong>Command:</strong> <code>{command}</code></p><h4>preview</h4><pre>{preview}</pre><h4>stdout</h4><pre>{stdout}</pre><h4>stderr</h4><pre>{stderr}</pre>".format(
                name=escape(result["recipe_name"]),
                status=escape(result["status"]),
                reason=(
                    f"<p><strong>Reason:</strong> {escape(result['reason'])}</p>"
                    if result.get("reason")
                    else ""
                ),
                command=escape(result.get("command", "")),
                preview=escape(result.get("preview", "")),
                stdout=escape(result.get("stdout", "")),
                stderr=escape(result.get("stderr", "")),
            )
            for result in dry_run["recipe_results"]
        )
        dry_run_html = (
            f"<div class=\"summary\"><strong>{escape(dry_run['summary'])}</strong><br>"
            f"Generated at {escape(dry_run['generated_at'])}</div>"
            f"<table><thead><tr><th>Recipe</th><th>Status</th><th>Exit</th></tr></thead><tbody>{rows}</tbody></table>"
            f"{details}"
        )

    approved_blocks = "".join(
        f"<h3>{escape(recipe_name)}</h3><pre>{escape(body or '(not currently approved)')}</pre>"
        for recipe_name, body in approved_snapshots.items()
    )
    body = f"""
<h1>Managed request review: {escape(request_id)}</h1>
<div class="summary">
  <strong>Status:</strong> <span class="status-pill">{escape(request.status)}</span><br>
  <strong>Targets:</strong> {escape(', '.join(request.target_recipes) or '-')}<br>
  <strong>Source:</strong> {escape(request.source)}<br>
  <strong>Dry-run summary:</strong> {escape(request.dry_run_summary or 'pending')}
</div>

<h2>Metadata</h2>
<table>
  <tbody>
    <tr><th>Request ID</th><td>{escape(request.request_id)}</td></tr>
    <tr><th>Author</th><td>{escape(request.author_label or '-')}</td></tr>
    <tr><th>Created</th><td>{escape(request.created_at)}</td></tr>
    <tr><th>Updated</th><td>{escape(request.updated_at)}</td></tr>
    <tr><th>Review notes</th><td>{escape(request.review_notes or '-')}</td></tr>
    <tr><th>Risk flags</th><td>{escape(', '.join(request.risk_flags) or '-')}</td></tr>
  </tbody>
</table>

<h2>Managed history</h2>
{_managed_surface_html(surface_status)}

<h2>Candidate artifact</h2>
<pre>{escape(candidate or tombstone or '(no candidate artifact recorded)')}</pre>

<h2>Approved state</h2>
{approved_blocks}

<h2>Diff</h2>
{f'<div class="diff">{diff_html}</div>' if diff_html else '<p>No side-by-side diff is available for this request.</p>'}

<h2>Dry-run</h2>
{dry_run_html}
"""
    review_path.write_text(
        _page(f"Managed request review {request_id}", body),
        encoding="utf-8",
    )
    moment = (now or datetime.now(timezone.utc)).replace(microsecond=0)
    return {
        "request_id": request_id,
        "review_path": str(review_path),
        "generated_at": moment.isoformat(),
        "managed_surface": surface_status.to_dict(),
        "dry_run_result_path": (
            str((request_dir / "dry-run" / "result.json"))
            if (request_dir / "dry-run" / "result.json").is_file()
            else ""
        ),
    }


def render_dashboard_text(paths: ManagedPaths, store: RequestStore) -> str:
    """Render the terminal-oriented managed operator dashboard summary."""

    surface_status = managed_surface_status(paths)
    queue_rows = [
        (
            request.request_id,
            request.source,
            ",".join(request.target_recipes) or "-",
            _dry_run_state(paths, request.request_id, request.dry_run_summary),
            request.dry_run_summary or "-",
        )
        for request in _list_quarantined(store)
    ]
    approvals = _latest_approval_by_recipe(paths)
    pending_by_recipe = _pending_requests_by_recipe(store)
    library_rows = []
    for recipe in sorted(paths.approved_recipes_dir.glob("*.just")):
        latest = approvals.get(recipe.stem, {})
        library_rows.append(
            (
                recipe.stem,
                latest.get("request_id", "-"),
                latest.get("managed_commit", "-"),
                ",".join(pending_by_recipe.get(recipe.stem, [])) or "-",
            )
        )

    lines = _managed_surface_lines(surface_status) + ["", "Queue", "-----"]
    if queue_rows:
        lines.extend(
            f"{request_id}\t{source}\t{targets}\t{dry_run_state}\t{summary}"
            for request_id, source, targets, dry_run_state, summary in queue_rows
        )
    else:
        lines.append("(no quarantined requests)")

    lines.extend(["", "Library", "-------"])
    if library_rows:
        lines.extend(
            f"{name}\tlatest={request_id}\tcommit={commit}\tpending={pending}"
            for name, request_id, commit, pending in library_rows
        )
    else:
        lines.append("(no approved managed recipes)")

    lines.extend(["", "Settings", "--------"])
    settings = _settings_rows(paths)
    if settings:
        lines.extend(
            f"[{section}] {key} = {value}" if section else f"{key} = {value}"
            for section, key, value in settings
        )
    else:
        lines.append("(no settings)")

    lines.extend(["", f"HTML: {dashboard_file(paths)}"])
    return "\n".join(lines) + "\n"


def write_dashboard(
    paths: ManagedPaths,
    store: RequestStore,
    *,
    now: datetime | None = None,
) -> dict[str, Any]:
    """Render and persist the operator dashboard HTML companion."""

    surface_status = managed_surface_status(paths)
    queue_rows = [
        (
            request.request_id,
            request.source,
            ",".join(request.target_recipes) or "-",
            _dry_run_state(paths, request.request_id, request.dry_run_summary),
            request.dry_run_summary or "-",
        )
        for request in _list_quarantined(store)
    ]
    approvals = _latest_approval_by_recipe(paths)
    pending_by_recipe = _pending_requests_by_recipe(store)
    library_rows = []
    for recipe in sorted(paths.approved_recipes_dir.glob("*.just")):
        latest = approvals.get(recipe.stem, {})
        library_rows.append(
            (
                recipe.stem,
                latest.get("request_id", "-"),
                latest.get("managed_commit", "-"),
                ",".join(pending_by_recipe.get(recipe.stem, [])) or "-",
            )
        )

    queue_table = (
        "".join(
            f"<tr><td>{escape(request_id)}</td><td>{escape(source)}</td><td>{escape(targets)}</td><td>{escape(dry_run_state)}</td><td>{escape(summary)}</td></tr>"
            for request_id, source, targets, dry_run_state, summary in queue_rows
        )
        or "<tr><td colspan=\"5\">(no quarantined requests)</td></tr>"
    )
    library_table = (
        "".join(
            f"<tr><td>{escape(name)}</td><td>{escape(request_id)}</td><td>{escape(commit)}</td><td>{escape(pending)}</td></tr>"
            for name, request_id, commit, pending in library_rows
        )
        or "<tr><td colspan=\"4\">(no approved managed recipes)</td></tr>"
    )
    settings_table = (
        "".join(
            f"<tr><td>{escape(section or '-')}</td><td>{escape(key)}</td><td>{escape(value)}</td></tr>"
            for section, key, value in _settings_rows(paths)
        )
        or "<tr><td colspan=\"3\">(no settings)</td></tr>"
    )
    body = f"""
<h1>Managed operator dashboard</h1>
<div class="summary">Queue/library/settings snapshot for the managed recipe governance overlay.</div>

<h2>Managed history</h2>
{_managed_surface_html(surface_status)}

<h2>Queue</h2>
<table>
  <thead><tr><th>Request</th><th>Source</th><th>Targets</th><th>Dry-run</th><th>Summary</th></tr></thead>
  <tbody>{queue_table}</tbody>
</table>

<h2>Library</h2>
<table>
  <thead><tr><th>Recipe</th><th>Latest approval</th><th>Managed commit</th><th>Pending requests</th></tr></thead>
  <tbody>{library_table}</tbody>
</table>

<h2>Settings</h2>
<table>
  <thead><tr><th>Section</th><th>Key</th><th>Value</th></tr></thead>
  <tbody>{settings_table}</tbody>
</table>
"""
    target = dashboard_file(paths)
    target.write_text(_page("Managed operator dashboard", body), encoding="utf-8")
    moment = (now or datetime.now(timezone.utc)).replace(microsecond=0)
    return {
        "dashboard_path": str(target),
        "generated_at": moment.isoformat(),
        "managed_surface": surface_status.to_dict(),
        "queue_count": len(queue_rows),
        "approved_recipe_count": len(library_rows),
    }
