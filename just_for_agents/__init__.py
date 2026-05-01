"""just-for-agents support package.

Hosts helpers for the managed recipe governance overlay: filesystem layout
(`managed_paths`), quarantined change-request persistence (`request_store`),
manual mutation staging (`mutations`), and approval/projection helpers.
"""

from .dry_run import (
    DryRunError,
    dry_run_dir,
    dry_run_result_file,
    load_dry_run_result,
    run_request_dry_run,
)
from .history import (
    ApprovalError,
    append_decision,
    approve_request,
    commit_approval,
    ensure_managed_repo,
)
from .managed_paths import ManagedPaths, ensure_managed_layout
from .mutations import (
    MutationError,
    approved_recipe_path,
    create_delete_request,
    create_edit_request,
    create_new_request,
    render_candidate_recipe,
)
from .projection import render_include, write_include
from .request_store import Request, RequestStore
from .review import (
    ReviewError,
    dashboard_file,
    render_dashboard_text,
    request_review_file,
    write_dashboard,
    write_request_review,
)

__all__ = [
    "ApprovalError",
    "DryRunError",
    "ManagedPaths",
    "MutationError",
    "Request",
    "RequestStore",
    "ReviewError",
    "approved_recipe_path",
    "append_decision",
    "approve_request",
    "commit_approval",
    "create_delete_request",
    "create_edit_request",
    "create_new_request",
    "dashboard_file",
    "dry_run_dir",
    "dry_run_result_file",
    "ensure_managed_layout",
    "ensure_managed_repo",
    "load_dry_run_result",
    "render_candidate_recipe",
    "render_dashboard_text",
    "render_include",
    "request_review_file",
    "run_request_dry_run",
    "write_include",
    "write_dashboard",
    "write_request_review",
]
