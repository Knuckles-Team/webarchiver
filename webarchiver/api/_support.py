"""Small shared helpers for the webarchiver operations."""

from __future__ import annotations

import datetime as _dt
from typing import Any

__all__ = ["now", "read_only"]


def read_only(method: Any) -> Any:
    """Declare an operation as ``GET`` so the SDK serves it read-only."""
    method.__http_method__ = "GET"
    return method


def now() -> str:
    """The current UTC time in ISO 8601."""
    return _dt.datetime.now(_dt.UTC).isoformat()
