"""Fail CI/pre-commit if a package reintroduces a path source for a workspace member.

CONCEPT:OS-5.72-workspace-uv-sources — workspace-source drift guard (CLI).

A human report by
default, ``--check`` to exit non-zero for pre-commit/CI, ``--json`` for a
machine-readable findings list. The check itself lives in :mod:`workspace_sources`
(:func:`find_path_source_drift`) — this file is only the CLI entry point + the
``env-var-drift``-shaped pre-commit wiring.

Usage::

    python check_workspace_source_drift.py            # human report
    python check_workspace_source_drift.py --check     # exit 1 on drift (pre-commit)
    python check_workspace_source_drift.py --json      # machine-readable findings

Wire ``--check`` as a pre-commit hook (the mcp-builder scaffold does —
see the ``workspace-source-drift`` hook in ``scaffold_package.py``'s
``PRECOMMIT_CONFIG``).
"""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))

from workspace_sources import find_path_source_drift, find_workspace_root


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--root",
        default=".",
        help="Directory to start the workspace-root search from (default: cwd).",
    )
    parser.add_argument(
        "--check",
        action="store_true",
        help="Exit 1 if any drift is found (pre-commit/CI mode).",
    )
    parser.add_argument(
        "--json", action="store_true", help="Emit findings as machine-readable JSON."
    )
    args = parser.parse_args(argv)

    workspace_root = find_workspace_root(Path(args.root))
    if workspace_root is None:
        if args.json:
            print(json.dumps({"error": "no [tool.uv.workspace] root found"}))
        else:
            print(
                "No root pyproject.toml with [tool.uv.workspace] found above "
                f"{Path(args.root).resolve()} — nothing to check."
            )
        return 0

    findings = find_path_source_drift(workspace_root)

    if args.json:
        print(
            json.dumps(
                [
                    {
                        "pyproject": str(f.pyproject_path),
                        "member": f.member_name,
                        "value": f.raw_value,
                    }
                    for f in findings
                ],
                indent=2,
            )
        )
    elif not findings:
        print(f"OK — no workspace-source drift under {workspace_root}.")
    else:
        print(f"Workspace-source drift under {workspace_root}:\n")
        for finding in findings:
            print(f"  - {finding}")
        print(
            f"\n{len(findings)} finding(s). Fix: remove the path/non-workspace "
            "source and let the root [tool.uv.sources] table's "
            "`{ workspace = true }` entry resolve it — run "
            "`python workspace_sources.py sync` (or re-run the scaffolder) to "
            "regenerate the root table."
        )

    if args.check:
        return 1 if findings else 0
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
