"""Auto-emit + lint the root uv workspace `[tool.uv.sources]` table.

CONCEPT:OS-5.72-workspace-uv-sources — workspace-source auto-emit + drift guard.

**Root cause this closes.** The root workspace `pyproject.toml`
(`[tool.uv.workspace]` + `[tool.uv.sources]`) was a hand-edited file: whenever a
new package was scaffolded, a human had to remember to add its
`{ workspace = true }` line, and every so often a package's OWN `pyproject.toml`
would instead declare a `path = "../sibling"` source for a sibling that is
*already* a `[tool.uv.workspace]` member — uv then sees two conflicting
resolutions for the same package (a workspace member AND a path dependency) and
the lock fails or silently picks one. Both failure modes are hand-edit drift.

This module is the single source of truth for both fixes:

* :func:`resolve_workspace_members` — expand `[tool.uv.workspace].members` globs
  (honoring `exclude`) into the concrete `(dir, package_name)` pairs uv actually
  resolves, by reading each candidate's own `pyproject.toml` `[project].name`.
* :func:`sync_uv_sources` — regenerate the root `[tool.uv.sources]` table so it
  contains **exactly** one `<name> = { workspace = true }` line per resolved
  member (sorted, idempotent) — the scaffolder calls this after creating a new
  package so the root file never needs a human edit again.
* :func:`find_path_source_drift` — the lint: scan every workspace member's OWN
  `pyproject.toml` for a `[tool.uv.sources]` entry that is `{ path = "..." }`
  (or any non-`workspace = true` form) naming another resolved workspace member.
  That shape is always wrong once both packages are workspace members — the
  root file's `workspace = true` is the only correct resolution, so any such
  entry is drift, full stop.

Both the sync and the lint touch **only** the `[tool.uv.sources]` table's text —
every other line of `pyproject.toml` is preserved byte-for-byte. No TOML writer
dependency is needed (or added) because the table's own grammar
(`name = { workspace = true }` per line) is simple enough to regenerate as text.
"""

from __future__ import annotations

import tomllib
from dataclasses import dataclass
from pathlib import Path

_SOURCES_HEADER = "[tool.uv.sources]"
_TABLE_HEADER_RE_PREFIX = "\n["


@dataclass(frozen=True)
class WorkspaceMember:
    """A resolved `[tool.uv.workspace]` member: its directory and package name."""

    path: Path
    name: str


def find_workspace_root(start: Path) -> Path | None:
    """Walk upward from *start* to the nearest `pyproject.toml` declaring
    `[tool.uv.workspace]` — the root workspace file this module maintains.
    """
    current = start.resolve()
    if current.is_file():
        current = current.parent
    for candidate in (current, *current.parents):
        pyproject = candidate / "pyproject.toml"
        if not pyproject.is_file():
            continue
        try:
            data = tomllib.loads(pyproject.read_text(encoding="utf-8"))
        except tomllib.TOMLDecodeError:
            continue
        if "workspace" in data.get("tool", {}).get("uv", {}):
            return candidate
    return None


def resolve_workspace_members(root: Path) -> list[WorkspaceMember]:
    """Expand `[tool.uv.workspace].members` globs into concrete members.

    A candidate directory counts as a member only if it has its own
    `pyproject.toml` with a `[project].name` — matching uv's own resolution —
    and is not covered by an `exclude` glob.
    """
    pyproject = root / "pyproject.toml"
    data = tomllib.loads(pyproject.read_text(encoding="utf-8"))
    workspace = data.get("tool", {}).get("uv", {}).get("workspace", {})
    patterns: list[str] = list(workspace.get("members", []))
    excludes: list[str] = list(workspace.get("exclude", []))

    excluded_dirs: set[Path] = set()
    for pattern in excludes:
        candidates = [root] if pattern in {"", "."} else root.glob(pattern)
        excluded_dirs.update(p.resolve() for p in candidates if p.is_dir())

    seen: dict[Path, WorkspaceMember] = {}
    for pattern in patterns:
        candidates = [root] if pattern in {"", "."} else root.glob(pattern)
        for candidate in sorted(candidates):
            if not candidate.is_dir():
                continue
            resolved = candidate.resolve()
            if resolved in excluded_dirs:
                continue
            member_pyproject = candidate / "pyproject.toml"
            if not member_pyproject.is_file():
                continue
            try:
                member_data = tomllib.loads(
                    member_pyproject.read_text(encoding="utf-8")
                )
            except tomllib.TOMLDecodeError:
                continue
            name = member_data.get("project", {}).get("name")
            if not name:
                continue
            seen[resolved] = WorkspaceMember(path=candidate, name=name)
    return sorted(seen.values(), key=lambda m: m.name)


