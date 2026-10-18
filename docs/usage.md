# Usage — API / CLI / MCP

`webarchiver` exposes the same capability three ways: as **MCP tools** an agent
calls, as a **Python API** you import, and as a **CLI**.

## As an MCP server

Once [deployed](deployment.md), the server registers one typed, read-only
tool modules. Each module is independently togglable with a `*TOOL` environment
flag.

## As a Python API

```python
from webarchiver.auth import get_client

api = get_client()        # builds the fetch policy from SDK settings
result = await api.extract("https://example.org/article")
print(result.page.title, result.page.canonical_url)
```

## As a CLI

Optionally tune the fetch policy (`WEBARCHIVER_MIN_INTERVAL_S`, `WEBARCHIVER_MAX_BYTES`,
`WEBARCHIVER_OBEY_ROBOTS`), then run `webarchiver-mcp --transport stdio`.

### Explicit HTTP endpoint

HTTPS remains the default. For an existing HTTP-only endpoint you are authorized
to use, set `WEBARCHIVER_BASE_URL=http://service.example.invalid` and explicitly
set `WEBARCHIVER_ALLOW_PLAINTEXT=true`. This forwards the SDK's
`HttpClientOptions.allow_plaintext` choice only to that vendor client. Requests
remain bound to its exact scheme, host and port; redirects stay disabled.
HTTP carries requests without TLS encryption. The flag never retries HTTPS over
HTTP, changes certificate verification, or authorizes another endpoint. OIDC
token exchanges retain their separate TLS policy. Leave the flag false for HTTPS.
