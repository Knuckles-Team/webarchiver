#!/usr/bin/env python3
"""Generate or check live MCP contracts without calling provider tools.

Run from the project environment: python scripts/generate_tool_schemas.py [--check].
All tools retain both schemas in schemas/mcp_tools.json. Only tools in real
extraction presets receive connector pins; an empty starter preset is valid.
"""

from __future__ import annotations

import argparse
import asyncio
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

try:
    from agent_connector_sdk.manifest.live_contract import validate_live_tool_contract
    from agent_connector_sdk.manifest.loader import (
        load_manifest,
        load_tool_presets,
        require_valid_connector_package,
    )
    from agent_connector_sdk.manifest.tool_schema import (
        COMPATIBILITY_FINGERPRINT_ALGORITHM,
        canonical_input_schema,
        canonical_output_schema,
    )
    from fastmcp import Client

    from webarchiver.mcp_server import build_server
except ImportError as exc:
    raise SystemExit(
        "Install this project's declared dependencies before generating schemas"
    ) from exc

PACKAGE = ROOT / "webarchiver"


def _write_or_check(path: Path, value: dict, check: bool) -> None:
    text = (
        json.dumps(
            value,
            ensure_ascii=False,
            sort_keys=True,
            separators=(",", ":"),
            allow_nan=False,
        )
        + "\n"
    )
    if check:
        if not path.is_file() or path.read_text(encoding="utf-8") != text:
            raise SystemExit(f"Stale generated contract: {path.relative_to(ROOT)}")
    else:
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(text, encoding="utf-8")


async def generate(check: bool) -> None:
    async with Client(build_server(command_args=["--transport", "stdio"])) as client:
        tools = await client.list_tools()
    contracts = {}
    for tool in tools:
        contract = validate_live_tool_contract(tools, tool_name=tool.name)
        contracts[tool.name] = {
            "inputSchema": canonical_input_schema(tool),
            "outputSchema": canonical_output_schema(tool),
            "compatibility_sha256": contract.compatibility_sha256,
        }
    presets = load_tool_presets(PACKAGE / "connectors/mcp_source_presets.json")
    pinned = {
        preset.tool: contracts[preset.tool]["compatibility_sha256"]
        for preset in presets.values()
    }
    _write_or_check(
        ROOT / "schemas/mcp_tools.json",
        {
            "algorithm": COMPATIBILITY_FINGERPRINT_ALGORITHM,
            "tools": contracts,
        },
        check,
    )
    _write_or_check(
        PACKAGE / "connectors/tool_schema_fingerprints.json",
        {
            # The manifest carries the one connector identity, the fleet name.
            "connector": load_manifest(PACKAGE / "connector_manifest.yml").connector,
            "algorithm": COMPATIBILITY_FINGERPRINT_ALGORITHM,
            "tools": pinned,
        },
        check,
    )
    require_valid_connector_package(PACKAGE)


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--check", action="store_true")
    asyncio.run(generate(parser.parse_args().check))
