"""just-for-agents support package.

Hosts helpers for the managed recipe governance overlay: filesystem layout
(`managed_paths`), quarantined change-request persistence (`request_store`),
manual mutation staging (`mutations`), and approval/projection helpers.
"""

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

__all__ = [
    "ApprovalError",
    "ManagedPaths",
    "MutationError",
    "Request",
    "RequestStore",
    "approved_recipe_path",
    "append_decision",
    "approve_request",
    "commit_approval",
    "create_delete_request",
    "create_edit_request",
    "create_new_request",
    "ensure_managed_layout",
    "ensure_managed_repo",
    "render_candidate_recipe",
    "render_include",
    "write_include",
]
