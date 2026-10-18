from fastmcp import FastMCP


def register_system_tools(mcp: FastMCP) -> None:
    """Register system tools that do not wrap an API-client method.

    Every API operation is already one MCP tool, registered from the client
    class by ``register_tool_surface``. Add only non-client tools here, such as
    KG ingest tools. Do not add ``action``-routed dispatch tools.
    CONCEPT:CONN-WEBARCHIVER-001
    """
