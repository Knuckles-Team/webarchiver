"""Bounded site crawl: discover page URLs from a seed (CONN-WEBARCHIVER-WEB-SOURCE-R001.7).

A breadth-first walk from one seed URL. Every page goes through the same
:class:`~webarchiver.api.fetcher.Fetcher` as ``web_fetch``, so robots.txt, the
per-domain rate limit, size and content-type caps and egress pinning all
apply. The crawl returns URLs only; fetching and ingesting their content is the
caller's next step (Arbora ``research.web`` with ``urls``).
"""

from __future__ import annotations

import re
from collections import deque
from dataclasses import dataclass, field
from urllib.parse import urlsplit

from pydantic import BaseModel, ConfigDict, Field

from .extraction import extract_links
from .fetcher import Fetcher
from .policy import PolicyRefused, origin_of

__all__ = ["CrawlResult", "SkippedUrl", "crawl_site"]

MAX_PAGES = 1000
MAX_DEPTH = 10
_HTML = ("text/html", "application/xhtml")


class SkippedUrl(BaseModel):
    model_config = ConfigDict(frozen=True, extra="forbid")

    url: str
    reason: str


class CrawlResult(BaseModel):
    """The pages a bounded crawl reached, in discovery order."""

    model_config = ConfigDict(frozen=True, extra="forbid")

    seed_url: str
    urls: tuple[str, ...]
    skipped: tuple[SkippedUrl, ...] = ()
    truncated: bool = False
    max_depth_reached: int = Field(ge=0)


def _compile(patterns: tuple[str, ...], url: str) -> tuple[re.Pattern[str], ...]:
    try:
        return tuple(re.compile(p) for p in patterns)
    except re.error as exc:
        raise PolicyRefused("policy_refused", url, f"bad pattern: {exc}") from exc


def _normal(url: str) -> str:
    parts = urlsplit(url)
    path = parts.path or "/"
    return parts._replace(path=path, fragment="").geturl()


def _admitted(
    url: str,
    *,
    site: str,
    same_site: bool,
    include: tuple[re.Pattern[str], ...],
    exclude: tuple[re.Pattern[str], ...],
) -> bool:
    if same_site and (urlsplit(url).hostname or "").lower() != site:
        return False
    if include and not any(p.search(url) for p in include):
        return False
    return not any(p.search(url) for p in exclude)


@dataclass
class _Walk:
    """One breadth-first crawl's frontier and results."""

    fetcher: Fetcher
    seed: str
    site: str
    same_site: bool
    include: tuple[re.Pattern[str], ...]
    exclude: tuple[re.Pattern[str], ...]
    queue: deque[tuple[str, int]] = field(default_factory=deque)
    seen: set[str] = field(default_factory=set)
    urls: list[str] = field(default_factory=list)
    skipped: list[SkippedUrl] = field(default_factory=list)
    deepest: int = 0

    def enqueue(self, url: str, depth: int) -> None:
        target = _normal(url)
        if target in self.seen:
            return
        self.seen.add(target)
        if _admitted(
            target,
            site=self.site,
            same_site=self.same_site,
            include=self.include,
            exclude=self.exclude,
        ):
            self.queue.append((target, depth))

    async def visit(self, url: str, depth: int, max_depth: int) -> None:
        try:
            fetched = await self.fetcher.fetch(url)
        except PolicyRefused as refused:
            if url == self.seed:
                raise
            self.skipped.append(SkippedUrl(url=url, reason=refused.reason))
            return
        self.urls.append(url)
        self.deepest = max(self.deepest, depth)
        if depth >= max_depth or not fetched.content_type.startswith(_HTML):
            return
        for link in extract_links(fetched.text, fetched.final_url):
            self.enqueue(link.url, depth + 1)


def _check_bounds(seed_url: str, max_pages: int, max_depth: int) -> None:
    if not 1 <= max_pages <= MAX_PAGES:
        raise PolicyRefused(
            "policy_refused", seed_url, f"max_pages must be 1..{MAX_PAGES}"
        )
    if not 0 <= max_depth <= MAX_DEPTH:
        raise PolicyRefused(
            "policy_refused", seed_url, f"max_depth must be 0..{MAX_DEPTH}"
        )
    origin_of(seed_url)


async def crawl_site(
    fetcher: Fetcher,
    seed_url: str,
    *,
    same_site: bool = True,
    max_pages: int = 100,
    max_depth: int = 2,
    include: tuple[str, ...] = (),
    exclude: tuple[str, ...] = (),
) -> CrawlResult:
    """Walk links breadth-first from ``seed_url`` within the given bounds."""
    _check_bounds(seed_url, max_pages, max_depth)
    walk = _Walk(
        fetcher=fetcher,
        seed=_normal(seed_url),
        site=(urlsplit(seed_url).hostname or "").lower(),
        same_site=same_site,
        include=_compile(include, seed_url),
        exclude=_compile(exclude, seed_url),
    )
    walk.seen.add(walk.seed)
    walk.queue.append((walk.seed, 0))
    while walk.queue and len(walk.urls) < max_pages:
        url, depth = walk.queue.popleft()
        await walk.visit(url, depth, max_depth)
    return CrawlResult(
        seed_url=seed_url,
        urls=tuple(walk.urls),
        skipped=tuple(walk.skipped),
        truncated=bool(walk.queue),
        max_depth_reached=walk.deepest,
    )
