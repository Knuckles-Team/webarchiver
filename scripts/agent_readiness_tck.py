#!/usr/bin/env python3
"""Bounded, deterministic checks for a served Agent Readiness contract.

The offline readiness generator is deliberately authoritative for package source
artifacts.  This module is the small, separate TCK adapter for a *served* copy of
those artifacts.  It never sends credentials, follows redirects, or records
response bodies.  Network mode requires an exact HTTPS origin allowlist; loopback,
private, and link-local destinations are available only with the explicit
``local_fixture`` mode used by deterministic tests.

The adapter is stdlib-only so generated packages can run the TCK without making a
runtime provider dependency part of their documentation contract.  It is a
measurement tool, not a capability generator: an unavailable or inapplicable
surface is reported explicitly instead of being treated as a pass.
"""

from __future__ import annotations

import argparse
import hashlib
import ipaddress
import json
import math
import re
import socket
import ssl
import urllib.error
import urllib.request
from collections.abc import Mapping
from dataclasses import dataclass, field
from pathlib import PurePosixPath
from typing import Any, Protocol
from urllib.parse import urlsplit

TCK_SCHEMA_VERSION = "agent-readiness-tck/v1"
TCK_CONTRACT_VERSION = "agent-readiness-tck/v1"
TCK_MATURITY = "experimental"
TCK_STANDARDS = (
    "RFC 3986",
    "RFC 8414",
    "RFC 9264",
    "RFC 9457",
    "RFC 9727",
    "RFC 9728",
)

PASS = "PASS"
FAIL = "FAIL"
UNAVAILABLE = "UNAVAILABLE"
NOT_APPLICABLE = "NOT_APPLICABLE"
CHECK_STATUSES = frozenset({PASS, FAIL, UNAVAILABLE, NOT_APPLICABLE})

MAX_ORIGIN_CHARS = 512
MAX_PATH_CHARS = 1_024
MAX_HEADER_CHARS = 8_192
MAX_HEADERS = 128
MAX_RESPONSE_BYTES = 1_024 * 1_024
MAX_TIMEOUT_SECONDS = 10.0
MAX_LINKS = 128
MAX_JSON_DEPTH = 12
MAX_JSON_KEYS = 512
MAX_STRING_CHARS = 16_384
MAX_PROBLEM_DETAIL_CHARS = 2_048
MAX_PROBLEM_INSTANCE_CHARS = 512
MAX_PROBLEM_TYPE_CHARS = 256
MAX_RETRY_AFTER_SECONDS = 3_600.0

PROBLEM_JSON = "application/problem+json"
MARKDOWN = "text/markdown"
HTML = "text/html"
LINKSET_JSON = "application/linkset+json"
API_CATALOG_PROFILE = "https://www.rfc-editor.org/info/rfc9727"

_DEFAULT_DISCOVERY_PATHS = {
    "a2a_card": "/a2a.json",
    "api_catalog": "/.well-known/api-catalog",
    "mcp_server_card": "/.well-known/mcp-server-card.json",
    "agent_skills": "/.well-known/agent-skills.json",
    "oauth_protected_resource": "/.well-known/oauth-protected-resource",
    "oauth_authorization_server": "/.well-known/oauth-authorization-server",
}
_DISCOVERY_MEDIA_TYPES = {
    "a2a_card": "application/json",
    "api_catalog": LINKSET_JSON,
    "mcp_server_card": "application/json",
    "agent_skills": "application/json",
    "oauth_protected_resource": "application/json",
    "oauth_authorization_server": "application/json",
}
_PROBLEM_FIELDS = (
    "status",
    "code",
    "type",
    "instance",
    "retryable",
    "retry_after_s",
)
_DENIAL_CODES = frozenset(
    {
        "access_denied",
        "authentication_required",
        "forbidden",
        "not_authorized",
        "permission_denied",
        "policy_denied",
        "unauthorized",
    }
)
_SECRET_PATTERN = re.compile(
    r"(?ix)(?:api[_-]?key|access[_-]?token|refresh[_-]?token|password|"
    r"secret(?:[_-][a-z0-9]+)*|token(?:[_-][a-z0-9]+)*)"
    r"[\"'`]?\s*[:=]\s*(?!<|\$|env://|\*|redacted\b|none\b|false\b|true\b)"
    r"[\"']?[A-Za-z0-9_./+=:-]{12,}[\"']?"
)
_BEARER_PATTERN = re.compile(r"(?i)\bbearer\s+[A-Za-z0-9._~+/=-]{12,}")
_URL_PATTERN = re.compile(r"https?://[^\s<>'\"]+")
_LINK_PATTERN = re.compile(r"<([^<>]+)>\s*;\s*([^,]+)(?:,|$)", re.IGNORECASE)


class TckConfigurationError(ValueError):
    """The operator supplied an unsafe or incomplete TCK boundary."""


class TckUnavailable(RuntimeError):
    """A target could not be reached without making a readiness claim."""


class TckViolation(RuntimeError):
    """A response or transport violated a bounded TCK contract."""


