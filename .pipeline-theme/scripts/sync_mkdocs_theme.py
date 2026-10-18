"""Synchronize generated ecosystem MkDocs theme files into a consumer repo."""

from __future__ import annotations

import argparse
import re
import sys
from dataclasses import dataclass
from pathlib import Path
from typing import Literal


@dataclass(frozen=True)
class ThemeFile:
    """A canonical source file and its generated consumer-relative path."""

    source: str
    destination: str
    content_relative: bool = True


THEME_FILES = (
    ThemeFile("extra.css", "stylesheets/extra.css"),
    ThemeFile("assets/graph-mark.svg", "assets/graph-mark.svg"),
    ThemeFile("assets/favicon.svg", "assets/favicon.svg"),
    ThemeFile(
        "assets/brands/epistemic-graph-logo-v1.png",
        "assets/brands/epistemic-graph-logo-v1.png",
    ),
    ThemeFile(
        "assets/brands/agent-utilities-logo-v1.png",
        "assets/brands/agent-utilities-logo-v1.png",
    ),
    ThemeFile("assets/brands/arbora-logo-v1.png", "assets/brands/arbora-logo-v1.png"),
    ThemeFile(
        "assets/brands/agent-connector-sdk-logo-v1.png",
        "assets/brands/agent-connector-sdk-logo-v1.png",
    ),
    ThemeFile(
        "assets/brands/agent-webui-logo-v1.png",
        "assets/brands/agent-webui-logo-v1.png",
    ),
    ThemeFile(
        "assets/brands/geniusbot-logo-v1.png", "assets/brands/geniusbot-logo-v1.png"
    ),
    ThemeFile(
        "assets/brands/agent-terminal-ui-logo-v1.png",
        "assets/brands/agent-terminal-ui-logo-v1.png",
    ),
    ThemeFile("glossary.md", "glossary.md"),
)


RUNTIME_DIAGRAM_URL = (
    "https://raw.githubusercontent.com/Knuckles-Team/epistemic-graph/main/"
    "docs/assets/runtime-architecture.svg"
)
# Any reference to the diagram file; the only accepted target is RUNTIME_DIAGRAM_URL.
RUNTIME_DIAGRAM_REFERENCE = re.compile(r"[^\s\"'()<>]*runtime-architecture\.svg")
PAGE_SUFFIXES = {".md", ".html", ".yml", ".yaml"}


class ThemeSyncError(Exception):
    """The source, destination, or content-source contract is invalid."""


def _safe_relative_path(value: str, label: str) -> Path:
    path = Path(value)
    if (
        path.is_absolute()
        or not path.parts
        or any(part in {".", ".."} for part in path.parts)
    ):
        raise ThemeSyncError(f"{label} must be a contained relative path")
    return path


def _contained(root: Path, relative: Path, label: str) -> Path:
    base = root.resolve()
    result = (base / relative).resolve()
    if not result.is_relative_to(base):
        raise ThemeSyncError(f"{label} escapes the repository root")
    return result


def _check_file(destination: Path, expected: bytes, repository: Path) -> str | None:
    """Describe how ``destination`` diverges from ``expected``, or ``None`` when it matches."""
    try:
        actual = destination.read_bytes()
    except OSError:
        return f"missing generated file: {destination.relative_to(repository)}"
    if actual != expected:
        return f"generated file differs: {destination.relative_to(repository)}"
    return None


def _runtime_reference_mismatches(content_root: Path, repository: Path) -> list[str]:
    """Pages may show the runtime diagram only through the single canonical URL."""
    mismatches: list[str] = []
    if not content_root.is_dir():
        return mismatches
    for page in sorted(content_root.rglob("*")):
        if page.suffix not in PAGE_SUFFIXES or not page.is_file():
            continue
        text = page.read_text(encoding="utf-8", errors="replace")
        if any(
            match.group(0) != RUNTIME_DIAGRAM_URL
            for match in RUNTIME_DIAGRAM_REFERENCE.finditer(text)
        ):
            mismatches.append(
                f"runtime diagram must be referenced as {RUNTIME_DIAGRAM_URL}: "
                f"{page.relative_to(repository)}"
            )
    return mismatches


def sync_theme(
    *,
    source_root: Path,
    repository_root: Path,
    content_source: str,
    mode: Literal["sync", "check"],
) -> list[str]:
    """Copy canonical files in ``sync`` mode or return mismatches in ``check`` mode."""
    content_relative = _safe_relative_path(content_source, "content-source")
    repository = repository_root.resolve()
    content_root = _contained(repository, content_relative, "content-source")
    source = (source_root / "templates" / "mkdocs-theme").resolve()
    if not source.is_dir():
        raise ThemeSyncError(f"canonical theme directory does not exist: {source}")

    mismatches = _sync_files(source, content_root, repository, mode=mode)
    if mode == "check":
        mismatches.extend(_runtime_reference_mismatches(content_root, repository))
    return mismatches


def _sync_files(
    source: Path,
    content_root: Path,
    repository: Path,
    *,
    mode: Literal["sync", "check"],
) -> list[str]:
    """Write or compare every theme file and describe each divergence."""
    mismatches: list[str] = []
    for item in THEME_FILES:
        source_file = source / item.source
        if not source_file.is_file():
            raise ThemeSyncError(f"canonical theme file does not exist: {source_file}")
        destination_root = content_root if item.content_relative else repository
        destination = _contained(
            destination_root, Path(item.destination), item.destination
        )
        expected = source_file.read_bytes()
        if mode == "check":
            mismatch = _check_file(destination, expected, repository)
            if mismatch:
                mismatches.append(mismatch)
            continue
        destination.parent.mkdir(parents=True, exist_ok=True)
        destination.write_bytes(expected)
    return mismatches


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("mode", choices=("sync", "check"))
    parser.add_argument(
        "--root", type=Path, default=Path.cwd(), help="consumer repository root"
    )
    parser.add_argument(
        "--content-source",
        default="docs",
        help="consumer MkDocs content directory (normally docs or pages)",
    )
    parser.add_argument(
        "--source-root",
        type=Path,
        default=Path(__file__).resolve().parents[1],
        help="pipelines checkout containing templates/mkdocs-theme",
    )
    args = parser.parse_args(argv)
    try:
        mismatches = sync_theme(
            source_root=args.source_root,
            repository_root=args.root,
            content_source=args.content_source,
            mode=args.mode,
        )
    except (OSError, ThemeSyncError) as exc:
        print(f"shared MkDocs theme: CANNOT RUN: {exc}", file=sys.stderr)
        return 2
    if mismatches:
        print("shared MkDocs theme: generated files are out of sync:", file=sys.stderr)
        for mismatch in mismatches:
            print(f"  - {mismatch}", file=sys.stderr)
        return 1
    print(f"shared MkDocs theme: {args.mode} complete")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
