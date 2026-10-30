# Webarchiver

![GitHub Repo stars](https://img.shields.io/github/stars/Knuckles-Team/webarchiver)
![GitHub forks](https://img.shields.io/github/forks/Knuckles-Team/webarchiver)
![GitHub contributors](https://img.shields.io/github/contributors/Knuckles-Team/webarchiver)
![GitHub license](https://img.shields.io/github/license/Knuckles-Team/webarchiver)
![GitHub last commit (by committer)](https://img.shields.io/github/last-commit/Knuckles-Team/webarchiver)
![GitHub pull requests](https://img.shields.io/github/issues-pr/Knuckles-Team/webarchiver)
![GitHub closed pull requests](https://img.shields.io/github/issues-pr-closed/Knuckles-Team/webarchiver)
![GitHub issues](https://img.shields.io/github/issues/Knuckles-Team/webarchiver)
![GitHub top language](https://img.shields.io/github/languages/top/Knuckles-Team/webarchiver)
![GitHub language count](https://img.shields.io/github/languages/count/Knuckles-Team/webarchiver)
![GitHub repo size](https://img.shields.io/github/repo-size/Knuckles-Team/webarchiver)
![GitHub repo file count (file type)](https://img.shields.io/github/directory-file-count/Knuckles-Team/webarchiver)
![PyPI - Version](https://img.shields.io/pypi/v/webarchiver)
![PyPI - Downloads](https://img.shields.io/pypi/dd/webarchiver)
![PyPI - License](https://img.shields.io/pypi/l/webarchiver)
![PyPI - Wheel](https://img.shields.io/pypi/wheel/webarchiver)
![PyPI - Implementation](https://img.shields.io/pypi/implementation/webarchiver)
![MCP Server](https://badge.mcpx.dev?type=server 'MCP Server')

Governed web fetch, extract, render, screenshot and link connector

The [documentation site](https://knuckles-team.github.io/webarchiver/) contains the
full API, deployment, security, and operational reference. This README is the concise
entry point for installation and the supported runtime surfaces.

## Overview

`webarchiver` is the fleet's web fetch and scrape connector. It reads public web
pages under an explicit policy and returns typed results an agent or the graph
can ingest: raw pages, extracted main content with document metadata, rendered
DOMs, full-page screenshots and outbound links. It holds no credentials.

## Key capabilities

- **Governed fetch** — robots.txt, a per-domain rate limit, size and
  content-type caps, re-checked redirects and egress pinning that refuses
  private and loopback destinations. Every refusal has a typed reason.
- **Main-content extraction** — clean text and markdown with title, author,
  published date, canonical URL, content digest and links.
- **Rendering** — headless Chromium for pages built by scripts, with ad and
  tracker requests aborted and fixed overlays removed.
- **Screenshots** — full-page PNG captures.
- **Site crawl** — a bounded breadth-first walk from one seed URL that returns
  page URLs (up to 1000) under the same robots and rate policy.
- **One tool per operation** — `web_fetch`, `web_extract`,
  `web_render`, `web_screenshot`, `web_crawl` and `web_links`, all
  read-only.
- **Shared web-source contract** — `web_fetch` and `web_extract` are the
  scion-sdk web-source contract's tools: the same request, page
  result and refusal reasons as every page connector, including the ArchiveBox
  connector. Each page names its `backend` (`webarchiver`).

## Quick start

Install the package and run its generated entry points:

```bash
python -m pip install "webarchiver[mcp]"
webarchiver-mcp
```

For an on-demand run, use `uvx`:

```bash
uvx --from "webarchiver[mcp]" webarchiver-mcp
```

The networked server binds to loopback by default:

```bash
webarchiver-mcp --transport streamable-http --host 127.0.0.1 --port 8000
```

## Architecture

The provider keeps the boundary between transport and domain code explicit:

```text
client → MCP entry point → one tool per operation → fetch policy → web
                                  └── skills, prompts, ontology, connector presets
```

The MCP surface has one typed, read-only tool per operation. Regenerate the tool
fingerprints with `python scripts/generate_tool_schemas.py` after changing a tool
contract.

<!-- MCP-TOOLS-TABLE:START -->
<!-- MCP-TOOLS-TABLE:END -->

## MCP configuration

The server supports local `stdio` and authenticated `streamable-http` deployments.
Keep endpoint, credential, selector, and TLS references in SDK configuration; do not put
resolved values in client configuration.

```json
{
  "mcpServers": {
    "webarchiver-mcp": {
      "command": "webarchiver-mcp",
      "args": [],
      "env": {"SYSTEMTOOL": "true"}
    }
  }
}
```

For a networked deployment, use an authenticated TLS ingress and keep the allowlist in
`MCP_ALLOWED_HOSTS`. A configured remote example is `https://service.example.invalid/mcp`;
it is documentation-only and is never contacted by the generator.

<!-- MCP-CONFIG-EXAMPLES:START -->

```json
{
  "mcpServers": {
    "webarchiver-mcp": {
      "command": "webarchiver-mcp",
      "args": ["--transport", "streamable-http", "--port", "8000"],
      "env": {
        "TRANSPORT": "streamable-http",
        "HOST": "127.0.0.1",
        "PORT": "8000",
        "SYSTEMTOOL": "true"
      }
    }
  }
}
```

<!-- MCP-CONFIG-EXAMPLES:END -->

Container builds install the published wheel for the pinned version. Publish the
release first, then run from the repository root:

```bash
docker build --file docker/Dockerfile --target mcp -t webarchiver:<version>-mcp .
```

Deploy reviewed images by digest (`webarchiver@sha256:<digest>`) and include
`--cap-drop=ALL` in the runtime policy. The [deployment guide](https://knuckles-team.github.io/webarchiver/deployment/)
contains the complete transport and container examples.

## Documentation

Use the [Pages documentation](https://knuckles-team.github.io/webarchiver/) for
installation details, API capabilities, deployment profiles, platform integration,
and the concept registry. The concise local references remain available at:

- [Installation](docs/installation.md)
- [Usage](docs/usage.md)
- [Deployment](docs/deployment.md)
- [Platform](docs/platform.md)
- [Concept registry](docs/concepts.md)

## Development

Create an isolated branch, install the test extra, and run the complete local gate:

```bash
uv sync --extra test
pytest tests -q
pre-commit run --all-files
```

Keep MCP examples and environment documentation aligned with the implemented settings.
Add focused positive and adversarial tests for every behavior change. See
`AGENTS.md` for the current module ownership and release checks.

## License

This project is distributed under the MIT license. See [LICENSE](LICENSE) for the
complete terms.
