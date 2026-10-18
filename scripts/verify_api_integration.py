#!/usr/bin/env python3
"""Fail-closed source/API/native MCP contract check for one generated connector.

Run with --source pointing to the pinned full OpenAPI document. This does not
replace operation-keyed mocked dispatch tests or certify live endpoint coverage.
"""

from __future__ import annotations

import argparse
import ast
import importlib
import json
import sys
import tomllib
from pathlib import Path


def find_package(root):
    project = tomllib.loads((root / "pyproject.toml").read_text())
    packages = project["tool"]["pipelines_hooks"]["packages"]
    if len(packages) != 1 or not packages[0].isidentifier():
        raise ValueError("Declare exactly one generated connector package")
    package = root / packages[0]
    client = package / "api/api_client_system.py"
    if not client.is_file() or client.is_symlink():
        raise ValueError("Missing generated api/api_client_system.py")
    tree = ast.parse(client.read_text())
    if not any(
        isinstance(node, ast.ClassDef) and node.name == "ApiClientSystem"
        for node in tree.body
    ):
        raise ValueError("Generated client must declare ApiClientSystem")
    if not (package / "mcp_server.py").is_file():
        raise ValueError("Missing generated mcp_server.py")
    return package


def arguments():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--source", type=Path, required=True)
    parser.add_argument("--root", type=Path, default=Path.cwd())
    parser.add_argument("--local", action="store_true")
    parser.add_argument("--pre-commit", action="store_true")
    parser.add_argument("--inspect", action="store_true")
    parser.add_argument("--client-budget", type=Path)
    parser.add_argument("--provider-overlay", type=Path)
    parser.add_argument("--expected-overlay-sha256")
    parser.add_argument("--evidence-root", type=Path)
    return parser.parse_args()


def main():
    args = arguments()
    root = args.root.resolve()
    package = find_package(root)
    sys.path.insert(0, str(root))
    checker = importlib.import_module(f"{package.name}.parity.check_openapi_parity")
    print(
        json.dumps(
            checker.check(
                args.source.resolve(),
                package,
                native=True,
                mode="inspect" if args.inspect else "ready",
                client_budget=args.client_budget,
                overlay_path=args.provider_overlay,
                expected_overlay_sha256=args.expected_overlay_sha256,
                evidence_root=args.evidence_root,
            ),
            indent=2,
            sort_keys=True,
        )
    )


if __name__ == "__main__":
    main()