def _render_sources_block(members: list[WorkspaceMember]) -> str:
    lines = [_SOURCES_HEADER]
    for member in members:
        lines.append(f"{member.name} = {{ workspace = true }}")
    return "\n".join(lines)


def sync_uv_sources(root: Path) -> bool:
    """Rewrite the root `[tool.uv.sources]` table to exactly one
    `{ workspace = true }` line per resolved workspace member.

    Returns True if the file content changed. Idempotent — a second call on an
    already-synced file is a no-op. Never writes a `path = "..."` source for a
    sibling; that shape is exactly what this function exists to eliminate.
    """
    pyproject = root / "pyproject.toml"
    original = pyproject.read_text(encoding="utf-8")
    members = resolve_workspace_members(root)
    new_block = _render_sources_block(members)

    header_idx = original.find(_SOURCES_HEADER)
    if header_idx == -1:
        # No existing table — append one after [tool.uv.workspace]'s block, or
        # at end of file if that block isn't found either.
        separator = "" if original.endswith("\n") else "\n"
        updated = f"{original}{separator}\n{new_block}\n"
    else:
        # Find the end of the table: the next top-level `[...]` header, or EOF.
        next_header_idx = original.find(_TABLE_HEADER_RE_PREFIX, header_idx + 1)
        tail = "" if next_header_idx == -1 else original[next_header_idx:]
        prefix = original[:header_idx]
        updated = f"{prefix}{new_block}\n{tail}" if tail else f"{prefix}{new_block}\n"

    if updated == original:
        return False
    pyproject.write_text(updated, encoding="utf-8")
    return True


# ── lint: reject a per-package path source for a sibling workspace member ──
@dataclass(frozen=True)
class SourceDriftFinding:
    """One drift finding: *pyproject_path* declares a bad source for *member*."""

    pyproject_path: Path
    member_name: str
    raw_value: str

    def __str__(self) -> str:  # pragma: no cover - human formatting only
        return (
            f"{self.pyproject_path}: [tool.uv.sources] {self.member_name!r} = "
            f"{self.raw_value!r} — a workspace member must use "
            f"{{ workspace = true }}, never a path source, for another member."
        )


def _describe_source_value(value: object) -> str:
    if isinstance(value, dict):
        return ", ".join(f"{k} = {v!r}" for k, v in value.items())
    return repr(value)


def find_path_source_drift(root: Path) -> list[SourceDriftFinding]:
    """Scan the root pyproject AND every resolved member's own pyproject.toml
    for a `[tool.uv.sources]` entry naming a workspace member as anything other
    than `{ workspace = true }` (most commonly a `path = "../sibling"` entry —
    the exact shape that caused the original path-vs-member conflicts).
    """
    members = resolve_workspace_members(root)
    member_names = {m.name for m in members}
    findings: list[SourceDriftFinding] = []

    candidates = [root / "pyproject.toml"] + [
        m.path / "pyproject.toml" for m in members
    ]
    for pyproject in candidates:
        if not pyproject.is_file():
            continue
        try:
            data = tomllib.loads(pyproject.read_text(encoding="utf-8"))
        except tomllib.TOMLDecodeError:
            continue
        sources = data.get("tool", {}).get("uv", {}).get("sources", {})
        for name, value in sources.items():
            if name not in member_names:
                continue  # not a workspace member — out of scope for this gate
            is_correct = isinstance(value, dict) and value.get("workspace") is True
            if not is_correct:
                findings.append(
                    SourceDriftFinding(
                        pyproject_path=pyproject,
                        member_name=name,
                        raw_value=_describe_source_value(value),
                    )
                )
    return sorted(findings, key=lambda f: (str(f.pyproject_path), f.member_name))


__all__ = [
    "SourceDriftFinding",
    "WorkspaceMember",
    "find_path_source_drift",
    "find_workspace_root",
    "resolve_workspace_members",
    "sync_uv_sources",
]


def _main(argv: list[str] | None = None) -> int:
    """``python workspace_sources.py sync [--root DIR]`` — regenerate the root
    `[tool.uv.sources]` table in place. The only supported subcommand; the
    scaffolder calls :func:`sync_uv_sources` directly instead of shelling out.
    """
    import argparse

    parser = argparse.ArgumentParser(description=_main.__doc__)
    parser.add_argument("command", choices=["sync"])
    parser.add_argument("--root", default=".", help="Search start (default: cwd).")
    args = parser.parse_args(argv)

    workspace_root = find_workspace_root(Path(args.root))
    if workspace_root is None:
        print(f"No [tool.uv.workspace] root found above {Path(args.root).resolve()}.")
        return 1
    changed = sync_uv_sources(workspace_root)
    print(
        f"{'Updated' if changed else 'Already in sync:'} "
        f"{workspace_root / 'pyproject.toml'}"
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(_main())
