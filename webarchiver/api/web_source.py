"""webarchiver's implementation of the SDK web-source contract.

CONN-WEBARCHIVER-WEB-SOURCE-R001.1. ``web_fetch`` and ``web_extract`` are served
by :func:`scion_sdk.ports.web_source.register_web_source_tools` over
:class:`WebarchiverSource`, so their names, schemas, refusal reasons and output
shape are the contract's, identical to every other page connector's. The page
is fetched natively (governed httpx client) and its main content extracted
with trafilatura; ``backend`` is ``webarchiver``.
"""

from __future__ import annotations

from scion_sdk.ports.web_source import (
    WebFetchRequest,
    WebOutboundLink,
    WebPageResult,
    WebSourceRefused,
    content_digest,
)

from .extraction import extract_page
from .fetcher import FetchedResponse, Fetcher
from .policy import PolicyRefused

__all__ = ["BACKEND", "WebarchiverSource"]

#: The connector named in every page's provenance.
BACKEND = "webarchiver"


class WebarchiverSource:
    """Fetch and extract pages under the connector's fetch policy."""

    def __init__(self, fetcher: Fetcher) -> None:
        self.fetcher = fetcher

    async def _fetch(self, request: WebFetchRequest) -> FetchedResponse:
        try:
            return await self.fetcher.fetch(
                request.url,
                max_bytes=request.max_bytes,
                accepted_types=tuple(t.lower() for t in request.accepted_types),
            )
        except PolicyRefused as refused:
            raise WebSourceRefused(refused.reason, refused.detail) from refused

    async def fetch(self, request: WebFetchRequest) -> WebPageResult:
        """The page body as text, under robots, rate, size and type policy."""
        fetched = await self._fetch(request)
        return WebPageResult(
            url=request.url,
            canonical_url=fetched.final_url,
            final_url=fetched.final_url,
            status=fetched.status,
            content_type=fetched.content_type,
            byte_count=fetched.bytes,
            content_digest=content_digest(fetched.text),
            retrieved_at=fetched.fetched_at,
            text_markdown=fetched.text,
            backend=BACKEND,
        )

    async def extract(self, request: WebFetchRequest) -> WebPageResult:
        """The page's main content as markdown, with its document metadata."""
        fetched = await self._fetch(request)
        try:
            page = extract_page(fetched.text, fetched.final_url)
        except PolicyRefused as refused:
            raise WebSourceRefused(refused.reason, refused.detail) from refused
        return WebPageResult(
            url=request.url,
            canonical_url=page.canonical_url,
            final_url=fetched.final_url,
            status=fetched.status,
            content_type=fetched.content_type,
            byte_count=fetched.bytes,
            content_digest=content_digest(page.markdown),
            retrieved_at=fetched.fetched_at,
            title=page.title,
            author=page.author,
            published_at=page.published,
            outbound_links=tuple(
                WebOutboundLink(url=link.url, text=link.text) for link in page.links
            ),
            text_markdown=page.markdown,
            backend=BACKEND,
        )
