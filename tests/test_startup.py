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


