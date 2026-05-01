"""CLI entry point: ``python -m just_for_agents <command> [args]``.

Exposes the minimal surface needed by the root Justfile's `managed-*` recipes:

* ``bootstrap`` — materialize the managed overlay layout, idempotent.
* ``queue`` — list quarantined change requests (id, source, target recipes).
* ``inspect <request_id>`` — print one request's full JSON.
* ``new <name>`` — stage a manual-add request with a candidate recipe body.
* ``edit <name>`` — clone one approved managed recipe into quarantine.
* ``delete <name>`` — stage a tombstone request for one approved recipe.
* ``dry-run <request_id>`` — capture a quarantined recipe dry-run preview.
* ``review <request_id>`` — render one browser-ready review page.
* ``dashboard`` — print a terminal dashboard and refresh the HTML companion.
* ``render-include`` — rebuild ``approved/includes/managed.just`` from approved/recipes/.
* ``approve <request_id>`` — approve a quarantined request, project, commit, ledger.
"""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

from .dry_run import DryRunError, run_request_dry_run
from .drift import ManagedDriftError, ensure_clean_managed_surface, managed_surface_status
from .history import ApprovalError, approve_request
from .managed_paths import ensure_managed_layout
from .mutations import (
    MutationError,
    create_delete_request,
    create_edit_request,
    create_new_request,
)
from .projection import write_include
from .request_store import RequestStore
from .review import ReviewError, render_dashboard_text, write_dashboard, write_request_review


def _repo_root() -> Path:
    # The package lives at <repo>/just_for_agents/, so the parent of this
    # file's directory is the repo root regardless of CWD.
    return Path(__file__).resolve().parent.parent


def cmd_bootstrap(_args: argparse.Namespace) -> int:
    paths = ensure_managed_layout(_repo_root())
    status = managed_surface_status(paths)
    print(f"managed overlay ready at {paths.managed_root}")
    print(f"  config:    {paths.config_file}")
    print(f"  quarantine:{paths.quarantine_requests_dir}")
    print(f"  approved:  {paths.approved_recipes_dir}")
    print(f"  include:   {paths.approved_include_file}")
    print(f"  history:   {paths.decisions_log}")
    print("  posture:   quarantine-first; bootstrap only creates the governed overlay")
    print(f"  history-status: {status.status} ({status.summary})")
    return 0


def cmd_queue(_args: argparse.Namespace) -> int:
    paths = ensure_managed_layout(_repo_root())
    store = RequestStore(paths)
    requests = store.list_quarantined()
    if not requests:
        print("(no quarantined requests)")
        return 0
    for request in requests:
        targets = ",".join(request.target_recipes) or "-"
        print(
            f"{request.request_id}\t{request.status}\t{request.source}\t{targets}\t{request.created_at}"
        )
    return 0


def cmd_inspect(args: argparse.Namespace) -> int:
    paths = ensure_managed_layout(_repo_root())
    store = RequestStore(paths)
    request = store.get(args.request_id)
    if request is None:
        print(f"unknown request: {args.request_id}", file=sys.stderr)
        return 1
    print(json.dumps(request.to_dict(), indent=2, sort_keys=True))
    return 0


def _request_payload(store: RequestStore, request_id: str, artifact_path: Path, key: str) -> dict:
    request = store.get(request_id)
    if request is None:
        raise RuntimeError(f"newly created request vanished: {request_id}")
    payload = request.to_dict()
    payload["request_path"] = str(store.request_dir(request_id))
    payload[key] = str(artifact_path)
    return payload


def cmd_new(args: argparse.Namespace) -> int:
    paths = ensure_managed_layout(_repo_root())
    store = RequestStore(paths)
    try:
        request, candidate = create_new_request(
            paths,
            store,
            recipe_name=args.recipe_name,
            command=args.command,
            desc=args.desc,
            params=args.params,
            author_label=args.author,
            review_notes=args.review_notes,
        )
    except MutationError as exc:
        print(f"mutation failed: {exc}", file=sys.stderr)
        return 1
    print(json.dumps(_request_payload(store, request.request_id, candidate, "candidate_path"), indent=2, sort_keys=True))
    return 0


def cmd_edit(args: argparse.Namespace) -> int:
    paths = ensure_managed_layout(_repo_root())
    store = RequestStore(paths)
    try:
        request, candidate = create_edit_request(
            paths,
            store,
            recipe_name=args.recipe_name,
            author_label=args.author,
            review_notes=args.review_notes,
        )
    except MutationError as exc:
        print(f"mutation failed: {exc}", file=sys.stderr)
        return 1
    print(json.dumps(_request_payload(store, request.request_id, candidate, "candidate_path"), indent=2, sort_keys=True))
    return 0


