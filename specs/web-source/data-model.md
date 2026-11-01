# CONN-WEBARCHIVER-WEB-SOURCE — Data model

Entities and records that the rows add or declare.

| Row | Entity or record | Definition |
|---|---|---|
| `CONN-WEBARCHIVER-WEB-SOURCE-R001.8` | Ingest mappings | `webarchiver/connector_manifest.yml` must declare `schema_mappings` for the `Document` and `Chunk` record types, mapped to the core `Document` and `Chunk` classes, so `SourceIngest` resolves `manifest:<connector>#schema_mappings/Document` and `../Chunk` in the pack the fleet imports (`SCION-SOURCE-INGEST-R004.25`). |

Relations follow the row text; the connector adds no table of its own.