@dataclass(frozen=True)
class TckResponse:
    """A response returned by either the real or fixture transport."""

    status: int
    headers: Mapping[str, str] = field(default_factory=dict)
    body: bytes = b""

    def __post_init__(self) -> None:
        try:
            status = int(self.status)
        except (TypeError, ValueError) as exc:
            raise TckViolation("response-status-invalid") from exc
        if not 100 <= status <= 599:
            raise TckViolation("response-status-invalid")
        if not isinstance(self.body, bytes):
            raise TckViolation("response-body-invalid")
        if len(self.headers) > MAX_HEADERS:
            raise TckViolation("response-header-budget-exceeded")
        normalized: dict[str, str] = {}
        for key, value in self.headers.items():
            if not isinstance(key, str) or not isinstance(value, str):
                raise TckViolation("response-header-invalid")
            if len(key) > 128 or len(value) > MAX_HEADER_CHARS:
                raise TckViolation("response-header-oversize")
            normalized[key.lower()] = value
        object.__setattr__(self, "status", status)
        object.__setattr__(self, "headers", normalized)


class TckTransport(Protocol):
    """Transport seam; implementations receive paths, never arbitrary URLs."""

    def fetch(
        self, path: str, accept: str, *, timeout: float, max_bytes: int
    ) -> TckResponse: ...


def _local_host(host: str) -> bool:
    normalized = host.rstrip(".").lower()
    if normalized in {"localhost", "local", "internal"} or normalized.endswith(
        (".local", ".localhost", ".internal", ".home", ".arpa")
    ):
        return True
    try:
        return not ipaddress.ip_address(normalized).is_global
    except ValueError:
        return False


def _normalized_origin(raw: object, *, local_fixture: bool) -> str:
    if not isinstance(raw, str) or not raw or len(raw) > MAX_ORIGIN_CHARS:
        raise TckConfigurationError("origin-boundary-invalid")
    try:
        parsed = urlsplit(raw)
        port = parsed.port
    except ValueError as exc:
        raise TckConfigurationError("origin-boundary-invalid") from exc
    host = (parsed.hostname or "").rstrip(".").lower()
    if (
        parsed.scheme.lower() not in {"http", "https"}
        or not host
        or parsed.username is not None
        or parsed.password is not None
        or parsed.query
        or parsed.fragment
        or parsed.path not in {"", "/"}
    ):
        raise TckConfigurationError("origin-boundary-invalid")
    scheme = parsed.scheme.lower()
    if scheme != "https" and not (local_fixture and _local_host(host)):
        raise TckConfigurationError("origin-must-use-https")
    if _local_host(host) and not local_fixture:
        raise TckConfigurationError("private-origin-requires-local-fixture")
    if port is not None and not 1 <= port <= 65_535:
        raise TckConfigurationError("origin-boundary-invalid")
    if (scheme, port) in {("https", 443), ("http", 80)}:
        port = None
    if ":" in host and not host.startswith("["):
        host = f"[{host}]"
    return f"{scheme}://{host}{f':{port}' if port else ''}"


def _safe_path(raw: object) -> str:
    if not isinstance(raw, str) or not raw or len(raw) > MAX_PATH_CHARS:
        raise TckConfigurationError("path-boundary-invalid")
    if "\x00" in raw or "\\" in raw:
        raise TckConfigurationError("path-boundary-invalid")
    if _SECRET_PATTERN.search(raw) or _BEARER_PATTERN.search(raw):
        raise TckConfigurationError("path-secret-like-value")
    parsed = urlsplit(raw)
    if parsed.scheme or parsed.netloc or parsed.query or parsed.fragment:
        raise TckConfigurationError("path-boundary-invalid")
    path = raw if raw.startswith("/") else f"/{raw}"
    parts = PurePosixPath(path).parts
    if any(part in {"", ".", ".."} for part in parts[1:]):
        raise TckConfigurationError("path-boundary-invalid")
    return path


def _safe_reference(raw: object, *, local_fixture: bool) -> str:
    """Validate a returned link without retaining its potentially sensitive value."""

    if not isinstance(raw, str) or not raw or len(raw) > MAX_PATH_CHARS:
        raise TckViolation("link-boundary-invalid")
    if _SECRET_PATTERN.search(raw) or _BEARER_PATTERN.search(raw):
        raise TckViolation("secret-like-link")
    try:
        parsed = urlsplit(raw)
    except ValueError as exc:
        raise TckViolation("link-boundary-invalid") from exc
    if parsed.username or parsed.password or parsed.query or parsed.fragment:
        raise TckViolation("link-boundary-invalid")
    if parsed.scheme or parsed.netloc:
        if not parsed.hostname:
            raise TckViolation("link-boundary-invalid")
        if parsed.scheme.lower() != "https" and not (
            local_fixture
            and parsed.scheme.lower() == "http"
            and _local_host(parsed.hostname)
        ):
            raise TckViolation("link-boundary-invalid")
        if _local_host(parsed.hostname) and not local_fixture:
            raise TckViolation("private-link")
        if parsed.port not in {None, 443}:
            raise TckViolation("link-boundary-invalid")
        return parsed.path or "/"
    if raw.startswith("//") or "\\" in raw:
        raise TckViolation("link-boundary-invalid")
    if any(part in {"", ".", ".."} for part in PurePosixPath(raw).parts):
        raise TckViolation("link-boundary-invalid")
    return raw


