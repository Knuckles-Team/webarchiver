# Connector architecture

The `webarchiver` package owns external-system operations and source mappings.
The [shared connector SDK](https://github.com/Knuckles-Team/agent-connector-sdk/blob/5babc4cc48ad73928468b243842f219f51e2cca1/README.md) owns reusable runtime contracts.

```mermaid
flowchart LR
    Caller[Authorized caller] --> Server[MCP server]
    Server --> Router[Operation router]
    Router --> Client[Connector API client]
    Client --> Vendor[Configured external system]
    Resolver[Credential references and TLS policy] --> Client
    Content[Packaged skills prompts ontology manifest] --> Server
    Source[Authorized source observations] --> Mapper[Connector ingest mapper]
    Mapper --> SDK[Shared connector ingest service]
```

## Source and verification map

| Boundary | Source | Verification target |
|---|---|---|
| MCP entry and routing | `webarchiver/mcp_server.py`, `webarchiver/mcp/mcp_system.py` | `tests/test_webarchiver_mcp_validation.py` |
| Credentials and TLS | `webarchiver/auth.py` | `tests/test_auth.py` |
| External requests | `webarchiver/api/api_client_base.py` | `tests/test_api_wrapper.py` |
| Native content and tool schemas | Package content and `scripts/generate_tool_schemas.py` | Live schema check; native content verification remains pending |
| Source observations | `webarchiver/kg_ingest.py` | `tests/test_kg_ingest.py` |

The [capability specification](https://github.com/Knuckles-Team/webarchiver/blob/main/specs/webarchiver/spec.md)
defines the planned behavior and acceptance targets.
The [delivery dashboard](https://knuckles-team.github.io/webarchiver/spec-delivery/)
shows source-backed records, code mappings, and declared relationships.
Its architecture download preserves the declared spec graph without inferring dependencies from shared code.

The generated source does not prove live service behavior, published artifacts, or deployed operation.
