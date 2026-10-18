#!/usr/bin/env python3
"""Generate deterministic, privacy-safe agent documentation artifacts.

The generator reads the source Markdown selected by ``mkdocs.yml``.  It never
imports a provider package or parses generated HTML, so a documentation build
cannot accidentally become a runtime capability oracle.  ``docs/agent-readiness.json``
is an explicit operator input; its applicability and content-signal choices are
copied into the provenance manifest rather than guessed.
"""

from __future__ import annotations

import argparse
import hashlib
import ipaddress
import json
import os
import re
import sys
import tempfile
from dataclasses import dataclass
from pathlib import Path, PurePosixPath
from typing import Any
from urllib.parse import urljoin, urlsplit

try:
    import yaml
except ImportError as exc:  # pragma: no cover - exercised by package users
    yaml = None
    _YAML_IMPORT_ERROR = exc
else:
    _YAML_IMPORT_ERROR = None


if yaml is not None:

    class _MkdocsLoader(yaml.SafeLoader):
        """Safe YAML loader that treats MkDocs Python-name tags as strings."""

    def _construct_python_name(loader: Any, suffix: str, node: Any) -> str:
        if not isinstance(node, yaml.ScalarNode):
            raise yaml.YAMLError("python-name tag must be scalar")
        return suffix

    _MkdocsLoader.add_multi_constructor(
        "tag:yaml.org,2002:python/name:", _construct_python_name
    )
else:  # pragma: no cover - only used when the optional parser is absent
    _MkdocsLoader = None


SCHEMA_VERSION = "agent-readiness/v1"
GENERATOR_VERSION = "1.0.0"
MAX_CURATED_CHARS = 32_000
MAX_FULL_CHARS = 500_000
MAX_SUMMARY_CHARS = 1_200
MAX_SOURCE_BYTES = 2_000_000
STANDARD_KINDS = frozenset({"rfc", "draft", "convention"})
APPLICABILITY_CATEGORIES = (
    "content",
    "discoverability",
    "access_policy",
    "capabilities",
    "errors",
    "provenance",
    "measurement",
    "deployment",
)
CAPABILITY_NAMES = frozenset({"api", "mcp", "a2a", "skills"})
CAPABILITY_DISCOVERY_VERSION = "capability-discovery/v1"
API_CATALOG_PROFILE = "https://www.rfc-editor.org/info/rfc9727"
API_CATALOG_REL = "api-catalog"
API_CATALOG_MEDIA_TYPE = "application/linkset+json"
MCP_SERVER_CARD_VERSION = "mcp-server-card/v1-experimental"
AGENT_SKILLS_VERSION = "agent-skills/v1"
_OAUTH_METADATA_FIELDS = {
    "oauth_protected_resource": "oauth-protected-resource",
    "oauth_authorization_server": "oauth-authorization-server",
}
#: Transports an applicable served surface may declare. ``stdio`` exists only
#: for MCP; an A2A agent is always reached over a network binding.
SURFACE_TRANSPORTS = {
    "mcp": frozenset({"stdio", "streamable-http", "sse"}),
    "a2a": frozenset({"jsonrpc", "http-json", "grpc"}),
}
#: ``local``: a client launches the server process itself (stdio);
#: ``in-cluster``: reachable only inside the deployment network under a
#: ``service_identity``; ``public``: reachable at a public HTTPS ``endpoint``.
REACHABILITY_VALUES = frozenset({"local", "in-cluster", "public"})
NON_PUBLIC_REACHABILITY = frozenset({"local", "in-cluster"})
TRANSPORT_KEYS = frozenset({"transport", "reachability", "service_identity"})
SERVICE_IDENTITY_PATTERN = re.compile(
    r"[a-z](?:[a-z0-9-]{0,61}[a-z0-9])?(?:\.[a-z0-9](?:[a-z0-9-]{0,61}[a-z0-9])?){1,4}"
)
SAFE_SIGNAL_POLICIES = frozenset({"unset", "operator-reviewed"})
SECRET_PATTERN = re.compile(
    r"(?ix)(?:api[_-]?key|access[_-]?token|refresh[_-]?token|password|"
    r"secret(?:[_-][a-z0-9]+)*|token(?:[_-][a-z0-9]+)*)"
    r"[\"'`]?\s*[:=]\s*(?!<|\$|env://|\*|redacted\b|none\b|false\b|true\b)"
    r"[\"']?[A-Za-z0-9_./+=:-]{12,}[\"']?"
)
BEARER_PATTERN = re.compile(r"(?i)\bbearer\s+[A-Za-z0-9._~+/=-]{12,}")


class ReadinessError(ValueError):
    """A privacy, provenance, schema, or deterministic-generation rejection."""


@dataclass(frozen=True)
class Page:
    """One leaf selected by the exact MkDocs navigation order."""

    title: str
    source: str
    url: str
    markdown_url: str
    summary: str
    digest: str
    size: int
    section: str


@dataclass(frozen=True)
class Section:
    """A top-level MkDocs navigation section."""

    title: str
    slug: str
    pages: tuple[Page, ...]


def _fail(message: str) -> None:
    raise ReadinessError(message)


def _regular_file(path: Path, label: str) -> bytes:
    try:
        metadata = path.lstat()
    except OSError as exc:
        raise ReadinessError(f"{label}-unavailable") from exc
    if path.is_symlink() or not path.is_file() or metadata.st_nlink != 1:
        _fail(f"{label}-not-regular")
    try:
        payload = path.read_bytes()
    except OSError as exc:
        raise ReadinessError(f"{label}-unreadable") from exc
    if len(payload) > MAX_SOURCE_BYTES:
        _fail(f"{label}-oversize")
    return payload


def _safe_relative(root: Path, raw: object, label: str) -> Path:
    if (
        not isinstance(raw, str)
        or not raw
        or "\x00" in raw
        or "\\" in raw
        or "?" in raw
        or "#" in raw
    ):
        _fail(f"{label}-path-invalid")
    relative = PurePosixPath(raw)
    if relative.is_absolute() or not relative.parts:
        _fail(f"{label}-path-invalid")
    if any(part in {"", ".", ".."} for part in relative.parts):
        _fail(f"{label}-path-invalid")
    try:
        root_stat = root.lstat()
    except OSError as exc:
        raise ReadinessError(f"{label}-root-unavailable") from exc
    if root.is_symlink() or not root.is_dir() or root_stat.st_nlink < 1:
        _fail(f"{label}-root-invalid")
    candidate = root.joinpath(*relative.parts)
    cursor = root
    for part in relative.parts:
        cursor /= part
        try:
            if cursor.is_symlink():
                _fail(f"{label}-symlink")
        except OSError as exc:
            raise ReadinessError(f"{label}-unavailable") from exc
    try:
        resolved_root = root.resolve(strict=True)
        resolved = candidate.resolve(strict=True)
        resolved.relative_to(resolved_root)
    except (OSError, ValueError) as exc:
        raise ReadinessError(f"{label}-containment") from exc
    return resolved