def _scan_safe_text(text: str, *, local_fixture: bool) -> None:
    if len(text) > MAX_STRING_CHARS:
        raise TckViolation("text-budget-exceeded")
    if _SECRET_PATTERN.search(text) or _BEARER_PATTERN.search(text):
        raise TckViolation("secret-like-response")
    for match in _URL_PATTERN.finditer(text):
        _safe_reference(match.group(0).rstrip(".,;:)"), local_fixture=local_fixture)


def _scan_json(value: object, *, local_fixture: bool, depth: int = 0) -> None:
    if depth > MAX_JSON_DEPTH:
        raise TckViolation("json-depth-exceeded")
    if isinstance(value, str):
        _scan_safe_text(value, local_fixture=local_fixture)
    elif isinstance(value, Mapping):
        if len(value) > MAX_JSON_KEYS:
            raise TckViolation("json-key-budget-exceeded")
        for key, child in value.items():
            if not isinstance(key, str) or len(key) > 256:
                raise TckViolation("json-key-invalid")
            _scan_safe_text(key, local_fixture=local_fixture)
            _scan_json(child, local_fixture=local_fixture, depth=depth + 1)
    elif isinstance(value, list):
        if len(value) > MAX_JSON_KEYS:
            raise TckViolation("json-list-budget-exceeded")
        for child in value:
            _scan_json(child, local_fixture=local_fixture, depth=depth + 1)
    elif value is not None and not isinstance(value, (bool, int, float)):
        raise TckViolation("json-value-invalid")


def _header(response: TckResponse, name: str) -> str:
    value = response.headers.get(name.lower(), "")
    if len(value) > MAX_HEADER_CHARS:
        raise TckViolation("response-header-oversize")
    return value.strip()


def _media_type(response: TckResponse) -> str:
    return _header(response, "content-type").split(";", 1)[0].strip().lower()


def _body_text(response: TckResponse, *, max_bytes: int, local_fixture: bool) -> str:
    if len(response.body) > max_bytes:
        raise TckViolation("response-size-budget-exceeded")
    try:
        text = response.body.decode("utf-8")
    except UnicodeDecodeError as exc:
        raise TckViolation("response-not-utf8") from exc
    _scan_safe_text(text, local_fixture=local_fixture)
    return text


def _body_evidence(response: TckResponse, *, max_bytes: int) -> dict[str, Any]:
    if len(response.body) > max_bytes:
        raise TckViolation("response-size-budget-exceeded")
    return {
        "http_status": response.status,
        "bytes": len(response.body),
        "sha256": hashlib.sha256(response.body).hexdigest(),
        "content_type": _media_type(response),
    }


def _check(
    identifier: str, status: str, *, reason: str = "", **evidence: Any
) -> dict[str, Any]:
    if status not in CHECK_STATUSES:
        raise ValueError("invalid TCK check status")
    result: dict[str, Any] = {"id": identifier, "status": status}
    if reason:
        result["reason"] = reason
    result["evidence"] = evidence
    return result


def _parse_json(text: str, *, local_fixture: bool) -> object:
    try:
        value = json.loads(text)
    except (UnicodeDecodeError, json.JSONDecodeError) as exc:
        raise TckViolation("malformed-json") from exc
    _scan_json(value, local_fixture=local_fixture)
    return value


def _parse_link_header(
    value: str, *, local_fixture: bool, max_links: int
) -> list[dict[str, str]]:
    if not value:
        raise TckViolation("link-header-missing")
    links: list[dict[str, str]] = []
    for match in _LINK_PATTERN.finditer(value):
        if len(links) >= max_links:
            raise TckViolation("link-budget-exceeded")
        href = _safe_reference(match.group(1), local_fixture=local_fixture)
        params = match.group(2)
        rel_match = re.search(r"(?:^|;)\s*rel=\"?([^;\"]+)", params, re.IGNORECASE)
        if not rel_match:
            raise TckViolation("link-rel-missing")
        rel = " ".join(rel_match.group(1).strip().lower().split())
        _scan_safe_text(rel, local_fixture=local_fixture)
        type_match = re.search(r"(?:^|;)\s*type=\"?([^;\"]+)", params, re.IGNORECASE)
        links.append(
            {
                "href": href,
                "rel": rel,
                "type": type_match.group(1).strip().lower() if type_match else "",
            }
        )
    if not links:
        raise TckViolation("link-header-malformed")
    return links


def _same_metadata(left: Mapping[str, Any], right: Mapping[str, Any]) -> bool:
    return all(left.get(field) == right.get(field) for field in _PROBLEM_FIELDS)


