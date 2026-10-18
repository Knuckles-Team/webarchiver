#!/usr/bin/env python3
"""Reject retired connector APIs in a generated SDK-based project.

This static check needs no installed connector dependencies. A connector is
MCP-only and depends on agent-connector-sdk alone: the retired control-plane
package may be neither imported nor declared as a dependency.
"""

from __future__ import annotations

import argparse
import ast
import re
import tomllib
from pathlib import Path

# Assembled so repository-wide searches for the retired dependency stay clean.
RETIRED_PACKAGE = "agent" + "_utilities"


def _imports(node: ast.AST) -> list[str]:
    if isinstance(node, ast.Import):
        return [alias.name for alias in node.names]
    if isinstance(node, ast.ImportFrom):
        return [node.module or ""]
    if not isinstance(node, ast.Call) or not node.args:
        return []
    function = node.func
    dynamic_import = (
        isinstance(function, ast.Name) and function.id == "__import__"
    ) or (isinstance(function, ast.Attribute) and function.attr == "import_module")
    argument = node.args[0]
    if (
        dynamic_import
        and isinstance(argument, ast.Constant)
        and isinstance(argument.value, str)
    ):
        return [argument.value]
    return []


def _module_violations(path: Path, root: Path) -> list[str]:
    relative = path.relative_to(root)
    try:
        tree = ast.parse(path.read_text(encoding="utf-8"), filename=str(relative))
    except (SyntaxError, UnicodeError) as exc:
        return [f"{relative}: cannot parse Python: {exc}"]
    violations = []
    for node in ast.walk(tree):
        for name in _imports(node):
            if name == RETIRED_PACKAGE or name.startswith(RETIRED_PACKAGE + "."):
                violations.append(
                    f"{relative}:{node.lineno}: retired connector import {name}"
                )
        if isinstance(node, ast.Constant) and node.value == "MCP_TOOL_MODE":
            violations.append(
                f"{relative}:{node.lineno}: retired MCP_TOOL_MODE setting"
            )
    return violations


def check_project(root: Path, package: str) -> list[str]:
    """Return actual AST/import and direct dependency contract violations."""
    if not package.isidentifier():
        return ["package must be a Python package directory name"]
    package_root = root / package
    if not package_root.is_dir():
        return [f"package directory does not exist: {package}"]
    project = tomllib.loads((root / "pyproject.toml").read_text(encoding="utf-8"))[
        "project"
    ]
    dependencies = project.get("dependencies", [])
    names = {
        re.split(r"[<>=!~\[; ]", value.lower().replace("_", "-"))[0]
        for value in dependencies
    }
    violations = []
    if "agent-connector-sdk" not in names:
        violations.append("pyproject.toml: connector requires agent-connector-sdk")
    if RETIRED_PACKAGE.replace("_", "-") in names:
        violations.append(
            "pyproject.toml: connectors depend on agent-connector-sdk only"
        )
    for extra, values in project.get("optional-dependencies", {}).items():
        if any(RETIRED_PACKAGE.replace("_", "-") in value.lower() for value in values):
            violations.append(
                f"pyproject.toml: extra {extra!r} pulls the retired package"
            )
    if any(
        re.match(r"epistemic[-_]graph\[[^]]*\bfull\b", value.lower())
        for value in dependencies
    ):
        violations.append(
            "pyproject.toml: connector must not require the full engine extra"
        )
    for path in sorted(package_root.rglob("*.py")):
        violations.extend(_module_violations(path, root))
    return violations


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("root", type=Path, nargs="?", default=Path("."))
    parser.add_argument("--package", required=True)
    args = parser.parse_args()
    violations = check_project(args.root, args.package)
    for violation in violations:
        print(violation)
    if not violations:
        print("Connector SDK contract: passed")
    return int(bool(violations))


if __name__ == "__main__":
    raise SystemExit(main())