def _safe_existing_path(root: Path, path: Path, label: str) -> Path:
    """Resolve an input only after rejecting absolute escapes and symlinks."""

    if path.is_absolute():
        try:
            relative = path.absolute().relative_to(root)
        except ValueError as exc:
            raise ReadinessError(f"{label}-containment") from exc
        raw = relative.as_posix()
    else:
        raw = path.as_posix()
    return _safe_relative(root, raw, label)


def _public_url(raw: object, label: str, *, directory: bool = False) -> str:
    if not isinstance(raw, str) or len(raw) > 2048:
        _fail(f"{label}-url-invalid")
    try:
        parsed = urlsplit(raw)
        host = parsed.hostname.rstrip(".").lower() if parsed.hostname else ""
        port = parsed.port
    except ValueError as exc:
        raise ReadinessError(f"{label}-url-invalid") from exc
    if parsed.scheme != "https" or parsed.username or parsed.password:
        _fail(f"{label}-url-invalid")
    if parsed.query or parsed.fragment or not host or port:
        _fail(f"{label}-url-invalid")
    if host in {"localhost", "local", "internal"} or host.endswith(
        (".local", ".localhost", ".internal", ".home", ".arpa")
    ):
        _fail(f"{label}-private-url")
    try:
        address = ipaddress.ip_address(host)
    except ValueError:
        address = None
    if address is not None and (
        address.is_private
        or address.is_loopback
        or address.is_link_local
        or address.is_reserved
        or address.is_unspecified
        or address.is_multicast
    ):
        _fail(f"{label}-private-url")
    if not parsed.netloc or (
        directory and parsed.path and not parsed.path.endswith("/")
    ):
        _fail(f"{label}-url-invalid")
    return raw.rstrip("/") + "/" if directory else raw


def _scan_safe_text(text: str, label: str) -> None:
    if SECRET_PATTERN.search(text) or BEARER_PATTERN.search(text):
        _fail(f"{label}-secret-like-value")
    for match in re.finditer(r"https?://[^\s)\]>\"']+", text):
        value = match.group(0).rstrip(".,;:")
        try:
            parsed = urlsplit(value)
            host = parsed.hostname.rstrip(".").lower() if parsed.hostname else ""
        except ValueError as exc:
            raise ReadinessError(f"{label}-url-invalid") from exc
        if parsed.username or parsed.password:
            _fail(f"{label}-credential-url")
        if parsed.query and re.search(
            r"(?i)(?:token|secret|password|api[_-]?key|credential|auth)=",
            parsed.query,
        ):
            _fail(f"{label}-credential-url")
        if host:
            if host in {"localhost", "local", "internal"} or host.endswith(
                (".local", ".localhost", ".internal", ".home", ".arpa")
            ):
                _fail(f"{label}-private-url")
            try:
                address = ipaddress.ip_address(host)
            except ValueError:
                address = None
            if address is not None and (
                address.is_private
                or address.is_loopback
                or address.is_link_local
                or address.is_reserved
                or address.is_unspecified
                or address.is_multicast
            ):
                _fail(f"{label}-private-url")


def _scan_json_strings(value: object, label: str) -> None:
    """Check capability metadata without importing the provider/runtime."""

    if isinstance(value, str):
        _scan_safe_text(value, label)
    elif isinstance(value, dict):
        for key, child in value.items():
            if not isinstance(key, str):
                _fail(f"{label}-metadata-invalid")
            _scan_json_strings(child, label)
    elif isinstance(value, list):
        for child in value:
            _scan_json_strings(child, label)
    elif value is not None and not isinstance(value, (bool, int, float)):
        _fail(f"{label}-metadata-invalid")


def _validate_capability_artifact(
    root: Path, name: str, artifact: str
) -> dict[str, str]:
    artifact_path = _safe_relative(root, artifact, f"{name}-artifact")
    payload = _regular_file(artifact_path, f"{name}-artifact")
    try:
        metadata = json.loads(payload.decode("utf-8"))
    except (UnicodeDecodeError, json.JSONDecodeError) as exc:
        raise ReadinessError(f"{name}-artifact-invalid-json") from exc
    if not isinstance(metadata, dict):
        _fail(f"{name}-artifact-invalid")
    allowed_keys = {
        "applicable",
        "http_transport",
        "source",
        "surface",
        "version",
    }
    if set(metadata) - allowed_keys:
        _fail(f"{name}-artifact-schema-invalid")
    if metadata.get("applicable") is not True:
        _fail(f"{name}-capability-not-proven")
    if metadata.get("surface") != name:
        _fail(f"{name}-artifact-schema-invalid")
    if "http_transport" in metadata and (
        name != "mcp" or type(metadata["http_transport"]) is not bool
    ):
        _fail(f"{name}-artifact-schema-invalid")
    if "version" in metadata and (
        not isinstance(metadata["version"], str) or not metadata["version"]
    ):
        _fail(f"{name}-artifact-schema-invalid")
    source = metadata.get("source")
    if not isinstance(source, str):
        _fail(f"{name}-artifact-source-invalid")
    source_path = _safe_relative(root, source, f"{name}-artifact-source")
    try:
        source_metadata = source_path.lstat()
    except OSError as exc:
        raise ReadinessError(f"{name}-artifact-source-unavailable") from exc
    if (
        source_path.is_symlink()
        or not source_path.is_file()
        or source_metadata.st_nlink != 1
    ):
        _fail(f"{name}-artifact-source-invalid")
    source_payload = _regular_file(source_path, f"{name}-artifact-source")
    _scan_json_strings(metadata, f"{name}-artifact")
    evidence = {
        "artifact": artifact,
        "artifact_sha256": hashlib.sha256(payload).hexdigest(),
        "source": source,
        "source_sha256": hashlib.sha256(source_payload).hexdigest(),
    }
    if metadata.get("http_transport") is True:
        evidence["http_transport"] = "true"
    return evidence