def _problem_from_json(value: object, *, local_fixture: bool) -> dict[str, Any]:
    if not isinstance(value, Mapping):
        raise TckViolation("problem-json-invalid")
    for field_name in _PROBLEM_FIELDS:
        if field_name not in value:
            raise TckViolation("problem-metadata-incomplete")
    if (
        not isinstance(value["status"], int)
        or isinstance(value["status"], bool)
        or not 100 <= value["status"] <= 599
    ):
        raise TckViolation("problem-status-invalid")
    if not isinstance(value["code"], str) or not re.fullmatch(
        r"[a-z0-9][a-z0-9_.-]{0,63}", value["code"]
    ):
        raise TckViolation("problem-code-invalid")
    if not isinstance(value["type"], str) or not isinstance(value["instance"], str):
        raise TckViolation("problem-reference-invalid")
    if (
        len(value["type"]) > MAX_PROBLEM_TYPE_CHARS
        or len(value["instance"]) > MAX_PROBLEM_INSTANCE_CHARS
    ):
        raise TckViolation("problem-reference-oversize")
    _scan_safe_text(value["type"], local_fixture=local_fixture)
    _scan_safe_text(value["instance"], local_fixture=local_fixture)
    if not isinstance(value["retryable"], bool):
        raise TckViolation("problem-retryable-invalid")
    retry_after = value["retry_after_s"]
    if retry_after is not None:
        try:
            retry_after_value = float(retry_after)
        except (TypeError, ValueError, OverflowError) as exc:
            raise TckViolation("problem-retry-after-invalid") from exc
        if (
            isinstance(retry_after, bool)
            or not isinstance(retry_after, (int, float))
            or not math.isfinite(retry_after_value)
            or retry_after_value < 0
            or retry_after_value > MAX_RETRY_AFTER_SECONDS
        ):
            raise TckViolation("problem-retry-after-invalid")
    detail = value.get("detail", "")
    if not isinstance(detail, str):
        raise TckViolation("problem-detail-invalid")
    if len(detail) > MAX_PROBLEM_DETAIL_CHARS:
        raise TckViolation("problem-detail-oversize")
    _scan_safe_text(detail, local_fixture=local_fixture)
    return {field: value[field] for field in _PROBLEM_FIELDS}


def _problem_from_markdown(text: str, *, local_fixture: bool) -> dict[str, Any]:
    if not text.startswith("---\n"):
        raise TckViolation("structured-markdown-frontmatter-missing")
    try:
        frontmatter, body = text[4:].split("\n---", 1)
    except ValueError as exc:
        raise TckViolation("structured-markdown-frontmatter-invalid") from exc
    values: dict[str, Any] = {}
    for line in frontmatter.splitlines():
        if not line.strip():
            continue
        if ":" not in line:
            raise TckViolation("structured-markdown-frontmatter-invalid")
        key, raw = line.split(":", 1)
        key = key.strip()
        if key in values or key not in _PROBLEM_FIELDS:
            raise TckViolation("structured-markdown-frontmatter-invalid")
        try:
            values[key] = json.loads(raw.strip())
        except json.JSONDecodeError as exc:
            raise TckViolation("structured-markdown-frontmatter-invalid") from exc
    if set(values) != set(_PROBLEM_FIELDS):
        raise TckViolation("problem-metadata-incomplete")
    _scan_safe_text(body, local_fixture=local_fixture)
    return _problem_from_json(values, local_fixture=local_fixture)


def _public_json_document(
    response: TckResponse,
    *,
    expected_media_type: str,
    max_bytes: int,
    local_fixture: bool,
) -> tuple[object, dict[str, Any]]:
    if not 200 <= response.status < 300:
        raise TckViolation("unexpected-status")
    if _media_type(response) != expected_media_type:
        raise TckViolation("content-type-mismatch")
    text = _body_text(response, max_bytes=max_bytes, local_fixture=local_fixture)
    return _parse_json(text, local_fixture=local_fixture), _body_evidence(
        response, max_bytes=max_bytes
    )


def _problem_json_document(
    response: TckResponse,
    *,
    max_bytes: int,
    local_fixture: bool,
) -> tuple[object, dict[str, Any]]:
    if not 400 <= response.status <= 599:
        raise TckViolation("problem-status-invalid")
    if _media_type(response) != PROBLEM_JSON:
        raise TckViolation("content-type-mismatch")
    text = _body_text(response, max_bytes=max_bytes, local_fixture=local_fixture)
    return _parse_json(text, local_fixture=local_fixture), _body_evidence(
        response, max_bytes=max_bytes
    )


@dataclass(frozen=True)
class TckConfig:
    """Explicit target and applicability contract for one bounded TCK run."""

    origin: str
    allowed_origins: tuple[str, ...]
    local_fixture: bool = False
    applicable: bool = True
    markdown_path: str = "/"
    error_path: str | None = None
    discovery: Mapping[str, bool | str] = field(default_factory=dict)
    security_paths: tuple[str, ...] = ()
    auth_sensitive: bool = False
    require_api_endpoint: bool = False
    timeout: float = 5.0
    max_response_bytes: int = 512 * 1024
    max_links: int = 64

    def __post_init__(self) -> None:
        if not self.allowed_origins or len(self.allowed_origins) > 32:
            raise TckConfigurationError("origin-allowlist-invalid")
        origins = tuple(
            sorted(
                {
                    _normalized_origin(item, local_fixture=self.local_fixture)
                    for item in self.allowed_origins
                }
            )
        )
        origin = _normalized_origin(self.origin, local_fixture=self.local_fixture)
        if origin not in origins:
            raise TckConfigurationError("origin-not-allowlisted")
        try:
            timeout = float(self.timeout)
        except (TypeError, ValueError) as exc:
            raise TckConfigurationError("timeout-boundary-invalid") from exc
        if not 0.1 <= timeout <= MAX_TIMEOUT_SECONDS:
            raise TckConfigurationError("timeout-boundary-invalid")
        if (
            not isinstance(self.max_response_bytes, int)
            or not 1 <= self.max_response_bytes <= MAX_RESPONSE_BYTES
        ):
            raise TckConfigurationError("response-boundary-invalid")
        if not isinstance(self.max_links, int) or not 1 <= self.max_links <= MAX_LINKS:
            raise TckConfigurationError("link-boundary-invalid")
        if not isinstance(self.applicable, bool) or not isinstance(
            self.auth_sensitive, bool
        ):
            raise TckConfigurationError("applicability-invalid")
        object.__setattr__(self, "origin", origin)
        object.__setattr__(self, "allowed_origins", origins)
        object.__setattr__(self, "timeout", timeout)
        object.__setattr__(self, "markdown_path", _safe_path(self.markdown_path))
        if self.error_path is not None:
            object.__setattr__(self, "error_path", _safe_path(self.error_path))
        paths: dict[str, bool | str] = {}
        for name, setting in self.discovery.items():
            if name not in _DEFAULT_DISCOVERY_PATHS:
                raise TckConfigurationError("discovery-name-invalid")
            if isinstance(setting, str):
                paths[name] = _safe_path(setting)
            elif isinstance(setting, bool):
                paths[name] = setting
            else:
                raise TckConfigurationError("discovery-applicability-invalid")
        object.__setattr__(self, "discovery", dict(sorted(paths.items())))
        object.__setattr__(
            self,
            "security_paths",
            tuple(sorted(_safe_path(path) for path in self.security_paths)),
        )


