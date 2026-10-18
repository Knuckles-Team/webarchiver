"""Fetch, extraction and refusals against a local fixture site (CONN-WEBARCHIVER-WEB-SOURCE-R001)."""

from __future__ import annotations

import hashlib

import pytest

from tests.conftest import FIXTURES
from webarchiver.api import ApiClientSystem, FetchPolicy, PolicyRefused
from webarchiver.api.policy import REFUSAL_REASONS, DomainRateLimiter, RobotsCache


def _client(**policy: object) -> ApiClientSystem:
    return ApiClientSystem(
        FetchPolicy(min_interval_s=0.0, **policy),  # type: ignore[arg-type]
        allow_loopback=True,
    )


@pytest.mark.spec("CONN-WEBARCHIVER-WEB-SOURCE-R001.2")
async def test_fetch_follows_redirect_and_returns_html(site: str) -> None:
    fetched = await _client().fetch(f"{site}/moved")
    assert fetched.final_url == f"{site}/article"
    assert fetched.status == 200
    assert "Pod disruption budgets" in fetched.text
    assert fetched.bytes == len(fetched.text.encode())


@pytest.mark.spec("CONN-WEBARCHIVER-WEB-SOURCE-R001.4")
@pytest.mark.parametrize(
    ("path", "reason", "policy"),
    [
        ("/private/secret", "robots_disallowed", {}),
        ("/image.png", "unsupported_type", {}),
        ("/huge", "size_exceeded", {"max_bytes": 1024}),
        ("/gone", "upstream_failed", {}),
    ],
)
async def test_refusals(
    site: str, path: str, reason: str, policy: dict[str, object]
) -> None:
    with pytest.raises(PolicyRefused) as refused:
        await _client(**policy).fetch(f"{site}{path}")
    assert refused.value.reason == reason
    assert refused.value.reason in REFUSAL_REASONS


@pytest.mark.spec("CONN-WEBARCHIVER-WEB-SOURCE-R001.2")
async def test_fetch_refuses_loopback_unless_allowed(site: str) -> None:
    client = ApiClientSystem(FetchPolicy(min_interval_s=0.0))
    with pytest.raises(PolicyRefused) as refused:
        await client.fetch(f"{site}/article")
    assert refused.value.reason == "egress_denied"


@pytest.mark.spec("CONN-WEBARCHIVER-WEB-SOURCE-R001.2")
async def test_fetch_refuses_non_http_url() -> None:
    with pytest.raises(PolicyRefused) as refused:
        await _client().fetch("file:///etc/passwd")
    assert refused.value.reason == "policy_refused"


@pytest.mark.spec("CONN-WEBARCHIVER-WEB-SOURCE-R001.2")
async def test_main_content_and_metadata(site: str) -> None:
    result = await _client().extract(f"{site}/article")
    page = result.page
    assert result.backend == "webarchiver"
    assert result.fetch_mode == "http"
    assert page.title == "Pod disruption budgets explained"
    assert page.author == "Ada Example"
    assert page.published.startswith("2026-09-01")
    assert page.canonical_url == f"{site}/article"
    assert "voluntary disruptions" in page.text
    assert "We use cookies" not in page.text
    assert "Copyright" not in page.text
    assert len(page.content_sha256) == 64
    urls = {link.url for link in page.links}
    assert "https://kubernetes.example.org/docs/pdb" in urls
    assert not any(url.startswith("mailto:") for url in urls)


@pytest.mark.spec("CONN-WEBARCHIVER-WEB-SOURCE-R001.2")
async def test_extract_refuses_a_page_without_content(site: str) -> None:
    with pytest.raises(PolicyRefused) as refused:
        await _client().extract(f"{site}/empty")
    assert refused.value.reason == "extract_empty"


@pytest.mark.spec("CONN-WEBARCHIVER-WEB-SOURCE-R001.2")
async def test_links_lists_outbound_links(site: str) -> None:
    result = await _client().links(f"{site}/article")
    assert {link.url for link in result.links} >= {
        f"{site}/",
        f"{site}/about",
        f"{site}/article",
        "https://kubernetes.example.org/docs/pdb",
    }
    same = await _client().links(f"{site}/article", same_site_only=True)
    assert all(link.same_site for link in same.links)
    assert len(same.links) < len(result.links)


@pytest.mark.spec("CONN-WEBARCHIVER-WEB-SOURCE-R001.2")
async def test_rate_limiter_spaces_requests_per_origin() -> None:
    now = [0.0]
    slept: list[float] = []

    async def sleep(seconds: float) -> None:
        slept.append(seconds)
        now[0] += seconds

    limiter = DomainRateLimiter(2.0, clock=lambda: now[0], sleep=sleep)
    await limiter.acquire("https://a.example")
    await limiter.acquire("https://b.example")
    await limiter.acquire("https://a.example")
    assert slept == [2.0]


@pytest.mark.spec("CONN-WEBARCHIVER-WEB-SOURCE-R001.2")
@pytest.mark.parametrize(("status", "allowed"), [(404, True), (503, False)])
async def test_robots_status_semantics(status: int, allowed: bool) -> None:
    async def loader(_url: str) -> tuple[int, str]:
        return status, ""

    cache = RobotsCache(loader)
    assert await cache.allowed("https://a.example/page", "ua") is allowed


@pytest.mark.spec("CONN-WEBARCHIVER-WEB-SOURCE-R001.5")
async def test_result_provenance(site: str) -> None:
    result = await _client().extract(f"{site}/moved")
    fixture = (FIXTURES / "article.html").read_bytes()
    assert result.backend == "webarchiver"
    assert result.url == f"{site}/moved"
    assert result.final_url == f"{site}/article"
    assert result.status == 200
    assert result.byte_count == len(fixture)
    assert (
        result.content_digest == hashlib.sha256(result.page.text.encode()).hexdigest()
    )
    assert result.retrieved_at.endswith("+00:00")
    assert result.robots == "allowed"
    assert result.content_type.startswith("text/html")
