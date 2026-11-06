"""Surface contracts: tool use, links, data locations and business roles."""

from scion_sdk.surface_contracts import (
    BusinessRole,
    DataLocation,
    Refusal,
    SurfaceLink,
    ToolStep,
    ToolUseContract,
)

CONTRACTS = (
    ToolUseContract(
        task="read-web-page",
        description="Read one public page as cited markdown; fall back to the raw body or the rendered DOM.",
        steps=(
            ToolStep(
                tool="web_extract",
                params=("request",),
                result=(
                    "url",
                    "final_url",
                    "title",
                    "markdown",
                    "outbound_links",
                    "retrieved_at",
                    "content_digest",
                ),
                refusals=(
                    Refusal(
                        code="robots_disallowed", when="robots.txt disallows the page"
                    ),
                    Refusal(
                        code="egress_denied",
                        when="the address is private or blocked by the egress policy",
                    ),
                    Refusal(
                        code="rate_limited",
                        when="the per-domain rate limit is exhausted",
                    ),
                    Refusal(code="upstream_failed", when="the site did not answer"),
                )
                + (
                    Refusal(
                        code="extract_empty", when="no main content could be extracted"
                    ),
                ),
            ),
            ToolStep(
                tool="web_fetch",
                params=("request",),
                result=(
                    "url",
                    "final_url",
                    "status",
                    "content_type",
                    "body",
                    "retrieved_at",
                    "content_digest",
                ),
                refusals=(
                    Refusal(
                        code="robots_disallowed", when="robots.txt disallows the page"
                    ),
                    Refusal(
                        code="egress_denied",
                        when="the address is private or blocked by the egress policy",
                    ),
                    Refusal(
                        code="rate_limited",
                        when="the per-domain rate limit is exhausted",
                    ),
                    Refusal(code="upstream_failed", when="the site did not answer"),
                )
                + (
                    Refusal(
                        code="unsupported_type", when="the content type is not accepted"
                    ),
                ),
            ),
            ToolStep(
                tool="web_render",
                params=("url",),
                result=("url", "final_url", "dom", "retrieved_at"),
                refusals=(
                    Refusal(
                        code="robots_disallowed", when="robots.txt disallows the page"
                    ),
                    Refusal(
                        code="egress_denied",
                        when="the address is private or blocked by the egress policy",
                    ),
                    Refusal(
                        code="rate_limited",
                        when="the per-domain rate limit is exhausted",
                    ),
                    Refusal(code="upstream_failed", when="the site did not answer"),
                ),
            ),
        ),
    ),
    ToolUseContract(
        task="capture-page-evidence",
        description="Capture a screenshot of a page as visual evidence next to its text.",
        steps=(
            ToolStep(
                tool="web_screenshot",
                params=("url", "full_page"),
                result=("url", "final_url", "image", "retrieved_at"),
                refusals=(
                    Refusal(
                        code="robots_disallowed", when="robots.txt disallows the page"
                    ),
                    Refusal(
                        code="egress_denied",
                        when="the address is private or blocked by the egress policy",
                    ),
                    Refusal(
                        code="rate_limited",
                        when="the per-domain rate limit is exhausted",
                    ),
                    Refusal(code="upstream_failed", when="the site did not answer"),
                ),
            ),
        ),
    ),
    ToolUseContract(
        task="discover-site-pages",
        description="List a page's links, then crawl a bounded section of the site.",
        steps=(
            ToolStep(
                tool="web_links",
                params=("url", "same_site_only"),
                result=("url", "links", "retrieved_at"),
                refusals=(
                    Refusal(
                        code="robots_disallowed", when="robots.txt disallows the page"
                    ),
                    Refusal(
                        code="egress_denied",
                        when="the address is private or blocked by the egress policy",
                    ),
                    Refusal(
                        code="rate_limited",
                        when="the per-domain rate limit is exhausted",
                    ),
                    Refusal(code="upstream_failed", when="the site did not answer"),
                ),
            ),
            ToolStep(
                tool="web_crawl",
                params=(
                    "seed_url",
                    "same_site",
                    "max_pages",
                    "max_depth",
                    "include",
                    "exclude",
                ),
                result=("seed_url", "pages", "max_depth_reached", "retrieved_at"),
                refusals=(
                    Refusal(
                        code="robots_disallowed", when="robots.txt disallows the page"
                    ),
                    Refusal(
                        code="egress_denied",
                        when="the address is private or blocked by the egress policy",
                    ),
                    Refusal(
                        code="rate_limited",
                        when="the per-domain rate limit is exhausted",
                    ),
                    Refusal(code="upstream_failed", when="the site did not answer"),
                )
                + (
                    Refusal(
                        code="policy_refused",
                        when="the crawl exceeds the allowed bounds",
                    ),
                ),
            ),
        ),
    ),
    ToolUseContract(
        task="research-market-pages",
        description="Scope a competitor or market site, extract each relevant page and keep screenshot evidence.",
        steps=(
            ToolStep(
                tool="web_links",
                params=("url", "same_site_only"),
                result=("links",),
                refusals=(
                    Refusal(
                        code="robots_disallowed", when="robots.txt disallows the page"
                    ),
                    Refusal(
                        code="egress_denied",
                        when="the address is private or blocked by the egress policy",
                    ),
                    Refusal(
                        code="rate_limited",
                        when="the per-domain rate limit is exhausted",
                    ),
                    Refusal(code="upstream_failed", when="the site did not answer"),
                ),
            ),
            ToolStep(
                tool="web_crawl",
                params=("seed_url", "max_pages", "max_depth", "include"),
                result=("pages",),
                refusals=(
                    Refusal(
                        code="robots_disallowed", when="robots.txt disallows the page"
                    ),
                    Refusal(
                        code="egress_denied",
                        when="the address is private or blocked by the egress policy",
                    ),
                    Refusal(
                        code="rate_limited",
                        when="the per-domain rate limit is exhausted",
                    ),
                    Refusal(code="upstream_failed", when="the site did not answer"),
                ),
            ),
            ToolStep(
                tool="web_extract",
                params=("request",),
                result=("final_url", "title", "markdown", "content_digest"),
                refusals=(
                    Refusal(
                        code="robots_disallowed", when="robots.txt disallows the page"
                    ),
                    Refusal(
                        code="egress_denied",
                        when="the address is private or blocked by the egress policy",
                    ),
                    Refusal(
                        code="rate_limited",
                        when="the per-domain rate limit is exhausted",
                    ),
                    Refusal(code="upstream_failed", when="the site did not answer"),
                ),
            ),
            ToolStep(
                tool="web_render",
                params=("url",),
                result=("dom",),
                refusals=(
                    Refusal(
                        code="robots_disallowed", when="robots.txt disallows the page"
                    ),
                    Refusal(
                        code="egress_denied",
                        when="the address is private or blocked by the egress policy",
                    ),
                    Refusal(
                        code="rate_limited",
                        when="the per-domain rate limit is exhausted",
                    ),
                    Refusal(code="upstream_failed", when="the site did not answer"),
                ),
            ),
            ToolStep(
                tool="web_screenshot",
                params=("url", "full_page"),
                result=("image",),
                refusals=(
                    Refusal(
                        code="robots_disallowed", when="robots.txt disallows the page"
                    ),
                    Refusal(
                        code="egress_denied",
                        when="the address is private or blocked by the egress policy",
                    ),
                    Refusal(
                        code="rate_limited",
                        when="the per-domain rate limit is exhausted",
                    ),
                    Refusal(code="upstream_failed", when="the site did not answer"),
                ),
            ),
        ),
    ),
)