class FixtureTransport:
    """Deterministic transport for focused TCK fixtures.

    Keys are ``(path, Accept)`` pairs, with an optional ``(path, "*")`` fallback.
    Fixture mode is still subject to every response, link, size, and secret gate;
    it only removes DNS and network nondeterminism.
    """

    def __init__(self, responses: Mapping[tuple[str, str], TckResponse | Exception]):
        self.responses = dict(responses)
        self.requests: list[tuple[str, str]] = []

    def fetch(
        self, path: str, accept: str, *, timeout: float, max_bytes: int
    ) -> TckResponse:
        del timeout, max_bytes
        self.requests.append((path, accept))
        response = self.responses.get((path, accept))
        if response is None:
            response = self.responses.get((path, "*"))
        if response is None:
            raise TckUnavailable("fixture-response-unavailable")
        if isinstance(response, Exception):
            raise response
        return response


class _RejectRedirects(urllib.request.HTTPRedirectHandler):
    def redirect_request(self, req, fp, code, msg, headers, newurl):  # noqa: ANN001
        raise TckViolation("redirect-rejected")


class UrllibTransport:
    """Non-redirecting HTTPS transport with no ambient proxy or credentials."""

    def __init__(self, config: TckConfig):
        self.config = config

    def _assert_destination(self) -> None:
        if self.config.local_fixture:
            return
        parsed = urlsplit(self.config.origin)
        host = parsed.hostname or ""
        port = parsed.port or 443
        try:
            answers = socket.getaddrinfo(host, port, type=socket.SOCK_STREAM)
        except OSError as exc:
            raise TckUnavailable("dns-unavailable") from exc
        if len(answers) > 32:
            raise TckViolation("dns-answer-budget-exceeded")
        addresses: set[str] = set()
        for answer in answers[:32]:
            try:
                addresses.add(str(ipaddress.ip_address(answer[4][0])))
            except (IndexError, TypeError, ValueError) as exc:
                raise TckViolation("dns-answer-invalid") from exc
        if not addresses or any(
            not ipaddress.ip_address(item).is_global for item in addresses
        ):
            raise TckViolation("private-destination")

    def fetch(
        self, path: str, accept: str, *, timeout: float, max_bytes: int
    ) -> TckResponse:
        self._assert_destination()
        url = f"{self.config.origin}{path}"
        request = urllib.request.Request(
            url,
            headers={"Accept": accept, "User-Agent": "agent-readiness-tck/v1"},
            method="GET",
        )
        try:
            context = ssl.create_default_context()
            opener = urllib.request.build_opener(
                urllib.request.ProxyHandler({}),
                urllib.request.HTTPSHandler(context=context),
                _RejectRedirects(),
            )
            with opener.open(request, timeout=timeout) as response:
                return self._read(response, max_bytes=max_bytes)
        except urllib.error.HTTPError as exc:
            return self._read(exc, max_bytes=max_bytes)
        except TckViolation:
            raise
        except (urllib.error.URLError, TimeoutError, OSError, ssl.SSLError) as exc:
            raise TckUnavailable("remote-unavailable") from exc

    @staticmethod
    def _read(response: Any, *, max_bytes: int) -> TckResponse:
        try:
            headers = dict(response.headers)
            body = response.read(max_bytes + 1)
        except (OSError, ValueError) as exc:
            raise TckUnavailable("response-unavailable") from exc
        if len(body) > max_bytes:
            raise TckViolation("response-size-budget-exceeded")
        return TckResponse(
            status=int(getattr(response, "status", getattr(response, "code", 0))),
            headers=headers,
            body=body,
        )


def _fetch(
    transport: TckTransport,
    path: str,
    accept: str,
    config: TckConfig,
) -> tuple[TckResponse | None, str | None]:
    try:
        return (
            transport.fetch(
                path,
                accept,
                timeout=config.timeout,
                max_bytes=config.max_response_bytes,
            ),
            None,
        )
    except TckUnavailable:
        return None, UNAVAILABLE
    except TckViolation:
        return None, FAIL
    except (OSError, ValueError):
        return None, UNAVAILABLE


