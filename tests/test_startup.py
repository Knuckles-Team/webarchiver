import importlib

import pytest


@pytest.mark.concept("CONN-WEBARCHIVER-001")
def test_mcp_server_module_importable():
    """MCP server module imports cleanly at startup. CONCEPT:CONN-WEBARCHIVER-001"""
    assert importlib.import_module("webarchiver.mcp_server") is not None


@pytest.mark.concept("CONN-WEBARCHIVER-001")
def test_version_has_one_source():
    """The served version is the installed distribution version. CONCEPT:CONN-WEBARCHIVER-001"""
    from importlib.metadata import version

    module = importlib.import_module("webarchiver.mcp_server")
    assert module._VERSION == version("webarchiver")
