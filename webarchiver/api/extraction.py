"""Main-content extraction from fetched HTML (CONN-WEBARCHIVER-WEB-SOURCE-R001).

Readability-style boilerplate removal is trafilatura's; this module only maps
its output onto one typed :class:`ExtractedPage` and collects outbound links
with lxml. A page with no extractable main content is refused rather than
returned empty, so a caller never ingests a fabricated blank document.
"""

from __future__ import annotations

import hashlib
import json
from urllib.parse import urldefrag, urljoin, urlsplit

import lxml.html
import trafilatura
from pydantic import BaseModel, ConfigDict

from .policy import PolicyRefused

__all__ = ["ExtractedPage", "PageLink", "extract_links", "extract_page"]

_MAX_LINKS = 2000


class PageLink(BaseModel):
    """One outbound hyperlink, resolved to an absolute URL."""

    model_config = ConfigDict(frozen=True, extra="forbid")

    url: str
    text: str = ""
    same_site: bool = False


class ExtractedPage(BaseModel):
    """The main content of one page plus its document metadata."""

    model_config = ConfigDict(frozen=True, extra="forbid")

    url: str
    canonical_url: str
    title: str = ""
    author: str = ""
    published: str = ""
    site_name: str = ""
    language: str = ""
    description: str = ""
    text: str
    markdown: str
    content_sha256: str
    links: tuple[PageLink, ...] = ()


def _canonical(html_doc: lxml.html.HtmlElement, base: str) -> str:
    for href in html_doc.xpath('//link[@rel="canonical"]/@href'):
        if str(href).strip():
            return urldefrag(urljoin(base, str(href).strip()))[0]
    return urldefrag(base)[0]


def extract_links(html: str, base_url: str) -> tuple[PageLink, ...]:
    """Every distinct http(s) ``<a href>`` in ``html``, absolute and de-fragmented."""
    if not html.strip():
        return ()
    doc = lxml.html.fromstring(html)
    site = (urlsplit(base_url).hostname or "").lower()
    seen: dict[str, PageLink] = {}
    for anchor in doc.iter("a"):
        href = (anchor.get("href") or "").strip()
        if not href:
            continue
        url = urldefrag(urljoin(base_url, href))[0]
        parts = urlsplit(url)
        if parts.scheme not in {"http", "https"} or url in seen:
            continue
        seen[url] = PageLink(
            url=url,
            text=" ".join(anchor.text_content().split())[:300],
            same_site=(parts.hostname or "").lower() == site,
        )
        if len(seen) >= _MAX_LINKS:
            break
    return tuple(seen.values())


def extract_page(html: str, url: str) -> ExtractedPage:
    """Extract ``html``'s main content as text and markdown with metadata."""
    if not html.strip():
        raise PolicyRefused("extract_empty", url, "empty body")
    doc = lxml.html.fromstring(html)
    canonical = _canonical(doc, url)
    raw = trafilatura.extract(
        html,
        url=url,
        output_format="json",
        with_metadata=True,
        include_comments=False,
        include_tables=True,
        favor_precision=True,
    )
    meta = json.loads(raw) if raw else {}
    text = str(meta.get("text") or "").strip()
    if not text:
        raise PolicyRefused("extract_empty", url, "no main content")
    markdown = (
        trafilatura.extract(
            html,
            url=url,
            output_format="markdown",
            include_comments=False,
            include_tables=True,
            favor_precision=True,
        )
        or text
    )
    return ExtractedPage(
        url=url,
        canonical_url=canonical,
        title=str(meta.get("title") or ""),
        author=str(meta.get("author") or ""),
        published=str(meta.get("date") or ""),
        site_name=str(meta.get("sitename") or ""),
        language=str(meta.get("language") or ""),
        description=str(meta.get("description") or ""),
        text=text,
        markdown=markdown.strip(),
        content_sha256=hashlib.sha256(text.encode("utf-8")).hexdigest(),
        links=extract_links(html, url),
    )
