"""Governed HTTP GET for one public web page (CONN-WEBARCHIVER-WEB-SOURCE-R001).

Requests go through the SDK's governed async client with egress pinning, so a
URL that resolves into private address space is refused before any byte is
sent. Redirects are followed by hand, one hop at a time, so every hop is
re-checked against robots.txt, the rate limiter and the egress policy.
"""

from __future__ import annotations

import datetime as _dt
from dataclasses import dataclass, field
from urllib.parse import urljoin, urlsplit

import httpx
from agent_connector_sdk.http.client import create_async_http_client
from agent_connector_sdk.http.egress import EgressPolicyError, PinnedEgressViolation
from agent_connector_sdk.http.options import HttpClientOptions
from agent_connector_sdk.http.retry import RetryPolicy
from pydantic import BaseModel, ConfigDict

from .policy import (
    DomainRateLimiter,
    FetchPolicy,
    PolicyRefused,
    RobotsCache,
    origin_of,
)

__all__ = ["FetchedResponse", "Fetcher"]

_REDIRECTS = frozenset({301, 302, 303, 307, 308})


class FetchedResponse(BaseModel):
    """One fetched response, bounded by :class:`FetchPolicy`."""

    model_config = ConfigDict(frozen=True, extra="forbid")

    url: str
    final_url: str
    status: int
    content_type: str
    text: str
    bytes: int
    fetched_at: str
    etag: str = ""
    last_modified: str = ""


@dataclass
class Fetcher:
    """Fetch pages under one policy; robots and rate state live per instance."""

    policy: FetchPolicy = field(default_factory=FetchPolicy)
    allow_loopback: bool = False
    allowed_private_hosts: tuple[str, ...] = ()
    transport: httpx.AsyncBaseTransport | None = None
    limiter: DomainRateLimiter = field(init=False)
    robots: RobotsCache = field(init=False)

    def __post_init__(self) -> None:
        self.limiter = DomainRateLimiter(self.policy.min_interval_s)
        self.robots = RobotsCache(self._load_robots)

    def _options(self, origin: str) -> HttpClientOptions:
        return HttpClientOptions(
            base_url=origin,
            timeout=self.policy.timeout_s,
            retry=RetryPolicy(max_attempts=1),
            headers={
                "User-Agent": self.policy.user_agent,
                "Accept": "text/html,application/xhtml+xml,text/plain;q=0.9,*/*;q=0.1",
            },
            allow_plaintext=True,
            pin_egress=self.transport is None,
            allow_loopback=self.allow_loopback,
            allowed_private_hosts=self.allowed_private_hosts,
        )

    async def _get(self, url: str) -> tuple[httpx.Response, bytes]:
        origin = origin_of(url)
        await self.limiter.acquire(origin)
        parts = urlsplit(url)
        target = parts.path or "/"
        if parts.query:
            target += f"?{parts.query}"
        try:
            async with create_async_http_client(
                self._options(origin), transport=self.transport
            ) as client:
                async with client.stream("GET", target) as response:
                    declared = response.headers.get("content-length", "")
                    if declared.isdigit() and int(declared) > self.policy.max_bytes:
                        raise PolicyRefused("size_exceeded", url, f"{declared} bytes")
                    body = bytearray()
                    async for chunk in response.aiter_bytes():
                        body.extend(chunk)
                        if len(body) > self.policy.max_bytes:
                            raise PolicyRefused("size_exceeded", url)
                    return response, bytes(body)
        except PolicyRefused:
            raise
        except (EgressPolicyError, PinnedEgressViolation, ValueError) as exc:
            raise PolicyRefused("egress_denied", url, str(exc)) from exc
        except httpx.TimeoutException as exc:
            raise PolicyRefused("upstream_failed", url) from exc
        except httpx.HTTPError as exc:
            raise PolicyRefused("upstream_failed", url, type(exc).__name__) from exc

    async def _load_robots(self, robots_url: str) -> tuple[int, str]:
        response, body = await self._get(robots_url)
        return response.status_code, body.decode("utf-8", errors="replace")

    async def fetch(self, url: str) -> FetchedResponse:
        """GET ``url`` under policy, following re-checked redirects."""
        current = url
        for _ in range(self.policy.max_redirects + 1):
            if self.policy.obey_robots and not await self.robots.allowed(
                current, self.policy.user_agent
            ):
                raise PolicyRefused("robots_disallowed", current)
            response, body = await self._get(current)
            if response.status_code in _REDIRECTS and "location" in response.headers:
                current = urljoin(current, response.headers["location"])
                continue
            if response.status_code >= 400:
                raise PolicyRefused(
                    "upstream_failed", current, str(response.status_code)
                )
            content_type = response.headers.get("content-type", "")
            if not self.policy.accepts(content_type):
                raise PolicyRefused("unsupported_type", current, content_type or "none")
            encoding = response.encoding or "utf-8"
            return FetchedResponse(
                url=url,
                final_url=current,
                status=response.status_code,
                content_type=content_type,
                text=body.decode(encoding, errors="replace"),
                bytes=len(body),
                fetched_at=_dt.datetime.now(_dt.UTC).isoformat(),
                etag=response.headers.get("etag", ""),
                last_modified=response.headers.get("last-modified", ""),
            )
        raise PolicyRefused("upstream_failed", url)
