# CONN-WEBARCHIVER-WEB-SOURCE — Web page fetch, extraction, render and screenshot connector

Owner: webarchiver. Cross-repo IDs: `SCION-SOURCE-INGEST-R005.40`, `ARBORA-OPS-R067`, `MEDULLA-UNIFIED-DATA-PLANE-R651.7`.

Extends: [SCION-SOURCE-INGEST](https://github.com/Knuckles-Team/scion-sdk/blob/main/specs/SCION-SOURCE-INGEST/spec.md)
References: [ARBORA-OPS](https://github.com/Knuckles-Team/arbora/blob/main/specs/hosted-api-operations/spec.md)

## Purpose and user stories

The webarchiver connector fetches, extracts, renders and captures web pages for the platform. It is the primary backend of the web research operation. It implements the SDK web-source contract.

A person asks the platform to research a topic on the web. The platform stores each chosen page as one Document with its source URL.

## Why a new spec

The search covered `specs/` of this repository and the SDK and arbora specs. This repository had no spec for page fetch. The SDK owns only the contract (`SCION-SOURCE-INGEST-R005.40`). The behavior of this one external system belongs here.

## Scope and interfaces

In scope: the web-source tools and their mapping onto the SDK contract.

Out of scope: search, page selection, enrichment and citations. The engine owns them. Served operations belong to arbora.

## Delivery mapping

Component: webarchiver connector

Code: ../../webarchiver/__init__.py

## User Scenarios & Testing

### User Story 1 - Pages answer through the web-source contract (rollup) (Priority: P1)

The fleet operator and the engine rely on this behaviour of `webarchiver`: The webarchiver connector must implement the web-source contract of `SCION-SOURCE-INGEST-R005.40`. It is proven independently of the other stories.

**Acceptance Scenarios**:

1. **Given** the `webarchiver` connector built from the default branch, **When** `the planned test of this row` runs, **Then** see each child.

### User Story 2 - Model (Priority: P1)

The fleet operator and the engine rely on this behaviour of `webarchiver`: `web_fetch` and `web_extract` are the SDK web-source contract's tools (`SCION-SOURCE-INGEST-R005.40.1`). It is proven independently of the other stories.

**Acceptance Scenarios**:

1. **Given** the `webarchiver` connector built from the default branch, **When** `tests/test_conformance.py::test_webarchiver_conforms_to_the_web_source_contract` runs, **Then** the served tool schemas equal the contract's, and an unknown argument is refused.

### User Story 3 - Behavior (Priority: P1)

The fleet operator and the engine rely on this behaviour of `webarchiver`: The connector must obey `robots.txt` for its user agent and cache each file for 3600 s. It is proven independently of the other stories.

**Acceptance Scenarios**:

1. **Given** the `webarchiver` connector built from the default branch, **When** `tests/test_extract.py::test_fetch_follows_redirect_and_returns_html` runs, **Then** fixture pages yield the expected markdown and metadata, and a disallowed path is refused.

### User Story 4 - Wiring (Priority: P2)

The fleet operator and the engine rely on this behaviour of `webarchiver`: The browser capture in `Webarchiver.launch_browser` (`webarchiver/webarchiver.py:63`) serves `web_render` and `web_screenshot`. It is proven independently of the other stories.

**Acceptance Scenarios**:

1. **Given** the `webarchiver` connector built from the default branch, **When** `tests/test_served.py::test_one_read_only_tool_per_operation` runs, **Then** a served `tools/call` reaches the extractor and the capture path.

### User Story 5 - Refusal (Priority: P2)

The fleet operator and the engine rely on this behaviour of `webarchiver`: Each refusal must use a closed reason of the contract: `robots_disallowed`, `rate_limited`, `size_exceeded`, `unsupported_type`, `egress_denied`, `policy_refused`, `extract_empty` or `upstream_failed`. It is proven independently of the other stories.

**Acceptance Scenarios**:

1. **Given** the `webarchiver` connector built from the default branch, **When** `tests/test_extract.py::test_refusals` runs, **Then** each case returns its reason and no page body.

### User Story 6 - Evidence (Priority: P2)

The fleet operator and the engine rely on this behaviour of `webarchiver`: Each result must name `backend=webarchiver`, the final URL, the HTTP status, the byte count, the content digest, the retrieval time and the `robots.txt` decision. It is proven independently of the other stories.

**Acceptance Scenarios**:

1. **Given** the `webarchiver` connector built from the default branch, **When** `tests/test_extract.py::test_result_provenance` runs, **Then** each named field is present and matches the fixture response.

### User Story 7 - Hot-path proof (Priority: P2)

The fleet operator and the engine rely on this behaviour of `webarchiver`: The test serves the connector and runs the SDK conformance kit of `SCION-SOURCE-INGEST-R005.40.2` against it. It is proven independently of the other stories.

**Acceptance Scenarios**:

1. **Given** the `webarchiver` connector built from the default branch, **When** `tests/test_conformance.py::test_webarchiver_conforms_to_the_web_source_contract` runs, **Then** the kit reports no broken obligation, and the engine holds one Document with `backend=webarchiver`.

### User Story 8 - Bounded site crawl (Priority: P2)

The fleet operator and the engine rely on this behaviour of `webarchiver`: `web_crawl(seed_url, same_site, max_pages, max_depth, include, exclude)` in `webarchiver/api/crawl.py` must walk links breadth-first from one seed and return the page URLs it reached, in discovery order. It is proven independently of the other stories.

**Acceptance Scenarios**:

1. **Given** the `webarchiver` connector built from the default branch, **When** `tests/test_crawl.py::test_bounded_crawl` runs, **Then** a fixture site yields the expected URLs in order, the disallowed path is reported and never fetched, and out-of-range bounds refuse with `policy_refused`.

### User Story 9 - Ingest mappings (Priority: P2)

The fleet operator and the engine rely on this behaviour of `webarchiver`: `webarchiver/connector_manifest.yml` must declare `schema_mappings` for the `Document` and `Chunk` record types, mapped to the core `Document` and `Chunk` classes, so `SourceIngest` resolves `manifest:<connector>#schema_mappings/Document` and `../Chunk` in the pack the fleet imports (`SCION-SOURCE-INGEST-R004.25`). It is proven independently of the other stories.

**Acceptance Scenarios**:

1. **Given** the `webarchiver` connector built from the default branch, **When** `tests/test_kg_ingest.py::test_manifest_maps_document_and_chunk` runs, **Then** the served manifest maps both record types with their text, title, source and backend fields.

### User Story 10 - Conformance (Priority: P2)

The fleet operator and the engine rely on this behaviour of `webarchiver`: The connector passes the SDK conformance kit (`SCION-SOURCE-INGEST-R005.40.2`) against itself, served in process. It is proven independently of the other stories.

**Acceptance Scenarios**:

1. **Given** the `webarchiver` connector built from the default branch, **When** `tests/test_conformance.py::test_webarchiver_conforms_to_the_web_source_contract` runs, **Then** the kit reports no broken obligation.

### User Story 11 - Fleet name (Priority: P2)

The fleet operator and the engine rely on this behaviour of `webarchiver`: The connector files its content pack, manifest and ingest binding under its fleet name `webarchiver-mcp`, not the package name. It is proven independently of the other stories.

**Acceptance Scenarios**:

1. **Given** the `webarchiver` connector built from the default branch, **When** `tests/test_fleet_name.py::test_connector_name_is_the_fleet_name` runs, **Then** the served content, the manifest and the ingest binding all name `webarchiver-mcp`.

### User Story 12 - Structured entity documents (Priority: P2)

The fleet operator and the engine rely on this behaviour of `webarchiver`: `web_fetch` must accept the media types `application/json` and `application/ld+json`. It is proven independently of the other stories.

**Acceptance Scenarios**:

1. **Given** the `webarchiver` connector built from the default branch, **When** `tests/test_extract.py::test_json_entity_document_passes_through` runs, **Then** test: `tests/test_extract.py::test_json_entity_document_passes_through` fetches a fixture entity document and asserts the body, media type and digest.

### Edge Cases

- The vendor service is unreachable or rejects the credential: the connector returns the SDK typed error and never a partial result.
- An argument outside the documented inputs is refused with the SDK typed refusal and causes no effect on the vendor service.

## Requirements

- **FR-001**: Pages answer through the web-source contract (rollup). Rows: `CONN-WEBARCHIVER-WEB-SOURCE-R001`.
- **FR-002**: Model. Rows: `CONN-WEBARCHIVER-WEB-SOURCE-R001.1`.
- **FR-003**: Behavior. Rows: `CONN-WEBARCHIVER-WEB-SOURCE-R001.2`.
- **FR-004**: Wiring. Rows: `CONN-WEBARCHIVER-WEB-SOURCE-R001.3`.
- **FR-005**: Refusal. Rows: `CONN-WEBARCHIVER-WEB-SOURCE-R001.4`.
- **FR-006**: Evidence. Rows: `CONN-WEBARCHIVER-WEB-SOURCE-R001.5`.
- **FR-007**: Hot-path proof. Rows: `CONN-WEBARCHIVER-WEB-SOURCE-R001.6`.
- **FR-008**: Bounded site crawl. Rows: `CONN-WEBARCHIVER-WEB-SOURCE-R001.7`.
- **FR-009**: Ingest mappings. Rows: `CONN-WEBARCHIVER-WEB-SOURCE-R001.8`.
- **FR-010**: Conformance. Rows: `CONN-WEBARCHIVER-WEB-SOURCE-R001.10`.
- **FR-011**: Fleet name. Rows: `CONN-WEBARCHIVER-WEB-SOURCE-R001.11`.
- **FR-012**: Structured entity documents. Rows: `CONN-WEBARCHIVER-WEB-SOURCE-R002`.

## Success Criteria

- **SC-001**: See each child. Rows: `CONN-WEBARCHIVER-WEB-SOURCE-R001`.
- **SC-002**: The served tool schemas equal the contract's, and an unknown argument is refused. Rows: `CONN-WEBARCHIVER-WEB-SOURCE-R001.1`.
- **SC-003**: Fixture pages yield the expected markdown and metadata, and a disallowed path is refused. Rows: `CONN-WEBARCHIVER-WEB-SOURCE-R001.2`.
- **SC-004**: A served `tools/call` reaches the extractor and the capture path. Rows: `CONN-WEBARCHIVER-WEB-SOURCE-R001.3`.
- **SC-005**: Each case returns its reason and no page body. Rows: `CONN-WEBARCHIVER-WEB-SOURCE-R001.4`.
- **SC-006**: Each named field is present and matches the fixture response. Rows: `CONN-WEBARCHIVER-WEB-SOURCE-R001.5`.
- **SC-007**: The kit reports no broken obligation, and the engine holds one Document with `backend=webarchiver`. Rows: `CONN-WEBARCHIVER-WEB-SOURCE-R001.6`.
- **SC-008**: A fixture site yields the expected URLs in order, the disallowed path is reported and never fetched, and out-of-range bounds refuse with `policy_refused`. Rows: `CONN-WEBARCHIVER-WEB-SOURCE-R001.7`.
- **SC-009**: The served manifest maps both record types with their text, title, source and backend fields. Rows: `CONN-WEBARCHIVER-WEB-SOURCE-R001.8`.
- **SC-010**: The kit reports no broken obligation. Rows: `CONN-WEBARCHIVER-WEB-SOURCE-R001.10`.
- **SC-011**: The served content, the manifest and the ingest binding all name `webarchiver-mcp`. Rows: `CONN-WEBARCHIVER-WEB-SOURCE-R001.11`.
- **SC-012**: Test: `tests/test_extract.py::test_json_entity_document_passes_through` fetches a fixture entity document and asserts the body, media type and digest. Rows: `CONN-WEBARCHIVER-WEB-SOURCE-R002`.

## Assumptions

- The `webarchiver` package keeps the entry point and module layout named in the rows.
- The shared SDK supplies the transport, authentication, retry and certification helpers the rows reuse.

## Traceability

| Label | Rows | Design section | Test ID | Evidence |
|---|---|---|---|---|
| FR-001 | `CONN-WEBARCHIVER-WEB-SOURCE-R001` | plan.md Production caller chain | T-001 | planned |
| FR-002 | `CONN-WEBARCHIVER-WEB-SOURCE-R001.1` | plan.md Production caller chain | T-002 | tests/test_conformance.py::test_webarchiver_conforms_to_the_web_source_contract |
| FR-003 | `CONN-WEBARCHIVER-WEB-SOURCE-R001.2` | plan.md Production caller chain | T-003 | tests/test_extract.py::test_fetch_follows_redirect_and_returns_html |
| FR-004 | `CONN-WEBARCHIVER-WEB-SOURCE-R001.3` | plan.md Production caller chain | T-004 | tests/test_served.py::test_one_read_only_tool_per_operation |
| FR-005 | `CONN-WEBARCHIVER-WEB-SOURCE-R001.4` | plan.md Production caller chain | T-005 | tests/test_extract.py::test_refusals |
| FR-006 | `CONN-WEBARCHIVER-WEB-SOURCE-R001.5` | plan.md Production caller chain | T-006 | tests/test_extract.py::test_result_provenance |
| FR-007 | `CONN-WEBARCHIVER-WEB-SOURCE-R001.6` | plan.md Production caller chain | T-007 | tests/test_conformance.py::test_webarchiver_conforms_to_the_web_source_contract |
| FR-008 | `CONN-WEBARCHIVER-WEB-SOURCE-R001.7` | plan.md Production caller chain | T-008 | tests/test_crawl.py::test_bounded_crawl |
| FR-009 | `CONN-WEBARCHIVER-WEB-SOURCE-R001.8` | plan.md Production caller chain | T-009 | tests/test_kg_ingest.py::test_manifest_maps_document_and_chunk |
| FR-010 | `CONN-WEBARCHIVER-WEB-SOURCE-R001.10` | plan.md Production caller chain | T-010 | tests/test_conformance.py::test_webarchiver_conforms_to_the_web_source_contract |
| FR-011 | `CONN-WEBARCHIVER-WEB-SOURCE-R001.11` | plan.md Production caller chain | T-011 | tests/test_fleet_name.py::test_connector_name_is_the_fleet_name |
| FR-012 | `CONN-WEBARCHIVER-WEB-SOURCE-R002` | plan.md Production caller chain | T-012 | tests/test_extract.py::test_json_entity_document_passes_through |
