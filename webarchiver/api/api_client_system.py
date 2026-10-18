"""The webarchiver operations: one public method per MCP tool.

CONN-WEBARCHIVER-WEB-SOURCE-R001. ``register_tool_surface`` turns each public
method of :class:`ApiClientSystem` into one typed tool named
``webarchiver_<method>``: ``fetch``, ``extract``, ``render``, ``screenshot``
and ``links``. All five only read the web, so each is declared ``GET`` and
served read-only. Every operation honours robots.txt and the per-domain rate
limit; a refusal is returned as a typed :class:`PolicyRefused`.
"""

from __future__ import annotations

from typing import Literal

from pydantic import BaseModel, ConfigDict

from ._support import now as _now
from ._support import read_only as _read_only
from .browser import Browser, RenderedPage, Screenshot
from .crawl import CrawlResult, crawl_site
from .extraction import ExtractedPage, PageLink, extract_links, extract_page
from .fetcher import FetchedResponse, Fetcher
from .policy import FetchPolicy, PolicyRefused, origin_of

__all__ = ["ApiClientSystem", "ExtractResult", "LinksResult"]

#: Rendered HTML returned by ``render`` is capped to keep tool results bounded.
_MAX_RENDERED_HTML = 2 * 1024 * 1024


class ExtractResult(BaseModel):
    """Extracted main content plus the provenance of how it was fetched."""

    model_config = ConfigDict(frozen=True, extra="forbid")

    backend: Literal["webarchiver"] = "webarchiver"
    fetch_mode: Literal["http", "render"]
    url: str
    final_url: str
    status: int
    content_type: str
    byte_count: int
    content_digest: str
    retrieved_at: str
    robots: Literal["allowed", "not_checked"]
    page: ExtractedPage


class LinksResult(BaseModel):
    """The outbound links of one page."""

    model_config = ConfigDict(frozen=True, extra="forbid")

    url: str
    final_url: str
    links: tuple[PageLink, ...]


class ApiClientSystem:
    """Policy-governed web fetch, extraction, rendering and screenshots."""

    def __init__(
        self,
        policy: FetchPolicy | None = None,
        *,
        allow_loopback: bool = False,
        allowed_private_hosts: tuple[str, ...] = (),
    ) -> None:
        self.policy = policy or FetchPolicy()
        self.fetcher = Fetcher(
            self.policy,
            allow_loopback=allow_loopback,
            allowed_private_hosts=allowed_private_hosts,
        )
        self.browser = Browser(allow_loopback=allow_loopback)

    async def _admit(self, url: str) -> None:
        """Robots and rate-limit admission for browser-driven operations."""
        if self.policy.obey_robots and not await self.fetcher.robots.allowed(
            url, self.policy.user_agent
        ):
            raise PolicyRefused("robots_disallowed", url)
        await self.fetcher.limiter.acquire(origin_of(url))

    @_read_only
    async def fetch(self, url: str) -> FetchedResponse:
        """GET one URL under robots.txt, rate-limit, size and content-type policy."""
        return await self.fetcher.fetch(url)

    @_read_only
    async def extract(self, url: str, render: bool = False) -> ExtractResult:
        """Fetch one URL and extract its main content as text and markdown.

        Returns title, author, published date, canonical URL and outbound
        links. ``render=True`` runs the page's scripts in headless Chromium
        first, for pages that build their content client-side.
        """
        if render:
            rendered = await self.render(url)
            page = extract_page(rendered.html, rendered.final_url)
            return ExtractResult(
                fetch_mode="render",
                url=url,
                final_url=rendered.final_url,
                status=rendered.status,
                content_type="text/html",
                byte_count=len(rendered.html.encode("utf-8")),
                content_digest=page.content_sha256,
                retrieved_at=_now(),
                robots=self._robots_decision(),
                page=page.model_copy(update={"url": url}),
            )
        fetched = await self.fetcher.fetch(url)
        page = extract_page(fetched.text, fetched.final_url)
        return ExtractResult(
            fetch_mode="http",
            url=url,
            final_url=fetched.final_url,
            status=fetched.status,
            content_type=fetched.content_type,
            byte_count=fetched.bytes,
            content_digest=page.content_sha256,
            retrieved_at=fetched.fetched_at,
            robots=self._robots_decision(),
            page=page.model_copy(update={"url": url}),
        )

    def _robots_decision(self) -> Literal["allowed", "not_checked"]:
        return "allowed" if self.policy.obey_robots else "not_checked"

    @_read_only
    async def render(self, url: str) -> RenderedPage:
        """Render one URL in ad-blocked headless Chromium and return its DOM."""
        await self._admit(url)
        rendered = await self.browser.render(url, user_agent=self.policy.user_agent)
        if len(rendered.html) > _MAX_RENDERED_HTML:
            raise PolicyRefused("size_exceeded", url, "rendered DOM")
        return rendered

    @_read_only
    async def screenshot(self, url: str, full_page: bool = True) -> Screenshot:
        """Take a PNG screenshot of one URL, the full page by default."""
        await self._admit(url)
        return await self.browser.screenshot(
            url, user_agent=self.policy.user_agent, full_page=full_page
        )

    @_read_only
    async def crawl(
        self,
        seed_url: str,
        same_site: bool = True,
        max_pages: int = 100,
        max_depth: int = 2,
        include: list[str] | None = None,
        exclude: list[str] | None = None,
    ) -> CrawlResult:
        """Discover up to ``max_pages`` (1 to 1000) page URLs from one seed.

        A breadth-first walk to ``max_depth`` (0 to 10) under the same robots,
        rate, size, type and egress policy as ``web_fetch``. ``include`` and
        ``exclude`` are regular expressions matched against each URL. Returns
        URLs only.
        """
        return await crawl_site(
            self.fetcher,
            seed_url,
            same_site=same_site,
            max_pages=max_pages,
            max_depth=max_depth,
            include=tuple(include or ()),
            exclude=tuple(exclude or ()),
        )

    @_read_only
    async def links(self, url: str, same_site_only: bool = False) -> LinksResult:
        """List the outbound http(s) links of one URL."""
        fetched = await self.fetcher.fetch(url)
        found = extract_links(fetched.text, fetched.final_url)
        if same_site_only:
            found = tuple(link for link in found if link.same_site)
        return LinksResult(url=url, final_url=fetched.final_url, links=found)

    async def _close(self) -> None:
        """Release the shared browser."""
        await self.browser.close()