def _validate_oauth_metadata(root: Path, field: str, raw: object) -> str:
    """Bind optional OAuth discovery to the exact well-known JSON authority."""
    if not isinstance(raw, str):
        _fail(f"{field}-metadata-invalid")
    expected = f".well-known/{_OAUTH_METADATA_FIELDS[field]}"
    if raw != expected:
        _fail(f"{field}-metadata-unbound")
    path = _safe_relative(root, raw, f"{field}-metadata")
    payload = _regular_file(path, f"{field}-metadata")
    try:
        metadata = json.loads(payload.decode("utf-8"))
    except (UnicodeDecodeError, json.JSONDecodeError) as exc:
        raise ReadinessError(f"{field}-metadata-invalid-json") from exc
    if not isinstance(metadata, dict):
        _fail(f"{field}-metadata-invalid")
    _scan_json_strings(metadata, f"{field}-metadata")
    return raw


def _validate_skills_path(root: Path, raw: object) -> str:
    if not isinstance(raw, str):
        _fail("skills-path-required")
    skills_root = _safe_relative(root, raw, "skills-path")
    try:
        entries = list(skills_root.iterdir())
    except OSError as exc:
        raise ReadinessError("skills-path-unavailable") from exc
    if not any(
        entry.is_dir()
        and not entry.is_symlink()
        and (entry / "SKILL.md").is_file()
        and not (entry / "SKILL.md").is_symlink()
        for entry in entries
    ):
        _fail("skills-path-not-proven")
    return raw


def _skill_entry(root: Path, skills_root: Path, directory: Path) -> dict[str, str]:
    """Read only the bound skill identity/description for public discovery."""
    skill_path = directory / "SKILL.md"
    payload = _regular_file(skill_path, "skill")
    try:
        text = payload.decode("utf-8")
    except UnicodeDecodeError as exc:
        raise ReadinessError("skill-encoding-invalid") from exc
    description = ""
    lines = text.splitlines()
    if lines and lines[0].strip() == "---":
        try:
            end = next(
                i for i, line in enumerate(lines[1:], 1) if line.strip() == "---"
            )
        except StopIteration as exc:
            raise ReadinessError("skill-frontmatter-invalid") from exc
        for line in lines[1:end]:
            if line.strip().startswith("description:"):
                description = line.split(":", 1)[1].strip().strip("\"'")
                break
    if not description:
        for line in lines:
            if line.startswith("#"):
                description = line.lstrip("#").strip()
                break
    name = directory.name
    relative = skill_path.relative_to(root).as_posix()
    _scan_safe_text(name, "skill-discovery")
    _scan_safe_text(relative, "skill-discovery")
    _scan_safe_text(description, "skill-discovery")
    entry = {"name": name, "path": relative}
    if description:
        entry["description"] = description[:400]
    return entry


def _render_agent_skills_index(root: Path, path: str) -> str:
    skills_root = _safe_relative(root, path, "skills-path")
    entries = []
    for directory in sorted(skills_root.iterdir(), key=lambda item: item.name):
        if (
            directory.is_dir()
            and not directory.is_symlink()
            and not directory.name.startswith(".")
            and (directory / "SKILL.md").is_file()
            and not (directory / "SKILL.md").is_symlink()
        ):
            entries.append(_skill_entry(root, skills_root, directory))
    if not entries:
        _fail("skills-path-not-proven")
    return (
        json.dumps(
            {
                "schema_version": AGENT_SKILLS_VERSION,
                "skills": entries,
            },
            indent=2,
            sort_keys=True,
        )
        + "\n"
    )


def _discovery_link(
    href: str,
    *,
    rel: str = "item",
    media_type: str = "application/json",
    title: str | None = None,
) -> dict[str, str]:
    link = {"href": href, "rel": rel, "type": media_type}
    if title:
        link["title"] = title
    return link


def _publicly_discoverable(capability: dict[str, Any]) -> bool:
    """Public discovery documents never advertise a surface declared
    ``local`` or ``in-cluster``; an undeclared reachability keeps v1 behavior."""

    return (
        capability.get("applicable") is True
        and capability.get("reachability") not in NON_PUBLIC_REACHABILITY
    )


def _render_mcp_server_card(
    readiness: dict[str, Any], *, project_name: str
) -> str | None:
    mcp = readiness["capabilities"].get("mcp", {})
    evidence = readiness["capability_evidence"].get("mcp", {})
    if not _publicly_discoverable(mcp) or evidence.get("http_transport") != "true":
        return None
    _scan_safe_text(project_name, "mcp-server-card")
    return (
        json.dumps(
            {
                "schema_version": MCP_SERVER_CARD_VERSION,
                "experimental": True,
                "server": {"name": project_name},
                "transports": ["streamable-http", "sse"],
                "source": "docs/capabilities/mcp.json",
            },
            indent=2,
            sort_keys=True,
        )
        + "\n"
    )


def _render_api_catalog(readiness: dict[str, Any]) -> str | None:
    capabilities = readiness["capabilities"]
    evidence = readiness["capability_evidence"]
    public_a2a = _publicly_discoverable(capabilities["a2a"])
    public_mcp_http = (
        _publicly_discoverable(capabilities["mcp"])
        and evidence.get("mcp", {}).get("http_transport") == "true"
    )
    if not (public_a2a or public_mcp_http):
        return None
    links: list[dict[str, str]] = []
    if capabilities["api"].get("applicable") is True:
        links.append(_discovery_link(capabilities["api"]["artifact"]))
    if public_a2a:
        links.append(_discovery_link("a2a.json", title="A2A agent card"))
        links.append(
            _discovery_link(
                capabilities["a2a"]["artifact"], title="A2A capability authority"
            )
        )
    if public_mcp_http:
        links.append(
            _discovery_link(
                ".well-known/mcp-server-card.json",
                title="Experimental MCP Server Card",
            )
        )
    if capabilities["skills"].get("applicable") is True:
        links.append(
            _discovery_link(".well-known/agent-skills.json", title="Agent Skills")
        )
    for field in _OAUTH_METADATA_FIELDS:
        for authority in evidence.values():
            metadata_path = authority.get(field)
            if metadata_path:
                title = (
                    "OAuth 2.0 Protected Resource Metadata (RFC 9728)"
                    if field == "oauth_protected_resource"
                    else "OAuth 2.0 Authorization Server Metadata (RFC 8414)"
                )
                links.append(
                    _discovery_link(metadata_path, rel="describedby", title=title)
                )
                break
    if not links:
        return None
    item_links = [
        {key: value for key, value in link.items() if key != "rel"}
        for link in links
        if link["rel"] == "item"
    ]
    describedby_links = [
        {key: value for key, value in link.items() if key != "rel"}
        for link in links
        if link["rel"] == "describedby"
    ]
    linkset: dict[str, Any] = {"anchor": ".", "item": item_links}
    if describedby_links:
        linkset["describedby"] = describedby_links
    return (
        json.dumps(
            {"linkset": [linkset], "profile": API_CATALOG_PROFILE},
            indent=2,
            sort_keys=True,
        )
        + "\n"
    )


