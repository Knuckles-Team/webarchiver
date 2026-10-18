"""Fetch policy: robots.txt, per-domain rate limits, and response caps.

CONN-WEBARCHIVER-WEB-SOURCE-R001. Every network operation of this connector goes
through one :class:`FetchPolicy`. A refusal is typed (:class:`PolicyRefused`)
and carries a stable ``reason`` code so a caller can tell "the site said no"
from "the transport failed".
"""

from __future__ import annotations

import asyncio
import time
import urllib.robotparser
from collections.abc import Awaitable, Callable
from dataclasses import dataclass, field
from urllib.parse import urlsplit

__all__ = [
    "DEFAULT_CONTENT_TYPES",
    "REFUSAL_REASONS",
    "DomainRateLimiter",
    "FetchPolicy",
    "PolicyRefused",
    "RobotsCache",
    "origin_of",
]

#: Content types the fetch operation returns by default.
DEFAULT_CONTENT_TYPES = (
    "text/html",
    "application/xhtml+xml",
    "text/plain",
    "text/markdown",
    "application/xml",
    "text/xml",
)


#: The closed refusal reasons of the web-source contract.
REFUSAL_REASONS = frozenset(
    {
        "robots_disallowed",
        "rate_limited",
        "size_exceeded",
        "unsupported_type",
        "egress_denied",
        "policy_refused",
        "extract_empty",
        "upstream_failed",
    }
)


class PolicyRefused(Exception):
    """The connector refused a URL; ``reason`` is one of :data:`REFUSAL_REASONS`."""

    def __init__(self, reason: str, url: str, detail: str = "") -> None:
        if reason not in REFUSAL_REASONS:
            raise ValueError(f"unknown refusal reason {reason!r}")
        self.reason = reason
        self.url = url
        self.detail = detail
        super().__init__(f"{reason}: {url}" + (f" ({detail})" if detail else ""))


def origin_of(url: str) -> str:
    """``scheme://host[:port]`` of an absolute http(s) URL, or refuse it."""
    parts = urlsplit(url)
    if parts.scheme not in {"http", "https"} or not parts.hostname:
        raise PolicyRefused("policy_refused", url, "absolute http(s) URL required")
    if parts.username or parts.password:
        raise PolicyRefused("policy_refused", url, "credentials in URL")
    host = parts.hostname.lower()
    port = f":{parts.port}" if parts.port else ""
    return f"{parts.scheme}://{host}{port}"


@dataclass(frozen=True)
class FetchPolicy:
    """Limits applied to every fetch.

    Attributes:
        user_agent: Sent on every request, and the robots.txt agent token.
        max_bytes: Hard cap on a response body; larger bodies are refused.
        content_types: Accepted media types (parameters ignored).
        min_interval_s: Minimum spacing between requests to one origin.
        timeout_s: Per-request timeout.
        max_redirects: Redirect hops followed, each re-checked by policy.
        obey_robots: Refuse URLs robots.txt disallows for ``user_agent``.
    """

    user_agent: str = "webarchiver/1.0 (+https://github.com/Knuckles-Team/webarchiver)"
    max_bytes: int = 5 * 1024 * 1024
    content_types: tuple[str, ...] = DEFAULT_CONTENT_TYPES
    min_interval_s: float = 1.0
    timeout_s: float = 20.0
    max_redirects: int = 5
    obey_robots: bool = True

    def accepts(self, content_type: str) -> bool:
        media = content_type.split(";", 1)[0].strip().lower()
        return media in self.content_types


@dataclass
class DomainRateLimiter:
    """Space requests to one origin at least ``min_interval_s`` apart."""

    min_interval_s: float
    clock: Callable[[], float] = time.monotonic
    sleep: Callable[[float], Awaitable[None]] = asyncio.sleep
    _next: dict[str, float] = field(default_factory=dict)
    _locks: dict[str, asyncio.Lock] = field(default_factory=dict)

    async def acquire(self, origin: str) -> None:
        lock = self._locks.setdefault(origin, asyncio.Lock())
        async with lock:
            now = self.clock()
            wait = self._next.get(origin, now) - now
            if wait > 0:
                await self.sleep(wait)
                now = self.clock()
            self._next[origin] = now + self.min_interval_s


RobotsLoader = Callable[[str], Awaitable[tuple[int, str]]]


@dataclass
class RobotsCache:
    """robots.txt rules per origin, fetched once and kept for ``ttl_s``.

    A 4xx robots.txt allows everything (RFC 9309 section 2.3.1.3); a 5xx or
    transport failure disallows everything for that origin until expiry.
    """

    loader: RobotsLoader
    ttl_s: float = 3600.0
    clock: Callable[[], float] = time.monotonic
    _rules: dict[str, tuple[float, urllib.robotparser.RobotFileParser]] = field(
        default_factory=dict
    )

    async def allowed(self, url: str, user_agent: str) -> bool:
        origin = origin_of(url)
        cached = self._rules.get(origin)
        if cached is None or cached[0] < self.clock():
            parser = await self._load(origin)
            self._rules[origin] = (self.clock() + self.ttl_s, parser)
        else:
            parser = cached[1]
        return parser.can_fetch(user_agent, url)

    async def _load(self, origin: str) -> urllib.robotparser.RobotFileParser:
        parser = urllib.robotparser.RobotFileParser()
        try:
            status, body = await self.loader(f"{origin}/robots.txt")
        except PolicyRefused as refused:
            if refused.reason in {"egress_denied", "policy_refused"}:
                raise
            status, body = 503, ""
        except Exception:  # noqa: BLE001 - any transport failure is "unreachable"
            status, body = 503, ""
        if status >= 500:
            parser.disallow_all = True
        elif status >= 400:
            parser.allow_all = True
        else:
            parser.parse(body.splitlines())
        return parser
