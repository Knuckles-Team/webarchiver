---
name: webarchiver-market-research-capture
skill_type: skill
description: >-
  Competitor and market research capture: read competitor and market pages
  (pricing, product, feature, about, blog and news pages) into structured
  text, metadata and links with the webarchiver-mcp server, then file a
  durable, tagged archive copy of each page with the archivebox-mcp server
  (archivebox_cli_add). Use when the agent must capture what a competitor or
  market page says on a date, build a research brief from captured pages, or
  keep evidence of a page for later comparison. Do NOT use for a one-off page
  read (webarchiver-web-capture) or for searching the archive
  (archivebox-snapshot-search); prefer those.
license: MIT
tags: [webarchiver, archivebox, market-research, competitor-research, capture, mcp]
metadata:
  author: Knuckles-Team
  version: '1.0.0'
---
# Competitor and market research capture

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

## Procedure
1. **Scope.** For each start URL, call `web_links` with `same_site_only: true`.
   Keep the pages that match the research question (pricing, plans, product,
   features, about, news). For a whole site section use `web_crawl` with
   `max_pages` at most 25, `max_depth` 1 and an `include` pattern such as
   `["/pricing", "/product"]`.
2. **Capture text.** Call `web_extract` with `request: {url}` on each kept page.
   Keep `title`, `published_at`, `canonical_url`, `final_url`, `retrieved_at`,
   `content_digest`, `text_markdown` and `outbound_links`.
3. **Fallback for script-built pages.** If `web_extract` refuses with
   `extract_empty` or the text lacks the prices or features a browser shows,
   call `web_render` with `url` and read the content from the rendered `html`.
4. **Visual evidence.** For pricing and plan pages, call `web_screenshot` with
   `full_page: false`.
5. **Durable copy.** Call `archivebox_cli_add` on archivebox-mcp once with all
   captured URLs: `urls: [...]`, `tag: "<run_tag>"`, `depth: 0`. Do not use
   `depth` above 0; scoping was step 1.
6. **Verify.** Call `archivebox_get_snapshots` with `tag: "<subject>"` (or the
   URL) and confirm one snapshot per captured URL.
7. **Report.** Write a research brief: one section per page with the
   canonical URL, the capture time, the key facts (prices, plans, features,
   claims) quoted from `text_markdown`, and the archive snapshot reference.
   Compare against an earlier run of the same `subject` when one exists.

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
