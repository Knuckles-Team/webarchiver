import sys
from importlib.metadata import version as _dist_version

from scion_sdk.connector import build_server as build_connector_server
from scion_sdk.ports.web_source import register_web_source_tools

from .api import WebarchiverSource
from .auth import get_client

_VERSION = _dist_version("webarchiver")

#: The fleet and onboarding name; EG files the content pack and ingest under it.
CONNECTOR_NAME = "webarchiver-mcp"

WEB_SOURCE_POLICY = """# Web source policy

webarchiver reads public web pages only and keeps nothing.

- robots.txt is honoured; a disallowed page is refused as robots_disallowed.
- Requests are rate limited per domain; a limited call is refused as rate_limited.
- Private, loopback and link-local addresses are refused as egress_denied.
- No credentials, cookies or form data are ever sent.
- Every result carries final_url, retrieved_at and content_digest.
- Refusal reasons are closed: robots_disallowed, egress_denied, policy_refused,
  unsupported_type, extract_empty, rate_limited, upstream_failed.
"""


def register_web_surface(context) -> None:
    """Register what the SDK tool surface does not own: the web-source tools and the policy."""
    mcp = context.server
    # web_fetch and web_extract: the SDK web-source contract's own tools.
    register_web_source_tools(mcp, lambda: WebarchiverSource(get_client().fetcher))

    @mcp.resource("webarchiver://policy", mime_type="text/markdown")
    def web_source_policy() -> str:
        """The read policy every webarchiver tool runs under."""
        return WEB_SOURCE_POLICY


def get_mcp_instance(*, command_args=None):
    """Build the connector server declared in ``webarchiver.connector``."""
    args, mcp = build_connector_server("webarchiver", command_args=command_args)
    return mcp, args, ()


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
