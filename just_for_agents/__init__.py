"""just-for-agents support package.

Hosts helpers for the managed recipe governance overlay: filesystem layout
(`managed_paths`) and quarantined change-request persistence (`request_store`).
"""

from .managed_paths import ManagedPaths, ensure_managed_layout
from .request_store import Request, RequestStore

__all__ = [
    "ManagedPaths",
    "ensure_managed_layout",
    "Request",
    "RequestStore",
]