def _slug(value: str) -> str:
    result = re.sub(r"[^a-z0-9]+", "-", value.lower()).strip("-")
    if not result:
        _fail("nav-section-invalid")
    return result


def _summary(markdown: str, limit: int) -> str:
    lines = markdown.splitlines()
    in_frontmatter = bool(lines and lines[0].strip() == "---")
    if in_frontmatter:
        try:
            end = next(
                i for i, line in enumerate(lines[1:], 1) if line.strip() == "---"
            )
        except StopIteration:
            _fail("markdown-frontmatter-invalid")
        lines = lines[end + 1 :]
    chunks: list[str] = []
    for line in lines:
        stripped = line.strip()
        if not stripped or stripped.startswith(("#", "<!--", "```")):
            if chunks:
                break
            continue
        chunks.append(stripped)
    value = re.sub(r"[`*_]", "", " ".join(chunks))
    value = re.sub(r"\[([^]]+)\]\([^)]*\)", r"\1", value)
    return value[:limit].strip()


def _static_page_url(
    site_url: str, source: str, *, use_directory_urls: bool = True
) -> str:
    """Map a Markdown source to the URL MkDocs serves it from.

    With MkDocs' default ``use_directory_urls: true`` every page is a
    directory URL; with ``false`` a page is its ``.html`` file (an
    ``index.md`` is its directory's ``index.html``), so the canonical URL
    names the file the site build actually writes.
    """

    parts = list(PurePosixPath(source).parts)
    if not use_directory_urls:
        if parts[-1] == "index.md":
            parts[-1] = "index.html"
        else:
            parts[-1] = PurePosixPath(parts[-1]).with_suffix(".html").name
        return urljoin(site_url, "/".join(parts))
    if parts[-1] == "index.md":
        parts.pop()
    else:
        parts[-1] = PurePosixPath(parts[-1]).with_suffix("").name
    static_path = "/".join(parts)
    if static_path:
        static_path += "/"
    return urljoin(site_url, static_path)


def _static_markdown_url(site_url: str, source: str) -> str:
    """Map a source to an unambiguous static Markdown fallback target."""

    parts = list(PurePosixPath(source).parts)
    if parts[-1] != "index.md":
        parts[-1] = PurePosixPath(parts[-1]).with_suffix("").name
        parts.append("index.md")
    return urljoin(site_url, "/".join(parts))


def _load_mkdocs(root: Path) -> tuple[dict[str, Any], bytes]:
    config_path = _safe_relative(root, "mkdocs.yml", "mkdocs")
    payload = _regular_file(config_path, "mkdocs")
    if yaml is None:
        raise ReadinessError("mkdocs-yaml-parser-unavailable") from _YAML_IMPORT_ERROR
    try:
        config = yaml.load(payload.decode("utf-8"), Loader=_MkdocsLoader)
    except (UnicodeDecodeError, yaml.YAMLError) as exc:
        raise ReadinessError("mkdocs-invalid-yaml") from exc
    if not isinstance(config, dict) or not isinstance(config.get("nav"), list):
        _fail("mkdocs-nav-invalid")
    return config, payload


def _flatten_nav(nav: list[Any]) -> list[tuple[str, str, str]]:
    leaves: list[tuple[str, str, str]] = []

    def visit(items: list[Any], section: str) -> None:
        for item in items:
            if isinstance(item, str):
                leaves.append(
                    (Path(item).stem.replace("-", " ").title(), item, section)
                )
                continue
            if not isinstance(item, dict) or len(item) != 1:
                _fail("mkdocs-nav-entry-invalid")
            title, child = next(iter(item.items()))
            if not isinstance(title, str) or not title.strip():
                _fail("mkdocs-nav-title-invalid")
            if isinstance(child, str):
                leaves.append((title, child, section or title))
            elif isinstance(child, list):
                visit(child, section or title)
            else:
                _fail("mkdocs-nav-entry-invalid")

    visit(nav, "")
    if not leaves:
        _fail("mkdocs-nav-empty")
    return leaves


def _validate_standards(value: object) -> list[dict[str, str]]:
    if not isinstance(value, list) or not value:
        _fail("maturity-standards-required")
    normalized: list[dict[str, str]] = []
    seen: set[str] = set()
    for entry in value:
        if not isinstance(entry, dict) or set(entry) != {"id", "kind", "level"}:
            _fail("maturity-entry-invalid")
        identifier = entry.get("id")
        kind = entry.get("kind")
        level = entry.get("level")
        if (
            not isinstance(identifier, str)
            or not re.fullmatch(r"[A-Za-z0-9][A-Za-z0-9 .:_/-]{1,127}", identifier)
            or identifier in seen
            or kind not in STANDARD_KINDS
            or not isinstance(level, str)
            or level not in {"normative", "draft", "advisory"}
        ):
            _fail("maturity-entry-invalid")
        if kind == "rfc" and level != "normative":
            _fail("maturity-rfc-level-invalid")
        if kind == "draft" and level == "normative":
            _fail("maturity-draft-level-invalid")
        seen.add(identifier)
        normalized.append({"id": identifier, "kind": kind, "level": level})
    return normalized


def _validate_surface_reachability(name: str, entry: dict[str, Any]) -> None:
    """Validate how an applicable MCP/A2A surface is actually reached.

    Without ``transport``/``reachability`` a declaration keeps its original v1
    meaning (an optional ``endpoint``, validated as public HTTPS when present).
    Once either is declared, both are required and must agree: ``local`` is
    MCP ``stdio`` with no endpoint or service identity; ``in-cluster`` is a
    network transport with a ``service_identity`` and no public endpoint;
    ``public`` is a network transport with a verifiable public HTTPS
    ``endpoint``. The pipelines Pages TCK applies the identical rules and
    error codes (``scripts/pages_readiness.py``).
    """

    if not TRANSPORT_KEYS & set(entry):
        return
    transport = entry.get("transport")
    reachability = entry.get("reachability")
    if transport is None or reachability is None:
        _fail("capability-transport-incomplete")
    if transport not in SURFACE_TRANSPORTS[name]:
        _fail("capability-transport-unsupported")
    if reachability not in REACHABILITY_VALUES:
        _fail("capability-reachability-invalid")
    endpoint = entry.get("endpoint")
    identity = entry.get("service_identity")
    if (transport == "stdio") != (reachability == "local"):
        _fail("capability-reachability-inconsistent")
    if reachability == "public":
        if identity is not None:
            _fail("capability-reachability-inconsistent")
        if not isinstance(endpoint, str):
            _fail("capability-endpoint-required")
        return
    if endpoint is not None:
        _fail("capability-reachability-inconsistent")
    if reachability == "local":
        if identity is not None:
            _fail("capability-reachability-inconsistent")
        return
    if identity is None:
        _fail("capability-service-identity-required")
    if (
        not isinstance(identity, str)
        or len(identity) > 253
        or not SERVICE_IDENTITY_PATTERN.fullmatch(identity)
    ):
        _fail("capability-service-identity-invalid")


