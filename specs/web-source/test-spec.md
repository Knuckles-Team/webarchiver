# CONN-WEBARCHIVER-WEB-SOURCE — Test specification

Governing spec: [spec.md](spec.md).

| Test ID | Requirement | Proving test | Expected observation |
|---|---|---|---|
| T-001 | `CONN-WEBARCHIVER-WEB-SOURCE-R001` | covered by the child rows | See each child. |
| T-002 | `CONN-WEBARCHIVER-WEB-SOURCE-R001.1` | `tests/test_conformance.py::test_webarchiver_conforms_to_the_web_source_contract` | The served tool schemas equal the contract's, and an unknown argument is refused. |
| T-003 | `CONN-WEBARCHIVER-WEB-SOURCE-R001.2` | `tests/test_extract.py::test_fetch_follows_redirect_and_returns_html` | Fixture pages yield the expected markdown and metadata, and a disallowed path is refused. |
| T-004 | `CONN-WEBARCHIVER-WEB-SOURCE-R001.3` | `tests/test_served.py::test_one_read_only_tool_per_operation` | A served `tools/call` reaches the extractor and the capture path. |
| T-005 | `CONN-WEBARCHIVER-WEB-SOURCE-R001.4` | `tests/test_extract.py::test_refusals` | Each case returns its reason and no page body. |
| T-006 | `CONN-WEBARCHIVER-WEB-SOURCE-R001.5` | `tests/test_extract.py::test_result_provenance` | Each named field is present and matches the fixture response. |
| T-007 | `CONN-WEBARCHIVER-WEB-SOURCE-R001.6` | `tests/test_conformance.py::test_webarchiver_conforms_to_the_web_source_contract` | The kit reports no broken obligation, and the engine holds one Document with `backend=webarchiver`. |
| T-008 | `CONN-WEBARCHIVER-WEB-SOURCE-R001.7` | `tests/test_crawl.py::test_bounded_crawl` | A fixture site yields the expected URLs in order, the disallowed path is reported and never fetched, and out-of-range bounds refuse with `policy_refused`. |
| T-009 | `CONN-WEBARCHIVER-WEB-SOURCE-R001.8` | `tests/test_kg_ingest.py::test_manifest_maps_document_and_chunk` (planned) | The served manifest maps both record types with their text, title, source and backend fields. |
| T-010 | `CONN-WEBARCHIVER-WEB-SOURCE-R001.10` | `tests/test_conformance.py::test_webarchiver_conforms_to_the_web_source_contract` | The kit reports no broken obligation. |
| T-011 | `CONN-WEBARCHIVER-WEB-SOURCE-R001.11` | `tests/test_fleet_name.py::test_connector_name_is_the_fleet_name` (planned) | The served content, the manifest and the ingest binding all name `webarchiver-mcp`. |
| T-012 | `CONN-WEBARCHIVER-WEB-SOURCE-R002` | `tests/test_extract.py::test_json_entity_document_passes_through` (planned) | Test: `tests/test_extract.py::test_json_entity_document_passes_through` fetches a fixture entity document and asserts the body, media type and digest. |
| T-013 | `CONN-WEBARCHIVER-WEB-SOURCE-R003` | covered by the child rows | See each child. |
| T-014 | `CONN-WEBARCHIVER-WEB-SOURCE-R003.1` | `tests/test_content_pack.py::test_every_class_rolls_up_to_medulla_core` | Every class reaches a core class, and the pack's tools, skills and prompts equal the served ones. |
| T-015 | `CONN-WEBARCHIVER-WEB-SOURCE-R003.2` | `tests/test_content_pack.py::test_access_contracts_route_every_class_to_a_served_tool` | The SDK parser accepts every contract, and the contracts cover every served tool and result class. |
| T-016 | `CONN-WEBARCHIVER-WEB-SOURCE-R003.3` | `tests/test_content_pack.py::test_prompts_and_skills_are_served_as_agent_definitions` | Both prompts and both skills are served, each prompt names its goal, tools, skills, data, guardrails and output, and the stubs are gone. |

## Negative and boundary cases

Each proving test above includes the refusal or error case that its row names. A vendor outage or an unauthorised call must return the SDK typed error.

## Quality and release proof

Run `uv run pytest tests` and `pre-commit run --all-files` from the repository root. A planned test is added by the code change that lands the row.
