"""Bounded site crawl (CONN-WEBARCHIVER-WEB-SOURCE-R001.7)."""

from __future__ import annotations

import pytest
from fastmcp import Client

import webarchiver.auth as auth_module
from webarchiver.api import ApiClientSystem, FetchPolicy, PolicyRefused
from webarchiver.mcp_server import get_mcp_instance


def _client() -> ApiClientSystem:
    return ApiClientSystem(FetchPolicy(min_interval_s=0.0), allow_loopback=True)


@pytest.mark.spec("CONN-WEBARCHIVER-WEB-SOURCE-R001.7")
async def test_bounded_crawl(site: str) -> None:
    result = await _client().crawl(f"{site}/docs/", max_depth=2)
    assert result.urls == (
        f"{site}/docs/",
        f"{site}/docs/a",
        f"{site}/docs/b",
        f"{site}/blog/post",
        f"{site}/docs/deep",
    )
    # robots.txt disallows /private/; it is reported, never fetched.
    assert [(s.url, s.reason) for s in result.skipped] == [
        (f"{site}/private/x", "robots_disallowed")
    ]
    assert result.max_depth_reached == 2
    assert not any("elsewhere.example" in u for u in result.urls)


@pytest.mark.spec("CONN-WEBARCHIVER-WEB-SOURCE-R001.7")
async def test_crawl_patterns_and_page_cap(site: str) -> None:
    only_docs = await _client().crawl(
        f"{site}/docs/", max_depth=5, include=[r"/docs/"], exclude=[r"/deep"]
    )
    assert only_docs.urls == (f"{site}/docs/", f"{site}/docs/a", f"{site}/docs/b")
    capped = await _client().crawl(f"{site}/docs/", max_pages=2, max_depth=5)
    assert len(capped.urls) == 2 and capped.truncated is True
    for bad in ({"max_pages": 1001}, {"max_depth": 11}, {"include": ["("]}):
        with pytest.raises(PolicyRefused) as refused:
            await _client().crawl(f"{site}/docs/", **bad)  # type: ignore[arg-type]
        assert refused.value.reason == "policy_refused"


@pytest.mark.spec("CONN-WEBARCHIVER-WEB-SOURCE-R001.7")
async def test_crawl_is_one_served_tool(
    site: str, monkeypatch: pytest.MonkeyPatch
) -> None:
    auth_module.close_client()
    monkeypatch.setenv("WEBARCHIVER_ALLOW_LOOPBACK", "true")
    monkeypatch.setenv("WEBARCHIVER_MIN_INTERVAL_S", "0")
    server, _args, _mw = get_mcp_instance(command_args=[])
    async with Client(server) as client:
        tools = {t.name: t for t in await client.list_tools()}
        result = await client.call_tool(
            "web_crawl", {"seed_url": f"{site}/docs/", "max_depth": 1}
        )
    auth_module.close_client()
    assert tools["web_crawl"].annotations.readOnlyHint is True
    assert "seed_url" in tools["web_crawl"].inputSchema["required"]
    body = result.structured_content or {}
    body = body.get("result", body)
    assert f"{site}/docs/b" in body["urls"]
