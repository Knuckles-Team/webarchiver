# CONN-WEBARCHIVER-WEB-SOURCE — Test specification

Governing spec: [spec.md](spec.md).

| Test ID | Requirement | Level | Setup and input | Expected observation | Evidence |
|---|---|---|---|---|---|
| T-001 | `CONN-WEBARCHIVER-WEB-SOURCE-R001` | Unit | Every child row. | See each child. |  |
| T-002 | `CONN-WEBARCHIVER-WEB-SOURCE-R001.1` | Unit | `tests/test_tools.py::test_tool_schemas_match_contract` | Each tool schema equals the contract schema, and an unknown argument is refused. |  |
| T-003 | `CONN-WEBARCHIVER-WEB-SOURCE-R001.2` | Unit | `tests/test_extract.py::test_main_content_and_metadata` | Fixture pages yield the expected markdown and metadata, and a disallowed path is refused. |  |
| T-004 | `CONN-WEBARCHIVER-WEB-SOURCE-R001.3` | Unit | `tests/test_served.py::test_tools_call_reaches_extractor` | A served `tools/call` reaches the extractor and the capture path. |  |
| T-005 | `CONN-WEBARCHIVER-WEB-SOURCE-R001.4` | Unit | `tests/test_extract.py::test_refusals` | Each case returns its reason and no page body. |  |
| T-006 | `CONN-WEBARCHIVER-WEB-SOURCE-R001.5` | Unit | `tests/test_extract.py::test_result_provenance` | Each named field is present and matches the fixture response. |  |
| T-007 | `CONN-WEBARCHIVER-WEB-SOURCE-R001.6` | Served | `tests/test_conformance_served.py::test_conformance_kit_and_sync` | The kit reports no broken obligation, and the engine holds one Document with `backend=webarchiver`. |  |
| T-008 | `CONN-WEBARCHIVER-WEB-SOURCE-R001.7` | Unit | `tests/test_crawl.py::test_bounded_crawl` | The fixture site yields the expected URLs in order and the disallowed path is reported, not fetched. |  |
| T-009 | `CONN-WEBARCHIVER-WEB-SOURCE-R001.8` | Unit | `tests/test_startup.py::test_manifest_maps_document_and_chunk_records` | The manifest maps Document and Chunk to the core classes. |  |
| T-010 | `CONN-WEBARCHIVER-WEB-SOURCE-R001.10` | Unit | `tests/test_conformance.py::test_webarchiver_conforms_to_the_web_source_contract` | The kit reports no broken obligation. |  |