def _content_checks(
    config: TckConfig, transport: TckTransport
) -> tuple[list[dict[str, Any]], TckResponse | None, TckResponse | None]:
    checks: list[dict[str, Any]] = []
    markdown, markdown_status = _fetch(
        transport, config.markdown_path, MARKDOWN, config
    )
    if markdown is None:
        checks.append(
            _check(
                "markdown-negotiation",
                markdown_status or UNAVAILABLE,
                reason="target-unavailable"
                if markdown_status == UNAVAILABLE
                else "response-rejected",
            )
        )
    else:
        try:
            evidence = _body_evidence(markdown, max_bytes=config.max_response_bytes)
            _body_text(
                markdown,
                max_bytes=config.max_response_bytes,
                local_fixture=config.local_fixture,
            )
            if not 200 <= markdown.status < 300 or _media_type(markdown) != MARKDOWN:
                raise TckViolation("content-negotiation-mismatch")
            checks.append(_check("markdown-negotiation", PASS, **evidence))
        except TckViolation as exc:
            checks.append(_check("markdown-negotiation", FAIL, reason=str(exc)))

    html_response, html_status = _fetch(transport, config.markdown_path, HTML, config)
    if html_response is None:
        checks.append(
            _check(
                "html-negotiation",
                html_status or UNAVAILABLE,
                reason="target-unavailable"
                if html_status == UNAVAILABLE
                else "response-rejected",
            )
        )
    else:
        try:
            evidence = _body_evidence(
                html_response, max_bytes=config.max_response_bytes
            )
            _body_text(
                html_response,
                max_bytes=config.max_response_bytes,
                local_fixture=config.local_fixture,
            )
            if (
                not 200 <= html_response.status < 300
                or _media_type(html_response) != HTML
            ):
                raise TckViolation("content-negotiation-mismatch")
            checks.append(_check("html-negotiation", PASS, **evidence))
        except TckViolation as exc:
            checks.append(_check("html-negotiation", FAIL, reason=str(exc)))

    if markdown is None:
        status = markdown_status or UNAVAILABLE
        for identifier in ("vary-accept", "cache-policy", "link-header"):
            checks.append(
                _check(identifier, status, reason="markdown-response-unavailable")
            )
        return checks, markdown, html_response

    try:
        vary = {
            item.strip().lower()
            for item in _header(markdown, "vary").split(",")
            if item.strip()
        }
        _scan_safe_text(" ".join(sorted(vary)), local_fixture=config.local_fixture)
        if "accept" not in vary:
            raise TckViolation("vary-accept-missing")
        checks.append(_check("vary-accept", PASS, fields=sorted(vary)))
    except TckViolation as exc:
        checks.append(_check("vary-accept", FAIL, reason=str(exc)))

    try:
        cache = _header(markdown, "cache-control").lower()
        if not cache:
            raise TckViolation("cache-control-missing")
        _scan_safe_text(cache, local_fixture=config.local_fixture)
        if config.auth_sensitive and not any(
            token in cache for token in ("private", "no-store")
        ):
            raise TckViolation("authenticated-cache-not-private")
        directives = sorted(
            {item.strip().split("=", 1)[0] for item in cache.split(",") if item.strip()}
        )
        checks.append(_check("cache-policy", PASS, directives=directives))
    except TckViolation as exc:
        checks.append(_check("cache-policy", FAIL, reason=str(exc)))

    try:
        links = _parse_link_header(
            _header(markdown, "link"),
            local_fixture=config.local_fixture,
            max_links=config.max_links,
        )
        if not any("api-catalog" in link["rel"].split() for link in links):
            raise TckViolation("api-catalog-link-missing")
        checks.append(
            _check(
                "link-header",
                PASS,
                count=len(links),
                relations=sorted({link["rel"] for link in links}),
            )
        )
        checks.append(
            _check("link-budget", PASS, count=len(links), maximum=config.max_links)
        )
    except TckViolation as exc:
        checks.append(_check("link-header", FAIL, reason=str(exc)))
        checks.append(
            _check("link-budget", FAIL, reason=str(exc), maximum=config.max_links)
        )
    return checks, markdown, html_response


