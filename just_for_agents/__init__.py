"""just-for-agents support package.

Hosts helpers for the managed recipe governance overlay: filesystem layout
(`managed_paths`) and quarantined change-request persistence (`request_store`).
"""

from .history import (
    ApprovalError,
    append_decision,
    approve_request,
    commit_approval,
    ensure_managed_repo,
)
from .managed_paths import ManagedPaths, ensure_managed_layout
from .projection import render_include, write_include
from .request_store import Request, RequestStore

__all__ = [
    "ApprovalError",
    "ManagedPaths",
    "Request",
    "RequestStore",
    "append_decision",
    "approve_request",
    "commit_approval",
    "ensure_managed_layout",
    "ensure_managed_repo",
    "render_include",
    "write_include",
]
