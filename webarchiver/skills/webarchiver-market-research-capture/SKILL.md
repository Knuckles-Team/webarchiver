---
name: webarchiver-market-research-capture
skill_type: skill
description: >-
  Capture competitor and market pages as structured text with webarchiver-mcp, then file a tagged durable copy of each with archivebox-mcp. Use to record what a page says on a date, build a research brief, or keep evidence for comparison. Do NOT use for one-off page reads (webarchiver-web-capture) or archive search (archivebox-snapshot-search).
license: MIT
tags: [webarchiver, archivebox, market-research, competitor-research, capture, mcp]
metadata:
  author: Knuckles-Team
  version: '1.0.0'
---
# Competitor and market research capture

Scope: Competitor and market research capture: read competitor and market pages (pricing, product, feature, about, blog and news pages) into structured text, metadata and links with the webarchiver-mcp server, then file a durable, tagged archive copy of each page with the archivebox-mcp server (archivebox_cli_add). Use when the agent must capture what a competitor or market page says on a date, build a research brief from captured pages, or keep evidence of a page for later comparison. Do NOT use for a one-off page read (webarchiver-web-capture) or for searching the archive (archivebox-snapshot-search); prefer those.

webarchiver is the primary capture path: it turns each page into structured
text and links. archivebox-mcp keeps the durable archive copy, tagged so the
captures of one research run can be found again.

## When to use
- Capture a competitor's pricing, product, feature or about pages.
- Capture market pages: industry news, analyst posts, directories, reviews.
- Re-capture the same pages later and compare what changed.

## When NOT to use
- Reading one page for an answer now: `webarchiver-web-capture`.
- Finding what was archived before: `archivebox-snapshot-search`.
- Pages behind a login, a paywall or a terms-of-use ban on automated access.

## Inputs
- `subject`: the competitor or market topic, for example `acme-pricing`.
- `urls`: the start pages. Find them with the search connector if needed.
- `run_tag`: `market-research,<subject>,<YYYY-MM-DD>`.

## Steps

1. Call `web_links`(url, same_site_only=true) for each start URL, or `web_crawl`(seed_url, max_pages=25, max_depth=1, include) for a site section such as `["/pricing", "/product"]`. Verify the kept pages match the research question and `truncated` is false.
2. Call `web_extract`(request) with `request: {url}` on each kept page. Verify each result has `title`, `canonical_url`, `retrieved_at`, `content_digest` and `text_markdown`.
3. For a page where `web_extract` refuses with `extract_empty` or lacks the prices or features a browser shows, call `web_render`(url). Verify the rendered `html` contains them.
4. For pricing and plan pages, call `web_screenshot`(url, full_page=false). Verify `png_base64` is present.
5. Call `archivebox_cli_add`(urls, tag, depth=0) once with all captured URLs and the `run_tag`. Verify the response accepts every URL.
6. Call `archivebox_get_snapshots`(tag) with the subject tag. Verify there is one snapshot per captured URL.
7. Write the research brief with one section per page: canonical URL, capture time, key facts quoted from `text_markdown`, and the snapshot reference. Verify every fact cites a `canonical_url` and `retrieved_at` from step 2.

## Failure recovery

| Failure | Cause | Recovery |
|---------|-------|----------|
| `web_extract` refuses with `robots_disallowed` or `egress_denied` | The page forbids automated access or is outside egress policy | Drop the page from the run and note the refusal in the brief |
| `archivebox_get_snapshots` shows fewer snapshots than URLs | Some URLs were not archived | Call `archivebox_cli_add`(urls, tag, depth=0) again with only the missing URLs |
| Crawl returns far too many pages | `include` pattern is too broad | Call `web_crawl`(seed_url, max_pages=25, max_depth=1, include) with a narrower `include` list |

## Output
- A research brief in markdown, each fact cited by `canonical_url` and
  `retrieved_at`.
- One ArchiveBox snapshot per captured page, tagged with `run_tag`.
- Ontology: each page is an `:ExtractedWebPage` (rolls up to `:WebResource`),
  each archive copy a `:WebSnapshot`.

## Guardrails
- Public pages only. Never log in, submit forms, or bypass robots.txt or a
  paywall.
- Never contact the competitor, post, or send messages about the research.
- Keep crawls small; the per-domain rate limit is shared.
- Quote facts exactly from the captured text; mark anything inferred.
- Removing archive snapshots needs the owner's approval, except test
  captures tagged `zz-validation-<date>`.
