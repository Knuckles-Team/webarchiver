# CONN-WEBARCHIVER-WEB-SOURCE — Implementation plan

Governing spec: [spec.md](spec.md). Rows: [requirements.md](requirements.md).

## Summary

This plan states how `webarchiver` delivers the rows of `CONN-WEBARCHIVER-WEB-SOURCE`. The live caller is the `webarchiver-mcp` console script. The owner is the `webarchiver` package. The rows reuse the `scion-sdk` helpers and add no second authority. The plan changes no runtime code.

## Technical Context

- **Language/Version**: Python >=3.12,<3.15
- **Primary Dependencies**: scion-sdk[mcp]>=0.6.4,<0.7.0; fastmcp; further pins in `pyproject.toml` (scion-sdk[mcp]>=0.6.4,<0.7.0, trafilatura>=2.0.0,<3.0.0, lxml>=6.0.0, playwright>=1.55.0,<2.0.0)
- **Storage**: N/A, the connector keeps no store of its own
- **Testing**: pytest; each row names the proving test as `path::name`
- **Target Platform**: Linux container and stdio or streamable HTTP MCP clients
- **Project Type**: connector
- **Performance Goals**: N/A, the vendor service sets the latency
- **Constraints**: vendor calls go through the SDK governed client; no connector-local transport
- **Scale/Scope**: 12 active row(s) in this spec

## Constitution Check

- Organization constitution 1.5.0, spec-first change: pass. Every behaviour is a row of this spec with a bound or planned test.
- Repository article R-I, connector scope: pass. The rows stay inside this connector's one external system and reuse the SDK for shared capabilities.

## Project Structure

- `webarchiver/api/web_source.py` (existing)
- `tests/test_conformance.py` (existing)
- `webarchiver/api/fetcher.py` (existing)
- `webarchiver/api/policy.py` (existing)
- `webarchiver/api/extraction.py` (existing)
- `tests/test_extract.py` (existing)
- `webarchiver/mcp_server.py` (existing)
- `webarchiver/api/browser.py` (existing)
- `tests/test_served.py` (existing)
- `webarchiver/api/request_filter.py` (existing)
- `webarchiver/api/crawl.py` (existing)
- `tests/test_crawl.py` (existing)
- `tests/test_kg_ingest.py` (existing)
- `webarchiver/kg_ingest.py` (existing)
- `pyproject.toml` (existing)
- `webarchiver/__init__.py` (existing)
- `tests/test_fleet_name.py` (new, planned)

## Phase 0: Research

No unknowns. Every row names its code and test; the caller chain of each row was read from the code.

## Phase 1: Design

### Summary

This plan states how `webarchiver` delivers the rows of `CONN-WEBARCHIVER-WEB-SOURCE`. The live caller is the `webarchiver-mcp` console script. The owner is the `webarchiver` package. The rows reuse the `scion-sdk` helpers and add no second authority. The plan changes no runtime code.

### Technical Context

- **Language/Version**: Python >=3.12,<3.15
- **Primary Dependencies**: scion-sdk[mcp]>=0.6.4,<0.7.0; fastmcp; further pins in `pyproject.toml` (scion-sdk[mcp]>=0.6.4,<0.7.0, trafilatura>=2.0.0,<3.0.0, lxml>=6.0.0, playwright>=1.55.0,<2.0.0)
- **Storage**: N/A, the connector keeps no store of its own
- **Testing**: pytest; each row names the proving test as `path::name`
- **Target Platform**: Linux container and stdio or streamable HTTP MCP clients
- **Project Type**: connector
- **Performance Goals**: N/A, the vendor service sets the latency
- **Constraints**: vendor calls go through the SDK governed client; no connector-local transport
- **Scale/Scope**: 12 active row(s) in this spec

### Constitution Check

- Organization constitution 1.5.0, spec-first change: pass. Every behaviour is a row of this spec with a bound or planned test.
- Repository article R-I, connector scope: pass. The rows stay inside this connector's one external system and reuse the SDK for shared capabilities.

### Project Structure

- `webarchiver/api/web_source.py` (existing)
- `tests/test_conformance.py` (existing)
- `tests/test_extract.py` (existing)
- `tests/test_served.py` (existing)
- `webarchiver/api/crawl.py` (existing)
- `tests/test_crawl.py` (existing)
- `tests/test_startup.py` (existing)
- `webarchiver/mcp_server.py` (existing)
- `webarchiver/kg_ingest.py` (existing)
- `pyproject.toml` (existing)
- `webarchiver/__init__.py` (existing)
- `tests/test_conformance_served.py` (new, planned)
- `tests/test_fleet_name.py` (new, planned)

### Phase 0: Research

No unknowns. Every row names its code and test; the caller chain of each row was read from the code.

### Phase 1: Design

### Summary

This plan states how `webarchiver` delivers the rows of `CONN-WEBARCHIVER-WEB-SOURCE`. The live caller is the `webarchiver-mcp` console script. The owner is the `webarchiver` package. The rows reuse the `scion-sdk` helpers and add no second authority. The plan changes no runtime code.