def _discovery_check(
    name: str,
    response: TckResponse,
    config: TckConfig,
) -> dict[str, Any]:
    try:
        value, evidence = _public_json_document(
            response,
            expected_media_type=_DISCOVERY_MEDIA_TYPES[name],
            max_bytes=config.max_response_bytes,
            local_fixture=config.local_fixture,
        )
        if not isinstance(value, Mapping):
            raise TckViolation("discovery-document-invalid")
        if name == "api_catalog":
            if value.get("profile") != API_CATALOG_PROFILE:
                raise TckViolation("api-catalog-profile-stale")
            linksets = value.get("linkset")
            if not isinstance(linksets, list) or not linksets:
                raise TckViolation("api-catalog-linkset-invalid")
            count = 0
            has_endpoint = False
            for linkset in linksets:
                if not isinstance(linkset, Mapping):
                    raise TckViolation("api-catalog-linkset-invalid")
                for field_name in ("item", "describedby"):
                    links = linkset.get(field_name, [])
                    if not isinstance(links, list):
                        raise TckViolation("api-catalog-links-invalid")
                    count += len(links)
                    for link in links:
                        if not isinstance(link, Mapping) or "href" not in link:
                            raise TckViolation("api-catalog-link-invalid")
                        _safe_reference(
                            link["href"], local_fixture=config.local_fixture
                        )
                        if field_name == "item" and not str(link["href"]).startswith(
                            ("/.well-known", ".well-known")
                        ):
                            has_endpoint = True
            if count > config.max_links:
                raise TckViolation("link-budget-exceeded")
            if config.require_api_endpoint and not has_endpoint:
                raise TckViolation("api-catalog-endpoint-missing")
            evidence = {**evidence, "links": count}
        elif name == "mcp_server_card":
            if value.get("schema_version") != "mcp-server-card/v1-experimental":
                raise TckViolation("mcp-card-stale")
            if value.get("experimental") is not True:
                raise TckViolation("mcp-card-maturity-invalid")
            if not isinstance(value.get("transports"), list) or not value["transports"]:
                raise TckViolation("mcp-card-transport-missing")
        elif name == "agent_skills":
            if value.get("schema_version") != "agent-skills/v1":
                raise TckViolation("agent-skills-index-stale")
            skills = value.get("skills")
            if not isinstance(skills, list) or len(skills) > config.max_links:
                raise TckViolation("agent-skills-budget-invalid")
            for skill in skills:
                if not isinstance(skill, Mapping) or not isinstance(
                    skill.get("path"), str
                ):
                    raise TckViolation("agent-skills-entry-invalid")
                _safe_reference(skill["path"], local_fixture=config.local_fixture)
        elif name == "a2a_card":
            if not all(
                isinstance(value.get(field_name), str) and value[field_name]
                for field_name in ("name", "type", "version")
            ):
                raise TckViolation("a2a-card-invalid")
        elif not value:
            raise TckViolation("oauth-metadata-empty")
        return _check(name.replace("_", "-"), PASS, **evidence)
    except TckViolation as exc:
        return _check(name.replace("_", "-"), FAIL, reason=str(exc))


def _run_discovery(config: TckConfig, transport: TckTransport) -> list[dict[str, Any]]:
    checks: list[dict[str, Any]] = []
    for name, setting in config.discovery.items():
        if setting is False:
            checks.append(
                _check(name.replace("_", "-"), NOT_APPLICABLE, reason="disabled")
            )
            continue
        path = _DEFAULT_DISCOVERY_PATHS[name] if setting is True else setting
        response, status = _fetch(transport, path, _DISCOVERY_MEDIA_TYPES[name], config)
        if response is None:
            checks.append(
                _check(
                    name.replace("_", "-"),
                    status or UNAVAILABLE,
                    reason="target-unavailable"
                    if status == UNAVAILABLE
                    else "response-rejected",
                )
            )
        else:
            checks.append(_discovery_check(name, response, config))
    return checks


def _run_error_parity(
    config: TckConfig, transport: TckTransport
) -> list[dict[str, Any]]:
    if config.error_path is None:
        return [_check("error-parity", NOT_APPLICABLE, reason="no-error-surface-bound")]
    json_response, json_status = _fetch(
        transport, config.error_path, PROBLEM_JSON, config
    )
    markdown_response, markdown_status = _fetch(
        transport, config.error_path, MARKDOWN, config
    )
    if json_response is None or markdown_response is None:
        status = UNAVAILABLE if UNAVAILABLE in {json_status, markdown_status} else FAIL
        return [_check("error-parity", status, reason="error-surface-unavailable")]
    try:
        json_value, json_evidence = _problem_json_document(
            json_response,
            max_bytes=config.max_response_bytes,
            local_fixture=config.local_fixture,
        )
        json_metadata = _problem_from_json(
            json_value, local_fixture=config.local_fixture
        )
        markdown_text = _body_text(
            markdown_response,
            max_bytes=config.max_response_bytes,
            local_fixture=config.local_fixture,
        )
        if (
            not 400 <= markdown_response.status <= 599
            or _media_type(markdown_response) != MARKDOWN
        ):
            raise TckViolation("structured-markdown-error-invalid")
        markdown_metadata = _problem_from_markdown(
            markdown_text, local_fixture=config.local_fixture
        )
        if (
            json_response.status != json_metadata["status"]
            or json_response.status != markdown_metadata["status"]
        ):
            raise TckViolation("problem-status-mismatch")
        if not _same_metadata(json_metadata, markdown_metadata):
            raise TckViolation("problem-metadata-parity-mismatch")
        if (
            json_metadata["status"] in {401, 403}
            or json_metadata["code"] in _DENIAL_CODES
        ):
            if json_metadata["retryable"] or json_metadata["retry_after_s"] is not None:
                raise TckViolation("denial-marked-retryable")
        return [
            _check(
                "error-parity",
                PASS,
                json=json_evidence,
                markdown=_body_evidence(
                    markdown_response, max_bytes=config.max_response_bytes
                ),
                denial_non_retryable=json_metadata["status"] in {401, 403}
                or json_metadata["code"] in _DENIAL_CODES,
            )
        ]
    except TckViolation as exc:
        return [_check("error-parity", FAIL, reason=str(exc))]


