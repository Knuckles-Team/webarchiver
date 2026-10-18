"""webarchiver passes the SDK web-source conformance kit (CONN-WEBARCHIVER-WEB-SOURCE-R001.1)."""

from __future__ import annotations

import pytest
from agent_connector_sdk.testing.web_source_conformance import (
    check_web_source,
    fastmcp_caller,
    fixture_site,
    served_tool_schemas,
)
from fastmcp import Client

import webarchiver.auth as auth_module
from webarchiver.mcp_server import get_mcp_instance

INTERVAL = 0.3


@pytest.mark.spec("CONN-WEBARCHIVER-WEB-SOURCE-R001.1")
@pytest.mark.spec("CONN-WEBARCHIVER-WEB-SOURCE-R001.10")
async def test_webarchiver_conforms_to_the_web_source_contract(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    auth_module.close_client()
    monkeypatch.setenv("WEBARCHIVER_ALLOW_LOOPBACK", "true")
    monkeypatch.setenv("WEBARCHIVER_MIN_INTERVAL_S", str(INTERVAL))
    server, _args, _mw = get_mcp_instance(command_args=[])
    with fixture_site() as site:
        async with Client(server) as client:
            report = await check_web_source(
                fastmcp_caller(client),
                site,
                backend="webarchiver",
                served_tools=await served_tool_schemas(client),
                min_interval_s=INTERVAL,
            )
    auth_module.close_client()
    assert report.ok, report.results
