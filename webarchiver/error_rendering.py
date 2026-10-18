"""Negotiate and render canonical problems without changing their metadata."""

from __future__ import annotations

from collections.abc import Mapping
from dataclasses import dataclass
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from .error_authority import ProblemDetails


PROBLEM_JSON_MEDIA_TYPE = "application/problem+json"
STRUCTURED_MARKDOWN_MEDIA_TYPE = "text/markdown"
BROWSER_HTML_MEDIA_TYPE = "text/html"
AGENT_ERROR_ACCEPT = (
    f"{PROBLEM_JSON_MEDIA_TYPE}, "
    f"{STRUCTURED_MARKDOWN_MEDIA_TYPE};q=0.9, "
    f"{BROWSER_HTML_MEDIA_TYPE};q=0.5"
)


@dataclass(frozen=True)
class RenderedError:
    """A transport-neutral response ready for an HTTP/MCP adapter."""

    status_code: int
    media_type: str
    body: str
    headers: Mapping[str, str]


def _quality(parameters: list[str]) -> float | None:
    """Read one bounded q value; preserve the default for malformed parameters."""
    try:
        quality = next(
            float(part.split("=", 1)[1].strip())
            for part in parameters
            if part.lower().startswith("q=")
        )
    except (StopIteration, ValueError):
        quality = 1.0
    return quality if 0.0 <= quality <= 1.0 else None


def _specificity(token: str, offered: str) -> int:
    if token == offered:
        return 2
    return 1 if token in {"*/*", offered.split("/", 1)[0] + "/*"} else -1


def _accept_quality(accept: str, offered: str) -> tuple[float, int, int]:
    """Return q, specificity, and source order for one offered media type."""
    best_match = (-1, 0.0, -10_000)
    for order, item in enumerate(accept.split(",")):
        bits = [part.strip() for part in item.split(";")]
        quality = _quality(bits[1:])
        specificity = _specificity(bits[0].lower(), offered)
        if quality is not None and specificity >= 0:
            best_match = max(best_match, (specificity, quality, -order))
    specificity, quality, source_order = best_match
    return quality, specificity, source_order


def negotiate_media_type(accept: str | None) -> str:
    """Prefer agent formats, while retaining HTML for browser Accept headers."""
    if not accept or not accept.strip():
        return PROBLEM_JSON_MEDIA_TYPE
    offered = (
        PROBLEM_JSON_MEDIA_TYPE,
        STRUCTURED_MARKDOWN_MEDIA_TYPE,
        BROWSER_HTML_MEDIA_TYPE,
    )
    ranked = [
        (*_accept_quality(accept, media_type), -priority, media_type)
        for priority, media_type in enumerate(offered)
    ]
    supported = [candidate for candidate in ranked if candidate[0] > 0]
    return max(supported)[-1] if supported else PROBLEM_JSON_MEDIA_TYPE


def render_error(
    problem: ProblemDetails, *, accept: str | None = None
) -> RenderedError:
    """Negotiate one bounded representation without changing its semantics."""
    media_type = negotiate_media_type(accept)
    if media_type == STRUCTURED_MARKDOWN_MEDIA_TYPE:
        body = problem.to_markdown()
    elif media_type == BROWSER_HTML_MEDIA_TYPE:
        body = problem.to_html()
    else:
        media_type = PROBLEM_JSON_MEDIA_TYPE
        body = problem.to_json()
    headers = {
        "Content-Type": f"{media_type}; charset=utf-8",
        "Vary": "Accept",
    }
    if problem.retry_after_s is not None:
        headers["Retry-After"] = str(problem.retry_after_s)
    return RenderedError(
        status_code=problem.status,
        media_type=media_type,
        body=body,
        headers=headers,
    )
