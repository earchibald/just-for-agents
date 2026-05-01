"""CLI entry point: ``python -m just_for_agents <command> [args]``.

Exposes the minimal surface needed by the root Justfile's `managed-*` recipes:

* ``bootstrap`` — materialize the managed overlay layout, idempotent.
* ``queue`` — list quarantined change requests (id, source, target recipes).
* ``inspect <request_id>`` — print one request's full JSON.
* ``render-include`` — rebuild ``approved/includes/managed.just`` from approved/recipes/.
* ``approve <request_id>`` — approve a quarantined request, project, commit, ledger.
"""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

from .history import ApprovalError, approve_request
from .managed_paths import ensure_managed_layout
from .projection import write_include
from .request_store import RequestStore


def _repo_root() -> Path:
    # The package lives at <repo>/just_for_agents/, so the parent of this
    # file's directory is the repo root regardless of CWD.
    return Path(__file__).resolve().parent.parent


def cmd_bootstrap(_args: argparse.Namespace) -> int:
    paths = ensure_managed_layout(_repo_root())
    print(f"managed overlay ready at {paths.managed_root}")
    print(f"  config:    {paths.config_file}")
    print(f"  quarantine:{paths.quarantine_requests_dir}")
    print(f"  approved:  {paths.approved_recipes_dir}")
    print(f"  include:   {paths.approved_include_file}")
    print(f"  history:   {paths.decisions_log}")
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


def cmd_render_include(_args: argparse.Namespace) -> int:
    paths = ensure_managed_layout(_repo_root())
    target = write_include(paths)
    print(f"rendered {target}")
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