def _validate_input(root: Path, value: dict[str, Any]) -> dict[str, Any]:
    if value.get("schema_version") != SCHEMA_VERSION:
        _fail("applicability-schema-version")
    project = value.get("project")
    if (
        not isinstance(project, dict)
        or set(project) != {"name", "kind"}
        or not isinstance(project.get("name"), str)
        or not 1 <= len(project["name"]) <= 200
        or any(ord(char) < 32 for char in project["name"])
    ):
        _fail("applicability-project-invalid")
    kind = project.get("kind")
    if kind not in {"library", "package", "service", "docs-only"}:
        _fail("applicability-project-kind-invalid")
    applicability = value.get("applicability")
    if not isinstance(applicability, dict) or set(applicability) != set(
        APPLICABILITY_CATEGORIES
    ):
        _fail("applicability-categories-invalid")
    if any(
        not isinstance(applicability[key], bool) for key in APPLICABILITY_CATEGORIES
    ):
        _fail("applicability-category-value-invalid")
    standards = _validate_standards(value.get("standards"))
    signals = value.get("content_signals")
    if (
        not isinstance(signals, dict)
        or set(signals) - {"policy", "values"}
        or signals.get("policy") not in SAFE_SIGNAL_POLICIES
    ):
        _fail("content-signals-policy-required")
    if signals["policy"] == "operator-reviewed":
        if not isinstance(signals.get("values"), dict):
            _fail("content-signals-values-required")
        _scan_json_strings(signals["values"], "content-signals")
    elif "values" in signals:
        _fail("content-signals-values-unset")
    normalized_signals = {"policy": signals["policy"]}
    if signals["policy"] == "operator-reviewed":
        normalized_signals["values"] = signals["values"]
    budgets = value.get("budgets")
    if not isinstance(budgets, dict) or set(budgets) - {
        "curated_chars",
        "summary_chars",
        "full_chars",
    }:
        _fail("budgets-required")
    curated = budgets.get("curated_chars")
    summary = budgets.get("summary_chars")
    full = budgets.get("full_chars", 0)
    if (
        type(curated) is not int
        or not 1 <= curated <= MAX_CURATED_CHARS
        or type(summary) is not int
        or not 1 <= summary <= MAX_SUMMARY_CHARS
        or type(full) is not int
        or not 0 <= full <= MAX_FULL_CHARS
    ):
        _fail("budgets-invalid")
    capabilities = value.get("capabilities")
    if not isinstance(capabilities, dict) or set(capabilities) != CAPABILITY_NAMES:
        _fail("capabilities-invalid")
    normalized_capabilities: dict[str, dict[str, Any]] = {}
    capability_evidence: dict[str, dict[str, str]] = {}
    for name, entry in capabilities.items():
        if not isinstance(entry, dict) or not isinstance(entry.get("applicable"), bool):
            _fail("capability-entry-invalid")
        if name == "skills":
            allowed_keys = {"applicable", "path"}
        elif name in SURFACE_TRANSPORTS:
            allowed_keys = {
                "applicable",
                "artifact",
                "endpoint",
                *_OAUTH_METADATA_FIELDS,
                *TRANSPORT_KEYS,
            }
        else:
            allowed_keys = {
                "applicable",
                "artifact",
                "endpoint",
                *_OAUTH_METADATA_FIELDS,
            }
        if set(entry) - allowed_keys:
            _fail("capability-entry-invalid")
        applicable = entry["applicable"]
        if applicable and name in {"api", "mcp", "a2a"}:
            if kind == "library":
                _fail("library-capability-unsupported")
            if kind == "docs-only":
                _fail("docs-only-served-capability-unsupported")
        artifact = entry.get("artifact")
        endpoint = entry.get("endpoint")
        if applicable and name in {"api", "mcp", "a2a"}:
            if not isinstance(artifact, str):
                _fail("capability-authority-required")
            if endpoint is not None:
                _public_url(endpoint, f"{name}-endpoint")
            if name in SURFACE_TRANSPORTS:
                _validate_surface_reachability(name, entry)
            capability_evidence[name] = _validate_capability_artifact(
                root, name, artifact
            )
            if (
                name == "mcp"
                and entry.get("transport") in {"streamable-http", "sse"}
                and capability_evidence[name].get("http_transport") != "true"
            ):
                _fail("mcp-transport-not-proven")
            for field in _OAUTH_METADATA_FIELDS:
                metadata_path = entry.get(field)
                if metadata_path is not None:
                    capability_evidence[name][field] = _validate_oauth_metadata(
                        root, field, metadata_path
                    )
        if applicable and name == "skills":
            normalized_path = _validate_skills_path(root, entry.get("path"))
        else:
            normalized_path = None
        if not applicable and set(entry) != {"applicable"}:
            _fail("capability-entry-inapplicable-data")
        if name == "skills" and applicable and set(entry) != {"applicable", "path"}:
            _fail("skills-path-required")
        # Runtime ``endpoint``, ``service_identity`` and OAuth metadata paths are
        # validated above but deliberately not recorded in the manifest; the
        # declared transport/reachability are, so consumers (the pipelines
        # Pages TCK) can see how the surface is reached without its address.
        normalized_capabilities[name] = {
            "applicable": applicable,
            **({"artifact": artifact} if isinstance(artifact, str) else {}),
            **({"path": normalized_path} if normalized_path is not None else {}),
            **{
                field: entry[field]
                for field in ("transport", "reachability")
                if applicable and isinstance(entry.get(field), str)
            },
        }
    return {
        "schema_version": SCHEMA_VERSION,
        "project": {"name": project["name"], "kind": kind},
        "applicability": {key: applicability[key] for key in APPLICABILITY_CATEGORIES},
        "standards": standards,
        "content_signals": normalized_signals,
        "budgets": {
            "curated_chars": curated,
            "summary_chars": summary,
            "full_chars": full,
        },
        "capabilities": normalized_capabilities,
        "capability_evidence": capability_evidence,
    }


