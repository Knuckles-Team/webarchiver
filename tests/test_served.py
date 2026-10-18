"""The served MCP surface: one read-only tool per operation (CONN-WEBARCHIVER-WEB-SOURCE-R001.3)."""

from __future__ import annotations

import os

import pytest
from fastmcp import Client

import webarchiver.auth as auth_module
from webarchiver.mcp_server import get_mcp_instance

#: Each operation and its required input: the SDK web-source contract's tools
#: take one ``request`` object; the connector's own tools take the URL.
OPERATIONS = {
    "web_fetch": "request",
    "web_extract": "request",
    "web_render": "url",
    "web_screenshot": "url",
    "web_links": "url",
    "web_crawl": "seed_url",
}


@pytest.fixture
def loopback(monkeypatch: pytest.MonkeyPatch):
    auth_module.close_client()
    monkeypatch.setenv("WEBARCHIVER_ALLOW_LOOPBACK", "true")
    monkeypatch.setenv("WEBARCHIVER_MIN_INTERVAL_S", "0")
    yield
    auth_module.close_client()


@pytest.mark.spec("CONN-WEBARCHIVER-WEB-SOURCE-R001.3")
async def test_one_read_only_tool_per_operation() -> None:
    server, _args, _mw = get_mcp_instance(command_args=[])
    async with Client(server) as client:
        tools = {tool.name: tool for tool in await client.list_tools()}
    served = {
        name: (
            tools[name].annotations.readOnlyHint,
            tools[name].inputSchema["required"],
        )
        for name in OPERATIONS
    }
    assert served == {name: (True, [field]) for name, field in OPERATIONS.items()}
    assert not any(
        "action" in t.inputSchema.get("properties", {}) for t in tools.values()
    )


@pytest.mark.spec("CONN-WEBARCHIVER-WEB-SOURCE-R001.3")
async def test_tools_call_reaches_extractor(site: str, loopback: None) -> None:
    server, _args, _mw = get_mcp_instance(command_args=[])
    async with Client(server) as client:
        result = await client.call_tool(
            "web_extract", {"request": {"url": f"{site}/article"}}
        )
    body = result.structured_content["result"]
    assert body["kind"] == "page" and body["backend"] == "webarchiver"
    assert body["title"] == "Pod disruption budgets explained"


def _chromium_available() -> bool:
    """Browser tests run where Chromium and its libraries exist (the image)."""
    return os.environ.get("WEBARCHIVER_BROWSER_TESTS") == "1"


@pytest.mark.spec("CONN-WEBARCHIVER-WEB-SOURCE-R001.3")
@pytest.mark.skipif(not _chromium_available(), reason="Chromium is not installed")
async def test_render_and_screenshot_in_headless_chromium(site: str) -> None:
    from webarchiver.api import ApiClientSystem, FetchPolicy

    client = ApiClientSystem(FetchPolicy(min_interval_s=0.0), allow_loopback=True)
    try:
        rendered = await client.render(f"{site}/article")
        assert "cookie-banner" not in rendered.html
        assert "Pod disruption budgets" in rendered.title
        assert "voluntary disruptions" in rendered.html
        shot = await client.screenshot(f"{site}/article")
        assert shot.bytes > 1000 and shot.png_base64.startswith("iVBOR")
    finally:
        await client._close()
