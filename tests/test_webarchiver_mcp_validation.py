import pytest

from webarchiver.mcp_server import get_mcp_instance


@pytest.mark.concept("CONN-WEBARCHIVER-001")
def test_mcp_instance_registration(monkeypatch):
    """MCP server instantiates with its tool domains registered.

    CONCEPT:CONN-WEBARCHIVER-001
    """
    monkeypatch.setattr("sys.argv", ["webarchiver-mcp"])
    mcp, args, middlewares = get_mcp_instance()
    assert mcp is not None
