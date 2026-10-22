import importlib

import pytest


@pytest.mark.concept("CONN-WEBARCHIVER-001")
def test_mcp_server_module_importable():
    """MCP server module imports cleanly at startup. CONCEPT:CONN-WEBARCHIVER-001"""
    assert importlib.import_module("webarchiver.mcp_server") is not None


@pytest.mark.concept("CONN-WEBARCHIVER-001")
def test_version_has_one_source():
    """The package version comes from _version.py. CONCEPT:CONN-WEBARCHIVER-001"""
    from webarchiver._version import __version__

    module = importlib.import_module("webarchiver.mcp_server")
    assert module.__version__ == __version__


@pytest.mark.concept("CONN-WEBARCHIVER-001")
async def test_server_lists_registered_tools_and_content():
    """The SDK-built server lists its tools and serves the manifest."""
    from fastmcp import Client

    from webarchiver.mcp_server import get_mcp_instance

    server, _args, _middlewares = get_mcp_instance(command_args=[])
    async with Client(server) as client:
        tools = {tool.name for tool in await client.list_tools()}
        resources = {str(item.uri) for item in await client.list_resources()}
    assert tools
    assert "manifest://connector" in resources


@pytest.mark.concept("CONN-WEBARCHIVER-001")
def test_manifest_loads_with_the_sdk_model():
    """connector_manifest.yml validates against agent-connector-sdk."""
    from pathlib import Path

    from agent_connector_sdk.manifest.loader import load_manifest

    import webarchiver

    manifest = load_manifest(
        Path(webarchiver.__file__).parent / "connector_manifest.yml"
    )
    assert manifest.connector == "webarchiver-mcp"


@pytest.mark.spec("CONN-WEBARCHIVER-WEB-SOURCE-R001.8")
def test_manifest_maps_document_and_chunk_records():
    """SourceIngest resolves manifest:<connector>#schema_mappings/<type> for both."""
    from pathlib import Path

    from agent_connector_sdk.manifest.loader import load_manifest

    import webarchiver

    manifest = load_manifest(
        Path(webarchiver.__file__).parent / "connector_manifest.yml"
    )
    for record_type, ontology_class in (("Document", "Document"), ("Chunk", "Chunk")):
        mapping = manifest.schema_mappings[record_type]
        assert mapping.ontology_class == ontology_class
        assert {"text", "title", "source_uri", "content_hash", "backend"} <= set(
            mapping.fields
        )


@pytest.mark.spec("CONN-WEBARCHIVER-WEB-SOURCE-R001.11")
def test_connector_name_is_the_fleet_name():
    """Pack, manifest and ingest binding are filed under the fleet name."""
    from pathlib import Path

    from agent_connector_sdk.manifest.loader import load_manifest

    import webarchiver
    from webarchiver import kg_ingest

    mcp_server = importlib.import_module("webarchiver.mcp_server")
    assert mcp_server.CONNECTOR_NAME == "webarchiver-mcp"
    assert kg_ingest._BINDING.connector == "webarchiver-mcp"
    manifest = load_manifest(
        Path(webarchiver.__file__).parent / "connector_manifest.yml"
    )
    assert manifest.connector == "webarchiver-mcp"