LINKS = (
    SurfaceLink(
        task="read-web-page",
        tools=("web_extract", "web_fetch", "web_render"),
        prompts=("webarchiver_operator", "webarchiver_market_researcher"),
        skills=("webarchiver-web-capture",),
    ),
    SurfaceLink(
        task="capture-page-evidence",
        tools=("web_screenshot",),
        prompts=("webarchiver_operator", "webarchiver_market_researcher"),
        skills=("webarchiver-web-capture",),
    ),
    SurfaceLink(
        task="discover-site-pages",
        tools=("web_links", "web_crawl"),
        prompts=("webarchiver_operator", "webarchiver_market_researcher"),
        skills=("webarchiver-web-capture",),
    ),
    SurfaceLink(
        task="research-market-pages",
        tools=("web_links", "web_crawl", "web_extract", "web_render", "web_screenshot"),
        prompts=("webarchiver_market_researcher",),
        skills=("webarchiver-market-research-capture",),
    ),
)

LOCATIONS = (
    DataLocation(
        name="public-web-pages",
        holds=("FetchedWebPage", "ExtractedWebPage", "RenderedWebPage"),
        instance="the public web, read on demand under robots, rate and egress policy",
        read_tool="web_extract",
        federation_key="url",
    ),
    DataLocation(
        name="public-web-links",
        holds=("WebLinkList", "WebCrawlResult"),
        instance="the public web, read on demand under robots, rate and egress policy",
        read_tool="web_links",
        federation_key="seed_url",
    ),
    DataLocation(
        name="public-web-screenshots",
        holds=("WebPageScreenshot",),
        instance="the public web, read on demand under robots, rate and egress policy",
        read_tool="web_screenshot",
        federation_key="url",
    ),
)

ROLES = (
    BusinessRole(
        name="market-research-analyst",
        tasks=("research-market-pages", "read-web-page", "capture-page-evidence"),
        description="Captures competitor and market pages for a cited research brief.",
    ),
)
