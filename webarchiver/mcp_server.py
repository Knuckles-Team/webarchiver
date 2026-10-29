import sys
from importlib.metadata import version as _dist_version
from pathlib import Path

from agent_connector_sdk.config import load_config
from agent_connector_sdk.mcp.content import ConnectorContent
from agent_connector_sdk.mcp.server import create_mcp_server
from agent_connector_sdk.mcp.tool_surface import register_tool_surface
from agent_connector_sdk.ports.web_source import register_web_source_tools

from . import mcp as tool_modules
from .api import ApiClientSystem, WebarchiverSource
from .auth import get_client

_VERSION = _dist_version("webarchiver")

#: The fleet and onboarding name; EG files the content pack and ingest under it.
CONNECTOR_NAME = "webarchiver-mcp"


def get_mcp_instance(*, command_args=None):
    """Construct one SDK-governed server and its native package content."""
    load_config()
    package_root = Path(__file__).resolve().parent
    args, mcp, middlewares = create_mcp_server(
        name="Webarchiver",
        version=_VERSION,
        instructions="Governed web fetch, extract, render, screenshot and link connector",
        command_args=command_args,
        content=ConnectorContent(
            connector=CONNECTOR_NAME,
            package_root=package_root,
            package_version=_VERSION,
        ),
    )
    # One typed, annotated MCP tool per API operation (SDK default).
    register_tool_surface(
        mcp,
        service="webarchiver",
        tool_prefix="web",
        tools_module=tool_modules,
        client_cls=ApiClientSystem,
        get_client=get_client,
    )
    # web_fetch and web_extract: the SDK web-source contract's own tools.
    register_web_source_tools(mcp, lambda: WebarchiverSource(get_client().fetcher))
    for middleware in middlewares:
        mcp.add_middleware(middleware)
    return mcp, args, middlewares


def build_server(*, command_args=None):
    return get_mcp_instance(command_args=command_args)[0]


def mcp_server():
    mcp, args, _ = get_mcp_instance()
    print("Starting Webarchiver MCP", file=sys.stderr)
    options = (
        {} if args.transport == "stdio" else {"host": args.host, "port": args.port}
    )
    mcp.run(transport=args.transport, **options)


if __name__ == "__main__":
    mcp_server()
