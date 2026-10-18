"""Headless, ad-blocked page rendering and full-page screenshots.

CONN-WEBARCHIVER-WEB-SOURCE-R001. Chromium runs through Playwright. Every
request the page makes, sub-resources included, is routed through
:meth:`Browser._route`: requests to a known ad or tracker host, or to an
address outside the public egress boundary, are aborted. Before a page loads,
fixed and sticky overlays are removed and scrolling is re-enabled, so a full
page screenshot shows the content rather than a cookie banner (the behaviour
the original Selenium archiver had).
"""

from __future__ import annotations

import asyncio
import base64
import socket
from dataclasses import dataclass, field
from functools import lru_cache
from typing import Any
from urllib.parse import urlsplit

from agent_connector_sdk.http.egress import egress_ip_is_blocked
from pydantic import BaseModel, ConfigDict

from .policy import PolicyRefused

__all__ = ["AD_HOST_SUFFIXES", "Browser", "RenderedPage", "Screenshot"]

#: Ad and tracker hosts aborted at the network layer (suffix match).
AD_HOST_SUFFIXES = (
    "doubleclick.net",
    "googlesyndication.com",
    "googleadservices.com",
    "google-analytics.com",
    "googletagmanager.com",
    "googletagservices.com",
    "adservice.google.com",
    "amazon-adsystem.com",
    "adnxs.com",
    "adsrvr.org",
    "criteo.com",
    "criteo.net",
    "taboola.com",
    "outbrain.com",
    "scorecardresearch.com",
    "quantserve.com",
    "hotjar.com",
    "facebook.net",
    "connect.facebook.net",
    "ads-twitter.com",
    "rubiconproject.com",
    "pubmatic.com",
    "openx.net",
    "moatads.com",
    "chartbeat.com",
    "segment.io",
    "mixpanel.com",
)

#: Removes fixed/sticky overlays and re-enables scrolling.
_DECLUTTER_JS = """
() => {
  for (const el of Array.from(document.querySelectorAll('body *'))) {
    const pos = getComputedStyle(el).position;
    if (pos === 'fixed' || pos === 'sticky' || pos === '-webkit-sticky') {
      el.remove();
    }
  }
  for (const el of [document.documentElement, document.body]) {
    if (el) { el.style.overflow = 'visible'; el.style.position = 'relative'; }
  }
}
"""

#: Scrolls through the page so lazy content loads, then back to the top.
_SCROLL_JS = """
async (maxHeight) => {
  const step = Math.max(window.innerHeight, 200);
  const height = Math.min(document.body.scrollHeight, maxHeight);
  for (let y = 0; y < height; y += step) {
    window.scrollTo(0, y);
    await new Promise(r => setTimeout(r, 50));
  }
  window.scrollTo(0, 0);
}
"""


class RenderedPage(BaseModel):
    """The DOM of a page after scripts ran."""

    model_config = ConfigDict(frozen=True, extra="forbid")

    url: str
    final_url: str
    status: int
    title: str
    html: str
    blocked_requests: int


class Screenshot(BaseModel):
    """A PNG screenshot, base64-encoded."""

    model_config = ConfigDict(frozen=True, extra="forbid")

    url: str
    final_url: str
    full_page: bool
    width: int
    png_base64: str
    bytes: int


def is_ad_host(host: str) -> bool:
    host = host.lower().rstrip(".")
    return any(host == s or host.endswith(f".{s}") for s in AD_HOST_SUFFIXES)


@lru_cache(maxsize=1024)
def _resolve(host: str) -> tuple[str, ...]:
    try:
        infos = socket.getaddrinfo(host, None, proto=socket.IPPROTO_TCP)
    except OSError:
        return ()
    return tuple(sorted({str(info[4][0]) for info in infos}))


@dataclass
class Browser:
    """One lazily launched Chromium shared by render and screenshot."""

    allow_loopback: bool = False
    navigation_timeout_ms: int = 30_000
    max_scroll_height: int = 20_000
    viewport_width: int = 1366
    viewport_height: int = 900
    _playwright: Any = field(default=None, init=False)
    _browser: Any = field(default=None, init=False)
    _lock: asyncio.Lock = field(default_factory=asyncio.Lock, init=False)

    def _egress_blocked(self, host: str) -> bool:
        addresses = _resolve(host)
        if not addresses:
            return True
        return any(
            egress_ip_is_blocked(ip, allow_loopback=self.allow_loopback)
            for ip in addresses
        )

    async def _ensure(self) -> Any:
        async with self._lock:
            if self._browser is None:
                from playwright.async_api import async_playwright

                self._playwright = await async_playwright().start()
                try:
                    self._browser = await asyncio.wait_for(
                        self._playwright.chromium.launch(
                            headless=True, args=["--disable-dev-shm-usage"]
                        ),
                        self.navigation_timeout_ms / 1000,
                    )
                except Exception as exc:  # noqa: BLE001 - launch failure is typed
                    await self._playwright.stop()
                    self._playwright = None
                    raise PolicyRefused(
                        "render_failed", "chromium", type(exc).__name__
                    ) from exc
        return self._browser

    async def close(self) -> None:
        if self._browser is not None:
            await self._browser.close()
            self._browser = None
        if self._playwright is not None:
            await self._playwright.stop()
            self._playwright = None

    async def _open(self, url: str, user_agent: str) -> tuple[Any, Any, int, list[int]]:
        host = urlsplit(url).hostname or ""
        if self._egress_blocked(host):
            raise PolicyRefused("egress_denied", url)
        browser = await self._ensure()
        context = await browser.new_context(
            user_agent=user_agent,
            viewport={"width": self.viewport_width, "height": self.viewport_height},
            java_script_enabled=True,
            accept_downloads=False,
        )
        blocked = [0]

        async def _route(route: Any) -> None:
            req_host = urlsplit(route.request.url).hostname or ""
            if req_host and (is_ad_host(req_host) or self._egress_blocked(req_host)):
                blocked[0] += 1
                await route.abort()
            else:
                await route.continue_()

        await context.route("**/*", _route)
        page = await context.new_page()
        try:
            response = await page.goto(
                url, wait_until="networkidle", timeout=self.navigation_timeout_ms
            )
        except Exception as exc:  # noqa: BLE001 - Playwright raises its own types
            await context.close()
            raise PolicyRefused("upstream_failed", url, type(exc).__name__) from exc
        status = response.status if response is not None else 0
        if status >= 400:
            await context.close()
            raise PolicyRefused("upstream_failed", url, str(status))
        await page.evaluate(_SCROLL_JS, self.max_scroll_height)
        await page.evaluate(_DECLUTTER_JS)
        return context, page, status, blocked

    async def render(self, url: str, *, user_agent: str) -> RenderedPage:
        context, page, status, blocked = await self._open(url, user_agent)
        try:
            return RenderedPage(
                url=url,
                final_url=page.url,
                status=status,
                title=await page.title(),
                html=await page.content(),
                blocked_requests=blocked[0],
            )
        finally:
            await context.close()

    async def screenshot(
        self, url: str, *, user_agent: str, full_page: bool = True
    ) -> Screenshot:
        context, page, _, _ = await self._open(url, user_agent)
        try:
            png = await page.screenshot(full_page=full_page, type="png")
            return Screenshot(
                url=url,
                final_url=page.url,
                full_page=full_page,
                width=self.viewport_width,
                png_base64=base64.b64encode(png).decode("ascii"),
                bytes=len(png),
            )
        finally:
            await context.close()