def _page_records(
    root: Path, config: dict[str, Any], summary_limit: int
) -> tuple[tuple[Page, ...], tuple[Section, ...]]:
    site_url = _public_url(config.get("site_url"), "mkdocs-site", directory=True)
    use_directory_urls = config.get("use_directory_urls", True)
    if not isinstance(use_directory_urls, bool):
        _fail("mkdocs-use-directory-urls-invalid")
    docs_dir_raw = config.get("docs_dir", "docs")
    docs_root = _safe_relative(root, docs_dir_raw, "docs-dir")
    leaves = _flatten_nav(config["nav"])
    pages: list[Page] = []
    seen_sources: set[str] = set()
    seen_urls: set[str] = set()
    seen_markdown_urls: set[str] = set()
    section_pages: dict[str, list[Page]] = {}
    for title, raw_source, section_title in leaves:
        source_path = _safe_relative(docs_root, raw_source, "nav-source")
        relative_source = source_path.relative_to(root).as_posix()
        if relative_source in seen_sources or not relative_source.endswith(".md"):
            _fail("mkdocs-nav-source-duplicate-or-invalid")
        payload = _regular_file(source_path, "nav-source")
        text = payload.decode("utf-8")
        _scan_safe_text(text, "markdown")
        url = _static_page_url(
            site_url, raw_source, use_directory_urls=use_directory_urls
        )
        if url in seen_urls:
            _fail("mkdocs-nav-url-duplicate")
        markdown_url = _static_markdown_url(site_url, raw_source)
        if markdown_url in seen_markdown_urls:
            _fail("mkdocs-nav-markdown-url-duplicate")
        section = section_title or "Documentation"
        page = Page(
            title=title,
            source=relative_source,
            url=url,
            markdown_url=markdown_url,
            summary=_summary(text, summary_limit),
            digest=hashlib.sha256(payload).hexdigest(),
            size=len(payload),
            section=section,
        )
        pages.append(page)
        section_pages.setdefault(section, []).append(page)
        seen_sources.add(relative_source)
        seen_urls.add(url)
        seen_markdown_urls.add(markdown_url)
    sections: list[Section] = []
    seen_slugs: set[str] = set()
    for title, section_items in section_pages.items():
        slug = _slug(title)
        if slug in seen_slugs:
            _fail("mkdocs-nav-section-duplicate")
        seen_slugs.add(slug)
        sections.append(Section(title=title, slug=slug, pages=tuple(section_items)))
    return tuple(pages), tuple(sections)


def _render_curated(
    config: dict[str, Any],
    readiness: dict[str, Any],
    sections: tuple[Section, ...],
    *,
    standards_reference: str | None = None,
) -> str:
    lines = [
        f"# {config.get('site_name', readiness['project']['name'])}",
        "",
        "> Current documentation index generated from the exact MkDocs navigation.",
        "> Capability and content-use claims are operator-scoped and provenance-bound.",
        "",
    ]
    for section in sections:
        lines.extend([f"## {section.title}", ""])
        for page in section.pages:
            suffix = f" — {page.summary}" if page.summary else ""
            lines.append(f"- [{page.title}]({page.url}){suffix}")
        lines.append("")
    if standards_reference is None:
        lines.extend(["## Standards maturity", ""])
        for standard in readiness["standards"]:
            lines.append(
                f"- {standard['id']}: {standard['kind']} ({standard['level']})"
            )
    else:
        lines.append(
            "Standards maturity and scope: "
            f"[root documentation index]({standards_reference})."
        )
    lines.append("")
    output = "\n".join(lines).rstrip() + "\n"
    _scan_safe_text(output, "llms")
    if len(output) > readiness["budgets"]["curated_chars"]:
        _fail("curated-context-oversize")
    return output


def _render_full(config: dict[str, Any], pages: tuple[Page, ...], budget: int) -> str:
    lines = [
        f"# {config.get('site_name', 'Documentation')} — full current Markdown context",
        "",
        "> Generated only when an explicit full-context budget is supplied.",
        "",
    ]
    root = Path(config["_root"])
    for page in pages:
        payload = _regular_file(root / page.source, "nav-source").decode("utf-8")
        lines.extend(
            [f"## {page.title}", f"Source: `{page.source}`", "", payload.rstrip(), ""]
        )
    output = "\n".join(lines).rstrip() + "\n"
    _scan_safe_text(output, "llms-full")
    if len(output) > budget:
        _fail("full-context-oversize")
    return output


def _check_output_components(path: Path) -> None:
    """Reject symlink/non-directory ancestors without changing the tree."""

    absolute = path.absolute()
    cursor = Path(absolute.anchor)
    for part in absolute.parts[1:]:
        cursor /= part
        try:
            metadata = cursor.lstat()
        except FileNotFoundError:
            return
        except OSError as exc:
            raise ReadinessError("output-unavailable") from exc
        if cursor.is_symlink():
            _fail("output-symlink")
        if cursor != absolute and not cursor.is_dir():
            _fail("output-parent-invalid")
        if cursor == absolute and not cursor.is_dir() and path.is_dir():
            _fail("output-parent-invalid")
        if metadata.st_nlink < 1:
            _fail("output-unavailable")


def _validate_output_target(target: Path) -> None:
    _check_output_components(target)
    if target.exists() and not target.is_dir():
        _fail("output-parent-invalid")


def _ensure_output_parent(path: Path) -> None:
    """Create only missing, non-symlink output directories at publish time."""

    absolute = path.absolute()
    missing: list[Path] = []
    cursor = absolute
    while True:
        try:
            metadata = cursor.lstat()
        except FileNotFoundError:
            missing.append(cursor)
            cursor = cursor.parent
            continue
        except OSError as exc:
            raise ReadinessError("output-parent-unavailable") from exc
        if cursor.is_symlink() or not cursor.is_dir() or metadata.st_nlink < 1:
            _fail("output-parent-invalid")
        break
    for directory in reversed(missing):
        try:
            directory.mkdir()
            if directory.is_symlink() or not directory.is_dir():
                _fail("output-parent-invalid")
        except OSError as exc:
            raise ReadinessError("output-parent-unavailable") from exc


def _validate_output_file(
    path: Path,
    relative: str,
    previous: set[str],
    previous_manifest: bool,
    adopt: bool,
) -> None:
    _check_output_components(path)
    if path.is_symlink():
        _fail("output-symlink")
    if not path.exists():
        return
    try:
        metadata = path.lstat()
    except OSError as exc:
        raise ReadinessError("output-unavailable") from exc
    if not path.is_file() or metadata.st_nlink != 1:
        _fail("output-not-regular")
    owned = relative in previous or (
        relative == "agent-readiness-manifest.json" and previous_manifest
    )
    if not owned and not adopt:
        _fail("output-unowned")