### Technical Context

- **Language/Version**: Python >=3.12,<3.15
- **Primary Dependencies**: scion-sdk[mcp]>=0.6.4,<0.7.0; fastmcp; further pins in `pyproject.toml` (scion-sdk[mcp]>=0.6.4,<0.7.0, trafilatura>=2.0.0,<3.0.0, lxml>=6.0.0, playwright>=1.55.0,<2.0.0)
- **Storage**: N/A, the connector keeps no store of its own
- **Testing**: pytest; each row names the proving test as `path::name`
- **Target Platform**: Linux container and stdio or streamable HTTP MCP clients
- **Project Type**: connector
- **Performance Goals**: N/A, the vendor service sets the latency
- **Constraints**: vendor calls go through the SDK governed client; no connector-local transport
- **Scale/Scope**: 12 active row(s) in this spec

### Constitution Check

- Organization constitution 1.5.0, spec-first change: pass. Every behaviour is a row of this spec with a bound or planned test.
- Repository article R-I, connector scope: pass. The rows stay inside this connector's one external system and reuse the SDK for shared capabilities.

### Project Structure

- `webarchiver/api/web_source.py` (existing)
- `tests/test_conformance.py` (existing)
- `tests/test_extract.py` (existing)
- `tests/test_served.py` (existing)
- `webarchiver/api/crawl.py` (existing)
- `tests/test_crawl.py` (existing)
- `tests/test_startup.py` (existing)
- `webarchiver/mcp_server.py` (existing)
- `webarchiver/kg_ingest.py` (existing)
- `pyproject.toml` (existing)
- `webarchiver/__init__.py` (existing)
- `tests/test_conformance_served.py` (new, planned)
- `tests/test_fleet_name.py` (new, planned)

### Phase 0: Research

No unknowns. Every row names its code and test; the caller chain of each row was read from the code.

### Phase 1: Design

### Existing system and reuse

`Webarchiver.launch_browser` at `webarchiver/webarchiver.py:63` holds the existing browser capture with ad removal. It becomes the render and screenshot path. The fetch and extraction tools are new. The SDK supplies the contract types, the server factory, the egress policy and the conformance kit.

### Architecture

Call path: arbora `research.web` -> engine work item of kind `WebPage` -> SDK ingest worker -> `WebFetchSourceAdapter.extract` -> this connector `web_extract` -> engine `SourceIngest`.

The connector holds no store and no selection rule. It returns one page result or one typed refusal per call.

### Interfaces and data model

The tool arguments and results are the SDK contract types of `SCION-SOURCE-INGEST-R005.40.1`. No connector-local result type exists.

### Live integration path

The production caller is `WebFetchSourceAdapter.extract` in the SDK. arbora reaches it through the engine work item of `ARBORA-OPS-R067.2`.

### Quality and release gates

The SDK conformance kit of `SCION-SOURCE-INGEST-R005.40.2` must pass against the served connector.

### Risks, alternatives, and decisions

A spec-only change on `main` must not publish a release. Merge commits for spec text carry `[skip ci]`.

### Phase 2: Task approach

`tasks.md` holds one task per row, producer first. Rows that depend on none run in parallel. A task is checked when its `Spec:` trailer is on the default branch.

### Complexity Tracking

None. The constitution check passed.

### Build contract

- `pre-commit run --all-files` runs ruff check, ruff format, the shared `connector-standard`, `spec`, `secrets` and `dependency-readiness` gates at the pinned shared revision.
- `uv run pytest tests` runs the proving tests; the shared complexity, duplication and KISS gates apply their org thresholds and this repository sets no local override.
- A change adds no scanner suppression and no duplicate implementation of an SDK helper.

### Production caller chain

- `CONN-WEBARCHIVER-WEB-SOURCE-R001.11`: `webarchiver-mcp` in `pyproject.toml` runs `webarchiver.mcp_server:mcp_server`, which builds the server from the `scion_sdk.connector` entry point `webarchiver` (`webarchiver/__init__.py:0`); `connector_name("webarchiver")` in the SDK resolves the same entry point name for the content pack, the manifest and the ingest binding.

### Cross-repo seams

None. The rows depend only on the published `scion-sdk` package, which the connector imports.

### Phase 2: Task approach

`tasks.md` holds one task per row, producer first. Rows that depend on none run in parallel. A task is checked when its `Spec:` trailer is on the default branch.

### Complexity Tracking

None. The constitution check passed.

### Build contract

- `pre-commit run --all-files` runs ruff check, ruff format, the shared `connector-standard`, `spec`, `secrets` and `dependency-readiness` gates at the pinned shared revision.
- `uv run pytest tests` runs the proving tests; the shared complexity, duplication and KISS gates apply their org thresholds and this repository sets no local override.
- A change adds no scanner suppression and no duplicate implementation of an SDK helper.

### Production caller chain

