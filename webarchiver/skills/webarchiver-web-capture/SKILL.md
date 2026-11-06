---
name: webarchiver-web-capture
skill_type: skill
description: >-
  Read public web pages with the webarchiver-mcp MCP server under robots.txt,
  a per-domain rate limit and egress policy: raw body (web_fetch), main
  content as markdown with title, author, date, canonical URL and links
  (web_extract), the browser-rendered DOM (web_render), a PNG screenshot
  (web_screenshot), a page's outbound links (web_links) and a bounded
  same-site crawl (web_crawl). Use when the agent must read, quote, compare
  or discover web pages. Do NOT use for a durable archive copy
  (archivebox-web-archiving) or for competitor and market research runs
  (webarchiver-market-research-capture); prefer those.
license: MIT
tags: [webarchiver, web, fetch, extract, render, screenshot, crawl, mcp]
metadata:
  author: Knuckles-Team
  version: '1.0.0'
---
# Webarchiver web capture

One typed, read-only tool per operation on the `webarchiver-mcp` server. No
credential is needed; the connector reads public pages only.

## When to use
- Read one page's main content as markdown with its metadata and links.
- Read a page that builds its content with scripts (render it first).
- Take a screenshot of a page as visual evidence.
- List a page's links, or discover the pages of one site.

## When NOT to use
- A durable, re-openable archive copy: `archivebox-web-archiving`.
- A full competitor or market capture run: `webarchiver-market-research-capture`.
- Web search (finding URLs for a query): the search connector, then this skill.

## Tools
| Tool | Arguments | Returns (ontology class) |
|---|---|---|
| `web_fetch` | `request: {url, max_bytes?, accepted_types?, timeout_s?}` | page body, status, final URL, digest (`:FetchedWebPage`) or a refusal (`:WebFetchRefusal`) |
| `web_extract` | `request: {url, ...}` | main content markdown, title, author, `published_at`, `canonical_url`, `outbound_links` (`:ExtractedWebPage`) |
| `web_render` | `url` | rendered DOM `html`, `title`, `final_url`, `status` (`:RenderedWebPage`) |
| `web_screenshot` | `url`, `full_page` (default true) | `png_base64`, `width` (`:WebPageScreenshot`) |
| `web_links` | `url`, `same_site_only` | `links: [{url, text, same_site}]` (`:WebLinkList`) |
| `web_crawl` | `seed_url`, `same_site`, `max_pages` (1-1000), `max_depth` (0-10), `include`, `exclude` | `urls`, `skipped`, `truncated` (`:WebCrawlResult`) |

## Procedure
1. Start with `web_extract`. It is the cheapest way to get readable text.
2. If the result is a refusal `extract_empty`, or the text is missing what a
   browser shows, call `web_render` and read the DOM.
3. Call `web_screenshot` with `full_page: false` when you need visual
   evidence; full-page shots of long pages are large.
4. To discover pages, call `web_links` on the start page, or `web_crawl` with
   small bounds first (`max_pages` 10 to 25, `max_depth` 1), then widen.
5. Cite `final_url`, `retrieved_at` and `content_digest` for every page you use.

## Refusals
Each refusal has one closed reason. Do not retry `robots_disallowed`,
`egress_denied`, `policy_refused` or `unsupported_type`. Wait at least one
second and retry `rate_limited` once. Retry `upstream_failed` once, then
report it. For `size_exceeded`, raise `max_bytes` only if the page is needed.

## Guardrails
- Read public pages only. Never send credentials, cookies or form data.
- Respect the refusals; never work around robots.txt.
- Large crawls cost time on the shared rate limit: keep `max_pages` small.