def _ensure_plan_output(
    target: Path,
    relative: str,
    payload: str | bytes,
    previous: set[str],
    previous_manifest: bool,
    adopt: bool,
    plan: dict[str, bytes],
) -> None:
    path = target / relative
    _validate_output_file(path, relative, previous, previous_manifest, adopt)
    plan[relative] = payload.encode("utf-8") if isinstance(payload, str) else payload


def _plan_delete(
    target: Path,
    relative: str,
    previous: set[str],
    previous_manifest: bool,
    adopt: bool,
    deletions: set[str],
) -> None:
    path = target / relative
    _validate_output_file(path, relative, previous, previous_manifest, adopt)
    if path.exists():
        deletions.add(relative)


def _atomic_write(path: Path, payload: bytes) -> None:
    _ensure_output_parent(path.parent)
    temporary: str | None = None
    try:
        descriptor, temporary = tempfile.mkstemp(
            prefix=f".{path.name}.", suffix=".tmp", dir=path.parent
        )
        with os.fdopen(descriptor, "wb") as handle:
            handle.write(payload)
            handle.flush()
            os.fsync(handle.fileno())
        # By path, not os.fchmod: fchmod is POSIX-only before Python 3.13.
        os.chmod(temporary, 0o644)
        os.replace(temporary, path)
        temporary = None
    except OSError as exc:
        raise ReadinessError("output-publish-failed") from exc
    finally:
        if temporary is not None:
            try:
                os.unlink(temporary)
            except OSError:
                pass


def _publish(target: Path, plan: dict[str, bytes], deletions: set[str]) -> None:
    """Publish one artifact set with the provenance manifest as commit record.

    Individual replacements are atomic, but a set spans several paths. Snapshot
    the owned prior state and roll it back on a mid-publication failure so a new
    manifest can never attest to a partial set. The manifest is always replaced
    last, after stale owned artifacts have been pruned successfully.
    """

    _ensure_output_parent(target)
    manifest = "agent-readiness-manifest.json"
    ordered = [relative for relative in sorted(plan) if relative != manifest]
    if manifest in plan:
        ordered.append(manifest)
    affected = set(plan) | deletions
    prior: dict[str, bytes | None] = {}
    for relative in affected:
        path = target / relative
        prior[relative] = _regular_file(path, "output-prior") if path.exists() else None
    try:
        for relative in ordered[:-1] if ordered[-1:] == [manifest] else ordered:
            _atomic_write(target / relative, plan[relative])
        for relative in sorted(deletions):
            try:
                (target / relative).unlink()
            except OSError as exc:
                raise ReadinessError("output-prune-failed") from exc
        if ordered[-1:] == [manifest]:
            _atomic_write(target / manifest, plan[manifest])
    except (OSError, ReadinessError) as exc:
        try:
            for relative in sorted(affected):
                path = target / relative
                payload = prior[relative]
                if payload is None:
                    if path.exists():
                        path.unlink()
                else:
                    _atomic_write(path, payload)
        except (OSError, ReadinessError) as rollback_exc:
            raise ReadinessError("output-rollback-failed") from rollback_exc
        if isinstance(exc, ReadinessError):
            raise
        raise ReadinessError("output-publish-failed") from exc


def _previous_generated(target: Path) -> tuple[set[str], bool]:
    manifest_path = target / "agent-readiness-manifest.json"
    _check_output_components(manifest_path)
    if not manifest_path.exists():
        return set(), False
    payload = _regular_file(manifest_path, "previous-manifest")
    try:
        manifest = json.loads(payload.decode("utf-8"))
    except (UnicodeDecodeError, json.JSONDecodeError) as exc:
        raise ReadinessError("previous-manifest-invalid") from exc
    generated = manifest.get("generated") if isinstance(manifest, dict) else None
    if (
        not isinstance(manifest, dict)
        or manifest.get("schema_version") != SCHEMA_VERSION
        or not isinstance(generated, list)
        or any(
            not isinstance(path, str)
            or not path
            or "\\" in path
            or PurePosixPath(path).is_absolute()
            or any(part in {"", ".", ".."} for part in PurePosixPath(path).parts)
            for path in generated
        )
    ):
        _fail("previous-manifest-invalid")
    return set(generated), True