- `CONN-WEBARCHIVER-WEB-SOURCE-R001.11`: `webarchiver-mcp` in `pyproject.toml` runs `webarchiver.mcp_server:mcp_server`, which builds the server from the `scion_sdk.connector` entry point `webarchiver` (`webarchiver/__init__.py:0`); `connector_name("webarchiver")` in the SDK resolves the same entry point name for the content pack, the manifest and the ingest binding.

### Cross-repo seams

None. The rows depend only on the published `scion-sdk` package, which the connector imports.

## Phase 2: Task approach

`tasks.md` holds one task per row, producer first. Rows that depend on none run in parallel. A task is checked when its `Spec:` trailer is on the default branch.

## Complexity Tracking

None. The constitution check passed.

## Build contract

- `pre-commit run --all-files` runs ruff check, ruff format, the shared `connector-standard`, `spec`, `secrets` and `dependency-readiness` gates at the pinned shared revision.
- `uv run pytest tests` runs the proving tests; the shared complexity, duplication and KISS gates apply their org thresholds and this repository sets no local override.
- A change adds no scanner suppression and no duplicate implementation of an SDK helper.

## Production caller chain

- `CONN-WEBARCHIVER-WEB-SOURCE-R001.1`: the `webarchiver-mcp` console script runs `webarchiver.mcp_server:mcp_server`, which calls `register_web_source_tools` (webarchiver/mcp_server.py:46) over `WebarchiverSource` (webarchiver/api/web_source.py:31).
- `CONN-WEBARCHIVER-WEB-SOURCE-R001.2`: the `webarchiver-mcp` console script runs `webarchiver.mcp_server:mcp_server`, which calls `register_web_source_tools` (webarchiver/mcp_server.py:46) over `WebarchiverSource` (webarchiver/api/web_source.py:31); the fetcher in `webarchiver/api/fetcher.py` applies robots, rate and size policy of `webarchiver/api/policy.py`.
- `CONN-WEBARCHIVER-WEB-SOURCE-R001.3`: an MCP client calls `web_render` or `web_screenshot`, registered by `register_tool_surface` in `webarchiver/mcp_server.py`, which reach `webarchiver/api/browser.py` through `Webarchiver.launch_browser`.
- `CONN-WEBARCHIVER-WEB-SOURCE-R001.4`: the `webarchiver-mcp` console script runs `webarchiver.mcp_server:mcp_server`, which calls `register_web_source_tools` (webarchiver/mcp_server.py:46) over `WebarchiverSource` (webarchiver/api/web_source.py:31); refusals come from `webarchiver/api/policy.py` and `webarchiver/api/request_filter.py`.
- `CONN-WEBARCHIVER-WEB-SOURCE-R001.5`: the `webarchiver-mcp` console script runs `webarchiver.mcp_server:mcp_server`, which calls `register_web_source_tools` (webarchiver/mcp_server.py:46) over `WebarchiverSource` (webarchiver/api/web_source.py:31).
- `CONN-WEBARCHIVER-WEB-SOURCE-R001.6`: the `webarchiver-mcp` console script runs `webarchiver.mcp_server:mcp_server`, which calls `register_web_source_tools` (webarchiver/mcp_server.py:46) over `WebarchiverSource` (webarchiver/api/web_source.py:31); the SDK conformance kit calls the served tools, then `connector-sync --once` ingests one page.
- `CONN-WEBARCHIVER-WEB-SOURCE-R001.7`: an MCP client calls `web_crawl`, implemented in `webarchiver/api/crawl.py`, which fetches every page through the same fetcher.
- `CONN-WEBARCHIVER-WEB-SOURCE-R001.8`: the ingest runner reads `webarchiver/connector_manifest.yml`, whose `schema_mappings` resolve `manifest:<connector>#schema_mappings/Document` and `Chunk`.
- `CONN-WEBARCHIVER-WEB-SOURCE-R001.10`: the `webarchiver-mcp` console script runs `webarchiver.mcp_server:mcp_server`, which calls `register_web_source_tools` (webarchiver/mcp_server.py:46) over `WebarchiverSource` (webarchiver/api/web_source.py:31); the SDK conformance kit runs against the served connector in process.
- `CONN-WEBARCHIVER-WEB-SOURCE-R001.11`: `webarchiver-mcp` in `pyproject.toml` runs `webarchiver.mcp_server:mcp_server`, which builds the server from the `scion_sdk.connector` entry point `webarchiver` (`webarchiver/__init__.py:0`); `connector_name("webarchiver")` in the SDK resolves the same entry point name for the content pack, the manifest and the ingest binding.
- `CONN-WEBARCHIVER-WEB-SOURCE-R002`: the `webarchiver-mcp` console script runs `webarchiver.mcp_server:mcp_server`, which calls `register_web_source_tools` (webarchiver/mcp_server.py:46) over `WebarchiverSource` (webarchiver/api/web_source.py:31).

## Cross-repo seams

None. The rows depend only on the published `scion-sdk` package, which the connector imports.