def _run_security_negatives(
    config: TckConfig, transport: TckTransport
) -> list[dict[str, Any]]:
    if not config.security_paths:
        return [
            _check("auth-security", NOT_APPLICABLE, reason="no-negative-surface-bound")
        ]
    results: list[dict[str, Any]] = []
    for path in config.security_paths:
        response, status = _fetch(transport, path, PROBLEM_JSON, config)
        identifier = f"auth-security:{path}"
        if response is None:
            results.append(
                _check(
                    identifier,
                    status or UNAVAILABLE,
                    reason="negative-surface-unavailable",
                )
            )
            continue
        try:
            value, evidence = _problem_json_document(
                response,
                max_bytes=config.max_response_bytes,
                local_fixture=config.local_fixture,
            )
            metadata = _problem_from_json(value, local_fixture=config.local_fixture)
            if (
                response.status not in {401, 403}
                or metadata["status"] != response.status
            ):
                raise TckViolation("negative-not-denied")
            if metadata["retryable"] or metadata["retry_after_s"] is not None:
                raise TckViolation("denial-marked-retryable")
            results.append(_check(identifier, PASS, **evidence))
        except TckViolation as exc:
            results.append(_check(identifier, FAIL, reason=str(exc)))
    return results


@dataclass(frozen=True)
class TckResult:
    """Structured evidence; no raw URLs beyond the validated target origin."""

    status: str
    checks: tuple[dict[str, Any], ...]
    target_origin: str
    fixture_mode: bool
    limits: Mapping[str, Any]

    def to_dict(self) -> dict[str, Any]:
        return {
            "schema_version": TCK_SCHEMA_VERSION,
            "contract_version": TCK_CONTRACT_VERSION,
            "maturity": TCK_MATURITY,
            "standards": list(TCK_STANDARDS),
            "status": self.status,
            "target_origin": self.target_origin,
            "fixture_mode": self.fixture_mode,
            "limits": dict(self.limits),
            "checks": list(self.checks),
        }

    def to_json(self) -> str:
        return (
            json.dumps(self.to_dict(), ensure_ascii=False, sort_keys=True, indent=2)
            + "\n"
        )


def _overall_status(checks: list[dict[str, Any]]) -> str:
    statuses = [check["status"] for check in checks]
    if FAIL in statuses:
        return FAIL
    if UNAVAILABLE in statuses:
        return UNAVAILABLE
    if statuses and all(status == NOT_APPLICABLE for status in statuses):
        return NOT_APPLICABLE
    return PASS


def run_tck(config: TckConfig, *, transport: TckTransport | None = None) -> TckResult:
    """Run only explicitly applicable checks and return structured evidence."""

    if not config.applicable:
        checks = [
            _check("agent-readiness-tck", NOT_APPLICABLE, reason="surface-disabled")
        ]
    else:
        active_transport = transport or UrllibTransport(config)
        checks, _, _ = _content_checks(config, active_transport)
        checks.extend(_run_discovery(config, active_transport))
        checks.extend(_run_error_parity(config, active_transport))
        checks.extend(_run_security_negatives(config, active_transport))
    return TckResult(
        status=_overall_status(checks),
        checks=tuple(checks),
        target_origin=config.origin,
        fixture_mode=config.local_fixture,
        limits={
            "timeout_s": config.timeout,
            "max_response_bytes": config.max_response_bytes,
            "max_links": config.max_links,
            "redirects": "rejected",
            "authorization": "never-sent",
            "query_strings": "rejected",
            "private_destinations": "local-fixture-only",
        },
    )


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--origin", required=True)
    parser.add_argument("--allow-origin", action="append", required=True)
    parser.add_argument("--local-fixture", action="store_true")
    parser.add_argument("--markdown-path", default="/")
    parser.add_argument("--error-path")
    parser.add_argument("--negative-path", action="append", default=[])
    parser.add_argument(
        "--discover", action="append", choices=sorted(_DEFAULT_DISCOVERY_PATHS)
    )
    parser.add_argument("--auth-sensitive", action="store_true")
    parser.add_argument("--require-api-endpoint", action="store_true")
    parser.add_argument("--timeout", type=float, default=5.0)
    parser.add_argument("--max-response-bytes", type=int, default=512 * 1024)
    parser.add_argument("--max-links", type=int, default=64)
    args = parser.parse_args(argv)
    try:
        config = TckConfig(
            origin=args.origin,
            allowed_origins=tuple(args.allow_origin),
            local_fixture=args.local_fixture,
            markdown_path=args.markdown_path,
            error_path=args.error_path,
            discovery={name: True for name in args.discover or ()},
            security_paths=tuple(args.negative_path),
            auth_sensitive=args.auth_sensitive,
            require_api_endpoint=args.require_api_endpoint,
            timeout=args.timeout,
            max_response_bytes=args.max_response_bytes,
            max_links=args.max_links,
        )
        result = run_tck(config)
    except TckConfigurationError as exc:
        print(f"agent-readiness TCK configuration rejected: {exc}")
        return 2
    print(result.to_json(), end="")
    return 0 if result.status in {PASS, NOT_APPLICABLE} else 1


if __name__ == "__main__":
    raise SystemExit(main())