def generate(
    root: Path,
    *,
    applicability: Path | None = None,
    output_dir: Path | None = None,
    include_full: bool = False,
    full_budget: int | None = None,
    check: bool = False,
    adopt_existing: bool = False,
) -> dict[str, Any]:
    """Validate, plan, and optionally publish readiness artifacts.

    All source, capability, URL, budget, and output-ownership checks happen
    before publication.  ``check`` returns the same manifest without changing
    the output tree; ``adopt_existing`` is the explicit escape hatch for a
    first run over already-present, unowned artifact paths.
    """

    root = root.resolve(strict=True)
    applicability_path = applicability or root / "docs" / "agent-readiness.json"
    applicability_path = _safe_existing_path(root, applicability_path, "applicability")
    applicability_bytes = _regular_file(applicability_path, "applicability")
    try:
        applicability_value = json.loads(applicability_bytes.decode("utf-8"))
    except (UnicodeDecodeError, json.JSONDecodeError) as exc:
        raise ReadinessError("applicability-invalid-json") from exc
    if not isinstance(applicability_value, dict):
        _fail("applicability-root-invalid")
    readiness = _validate_input(root, applicability_value)
    config, mkdocs_bytes = _load_mkdocs(root)
    pages, sections = _page_records(root, config, readiness["budgets"]["summary_chars"])
    config = {**config, "_root": str(root)}
    curated = _render_curated(config, readiness, sections)
    section_payloads: dict[str, str] = {}
    for section in sections:
        section_text = _render_curated(
            {
                **config,
                "site_name": f"{config.get('site_name', 'Documentation')} — {section.title}",
            },
            readiness,
            (section,),
            standards_reference="../../llms.txt",
        )
        section_payloads[f"llms-sections/{section.slug}/llms.txt"] = section_text

    effective_full_budget = (
        full_budget if full_budget is not None else readiness["budgets"]["full_chars"]
    )
    full_payload: str | None = None
    if include_full:
        if (
            type(effective_full_budget) is not int
            or not 0 < effective_full_budget <= MAX_FULL_CHARS
        ):
            _fail("full-context-budget-required")
        full_payload = _render_full(config, pages, effective_full_budget)

    discovery_payloads: dict[str, str] = {}
    if readiness["applicability"]["discoverability"]:
        skills = readiness["capabilities"].get("skills", {})
        if skills.get("applicable") is True:
            discovery_payloads[".well-known/agent-skills.json"] = (
                _render_agent_skills_index(root, skills["path"])
            )
        mcp_card = _render_mcp_server_card(
            readiness, project_name=readiness["project"]["name"]
        )
        if mcp_card is not None:
            discovery_payloads[".well-known/mcp-server-card.json"] = mcp_card
        api_catalog = _render_api_catalog(readiness)
        if api_catalog is not None:
            discovery_payloads[".well-known/api-catalog"] = api_catalog

    mirror_applicable = readiness["applicability"]["discoverability"]
    mirror_entries = [
        {
            "source": page.source,
            "url": page.url if mirror_applicable else None,
            "canonical_url": page.url if mirror_applicable else None,
            "markdown_url": page.markdown_url if mirror_applicable else None,
            "sha256": page.digest,
            "bytes": page.size,
        }
        for page in pages
    ]
    mirror = {
        "schema_version": SCHEMA_VERSION,
        "url_contract": "mkdocs-static/v2",
        "applicable": mirror_applicable,
        "entries": mirror_entries,
    }
    mirror_payload = json.dumps(mirror, indent=2, sort_keys=True) + "\n"
    provenance = {
        "schema_version": SCHEMA_VERSION,
        "generator_version": GENERATOR_VERSION,
        "project": readiness["project"],
        "applicability": readiness["applicability"],
        "standards": readiness["standards"],
        "content_signals": readiness["content_signals"],
        "capabilities": readiness["capabilities"],
        "capability_evidence": readiness["capability_evidence"],
        "budgets": {
            **readiness["budgets"],
            "full_requested": include_full,
            "full_effective_chars": effective_full_budget if include_full else 0,
        },
        "provenance": {
            "url_contract": "mkdocs-static/v2",
            "mkdocs_sha256": hashlib.sha256(mkdocs_bytes).hexdigest(),
            "applicability_sha256": hashlib.sha256(applicability_bytes).hexdigest(),
            "pages": [
                {"source": page.source, "sha256": page.digest, "bytes": page.size}
                for page in pages
            ],
        },
        "generated": [
            "llms.txt",
            *[f"llms-sections/{section.slug}/llms.txt" for section in sections],
            "markdown-mirror-manifest.json",
            *sorted(discovery_payloads),
            *(["llms-full.txt"] if include_full else []),
        ],
    }
    manifest_payload = json.dumps(provenance, indent=2, sort_keys=True) + "\n"
    target = (output_dir or root).absolute()
    _validate_output_target(target)
    previous_generated, previous_manifest = _previous_generated(target)
    plan: dict[str, bytes] = {}
    deletions: set[str] = set()
    _ensure_plan_output(
        target,
        "llms.txt",
        curated,
        previous_generated,
        previous_manifest,
        adopt_existing,
        plan,
    )
    for relative, payload in section_payloads.items():
        _ensure_plan_output(
            target,
            relative,
            payload,
            previous_generated,
            previous_manifest,
            adopt_existing,
            plan,
        )
    if full_payload is not None:
        _ensure_plan_output(
            target,
            "llms-full.txt",
            full_payload,
            previous_generated,
            previous_manifest,
            adopt_existing,
            plan,
        )
    elif "llms-full.txt" in previous_generated:
        _plan_delete(
            target,
            "llms-full.txt",
            previous_generated,
            previous_manifest,
            adopt_existing,
            deletions,
        )
    else:
        _check_output_components(target / "llms-full.txt")
    if full_payload is None and "llms-full.txt" not in previous_generated:
        if (target / "llms-full.txt").exists():
            _validate_output_file(
                target / "llms-full.txt",
                "llms-full.txt",
                previous_generated,
                previous_manifest,
                adopt_existing,
            )
    discovery_paths = {
        ".well-known/agent-skills.json",
        ".well-known/api-catalog",
        ".well-known/mcp-server-card.json",
    }
    for relative in sorted(discovery_paths):
        payload = discovery_payloads.get(relative)
        if payload is not None:
            _ensure_plan_output(
                target,
                relative,
                payload,
                previous_generated,
                previous_manifest,
                adopt_existing,
                plan,
            )
        elif relative in previous_generated:
            _plan_delete(
                target,
                relative,
                previous_generated,
                previous_manifest,
                adopt_existing,
                deletions,
            )
        else:
            _check_output_components(target / relative)
    current_section_paths = set(section_payloads)
    for relative in sorted(previous_generated):
        if (
            relative.startswith("llms-sections/")
            and relative.endswith("/llms.txt")
            and relative not in current_section_paths
        ):
            _plan_delete(
                target,
                relative,
                previous_generated,
                previous_manifest,
                adopt_existing,
                deletions,
            )
    _ensure_plan_output(
        target,
        "markdown-mirror-manifest.json",
        mirror_payload,
        previous_generated,
        previous_manifest,
        adopt_existing,
        plan,
    )
    _ensure_plan_output(
        target,
        "agent-readiness-manifest.json",
        manifest_payload,
        previous_generated,
        previous_manifest,
        adopt_existing,
        plan,
    )
    if not check:
        _publish(target, plan, deletions)
        return provenance
    return {
        **provenance,
        "planned": sorted(plan),
        "pruned": sorted(deletions),
    }


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--root", type=Path, default=Path("."))
    parser.add_argument("--applicability", type=Path)
    parser.add_argument("--output-dir", type=Path)
    parser.add_argument("--full", action="store_true", help="emit full context")
    parser.add_argument("--full-budget", type=int)
    parser.add_argument(
        "--check", action="store_true", help="validate and preview without writing"
    )
    parser.add_argument(
        "--adopt-existing",
        action="store_true",
        help="explicitly adopt pre-existing unowned output artifacts",
    )
    args = parser.parse_args(argv)
    try:
        manifest = generate(
            args.root,
            applicability=args.applicability,
            output_dir=args.output_dir,
            include_full=args.full,
            full_budget=args.full_budget,
            check=args.check,
            adopt_existing=args.adopt_existing,
        )
    except (OSError, ReadinessError, UnicodeError, ValueError) as exc:
        print(f"agent-readiness generation failed: {exc}", file=sys.stderr)
        return 2
    result = {"check": args.check, "generated": manifest["generated"]}
    if args.check:
        result.update(
            planned=manifest.get("planned", []), pruned=manifest.get("pruned", [])
        )
    print(json.dumps(result, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
