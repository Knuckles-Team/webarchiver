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
from urllib.parse import urlsplit

from pydantic import BaseModel, ConfigDict, Field

from .extraction import extract_links
from .fetcher import Fetcher
from .policy import PolicyRefused, origin_of

__all__ = ["CrawlResult", "SkippedUrl", "crawl_site"]

MAX_PAGES = 1000
MAX_DEPTH = 10


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
    if not 1 <= max_pages <= MAX_PAGES:
        raise PolicyRefused(
            "policy_refused", seed_url, f"max_pages must be 1..{MAX_PAGES}"
        )
    if not 0 <= max_depth <= MAX_DEPTH:
        raise PolicyRefused(
            "policy_refused", seed_url, f"max_depth must be 0..{MAX_DEPTH}"
        )
    origin_of(seed_url)
    site = (urlsplit(seed_url).hostname or "").lower()
    includes, excludes = _compile(include, seed_url), _compile(exclude, seed_url)
    seed = _normal(seed_url)
    queue: deque[tuple[str, int]] = deque([(seed, 0)])
    seen = {seed}
    urls: list[str] = []
    skipped: list[SkippedUrl] = []
    deepest = 0
    while queue and len(urls) < max_pages:
        url, depth = queue.popleft()
        try:
            fetched = await fetcher.fetch(url)
        except PolicyRefused as refused:
            if url == seed:
                raise
            skipped.append(SkippedUrl(url=url, reason=refused.reason))
            continue
        urls.append(url)
        deepest = max(deepest, depth)
        if depth >= max_depth or not fetched.content_type.startswith(
            ("text/html", "application/xhtml")
        ):
            continue
        for link in extract_links(fetched.text, fetched.final_url):
            target = _normal(link.url)
            if target in seen:
                continue
            seen.add(target)
            if _admitted(
                target,
                site=site,
                same_site=same_site,
                include=includes,
                exclude=excludes,
            ):
                queue.append((target, depth + 1))
    return CrawlResult(
        seed_url=seed_url,
        urls=tuple(urls),
        skipped=tuple(skipped),
        truncated=bool(queue),
        max_depth_reached=deepest,
    )