def cmd_delete(args: argparse.Namespace) -> int:
    paths = ensure_managed_layout(_repo_root())
    store = RequestStore(paths)
    try:
        request, tombstone = create_delete_request(
            paths,
            store,
            recipe_name=args.recipe_name,
            author_label=args.author,
            review_notes=args.review_notes,
        )
    except MutationError as exc:
        print(f"mutation failed: {exc}", file=sys.stderr)
        return 1
    print(json.dumps(_request_payload(store, request.request_id, tombstone, "tombstone_path"), indent=2, sort_keys=True))
    return 0


def cmd_render_include(_args: argparse.Namespace) -> int:
    paths = ensure_managed_layout(_repo_root())
    try:
        ensure_clean_managed_surface(paths)
        target = write_include(paths)
    except ManagedDriftError as exc:
        print(f"render failed: {exc}", file=sys.stderr)
        return 1
    print(f"rendered {target}")
    return 0


def cmd_dry_run(args: argparse.Namespace) -> int:
    paths = ensure_managed_layout(_repo_root())
    store = RequestStore(paths)
    try:
        payload = run_request_dry_run(paths, store, args.request_id)
    except DryRunError as exc:
        print(f"dry-run failed: {exc}", file=sys.stderr)
        return 1
    print(json.dumps(payload, indent=2, sort_keys=True))
    return 0


def cmd_review(args: argparse.Namespace) -> int:
    paths = ensure_managed_layout(_repo_root())
    store = RequestStore(paths)
    try:
        payload = write_request_review(paths, store, args.request_id)
    except ReviewError as exc:
        print(f"review failed: {exc}", file=sys.stderr)
        return 1
    print(json.dumps(payload, indent=2, sort_keys=True))
    return 0


def cmd_dashboard(_args: argparse.Namespace) -> int:
    paths = ensure_managed_layout(_repo_root())
    store = RequestStore(paths)
    try:
        write_dashboard(paths, store)
        print(render_dashboard_text(paths, store), end="")
    except ReviewError as exc:
        print(f"dashboard failed: {exc}", file=sys.stderr)
        return 1
    return 0


def cmd_approve(args: argparse.Namespace) -> int:
    paths = ensure_managed_layout(_repo_root())
    store = RequestStore(paths)
    try:
        entry = approve_request(
            paths,
            store,
            args.request_id,
            operator_label=args.operator,
            rationale=args.rationale,
        )
    except ApprovalError as exc:
        print(f"approval failed: {exc}", file=sys.stderr)
        return 1
    print(json.dumps(entry, indent=2, sort_keys=True))
    return 0


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(prog="just_for_agents")
    sub = parser.add_subparsers(dest="command", required=True)

    sub.add_parser("bootstrap", help="create the managed overlay layout").set_defaults(
        func=cmd_bootstrap
    )
    sub.add_parser("queue", help="list quarantined requests").set_defaults(func=cmd_queue)
    inspect = sub.add_parser("inspect", help="print one request as JSON")
    inspect.add_argument("request_id")
    inspect.set_defaults(func=cmd_inspect)

    new = sub.add_parser("new", help="stage a manual-add request")
    new.add_argument("recipe_name")
    new.add_argument("--command", required=True, help="recipe command body")
    new.add_argument("--desc", default="", help="optional @desc doc text")
    new.add_argument("--params", default="", help="optional recipe parameter list")
    new.add_argument("--author", default="", help="operator label for the request")
    new.add_argument("--review-notes", default="", help="freeform review notes")
    new.set_defaults(func=cmd_new)

    edit = sub.add_parser("edit", help="stage a manual-edit request from approved state")
    edit.add_argument("recipe_name")
    edit.add_argument("--author", default="", help="operator label for the request")
    edit.add_argument("--review-notes", default="", help="freeform review notes")
    edit.set_defaults(func=cmd_edit)

    delete = sub.add_parser("delete", help="stage a manual-delete tombstone request")
    delete.add_argument("recipe_name")
    delete.add_argument("--author", default="", help="operator label for the request")
    delete.add_argument("--review-notes", default="", help="freeform review notes")
    delete.set_defaults(func=cmd_delete)

    dry_run = sub.add_parser(
        "dry-run",
        help="capture a quarantined dry-run preview for one request",
    )
    dry_run.add_argument("request_id")
    dry_run.set_defaults(func=cmd_dry_run)

    review = sub.add_parser("review", help="render one request review page")
    review.add_argument("request_id")
    review.set_defaults(func=cmd_review)

    sub.add_parser(
        "dashboard",
        help="render the managed operator dashboard and refresh the HTML companion",
    ).set_defaults(func=cmd_dashboard)

    sub.add_parser(
        "render-include",
        help="rebuild approved/includes/managed.just from approved/recipes/",
    ).set_defaults(func=cmd_render_include)

    approve = sub.add_parser(
        "approve",
        help="approve a quarantined request, projecting it into the live include",
    )
    approve.add_argument("request_id")
    approve.add_argument("--operator", default="", help="operator label for the ledger")
    approve.add_argument("--rationale", default="", help="approval rationale")
    approve.set_defaults(func=cmd_approve)

    args = parser.parse_args(argv)
    return args.func(args)


if __name__ == "__main__":
    raise SystemExit(main())
