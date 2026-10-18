# Deployment

This page covers documentation delivery and running `webarchiver` as long-lived servers.

## Documentation site

Authorized public publication through mcp-builder includes GitHub Pages using the
checked `.github/workflows/pages.yml`, `mkdocs.yml` and `docs/` sources. Private
repository publication stays private and does not enable Pages. When using another
publication process, configure Pages to use GitHub Actions before running the
existing Pages workflow.

Review documentation for public release before publishing. Confirm that the Pages
run deployed the reviewed commit successfully, then check its public HTTPS URL and
readiness assets. A generated workflow file or accepted dispatch alone does not
prove delivery. Keep the run URL, source revision and live verification results in
the publication evidence.

## Build from the published release

The production Dockerfile installs the published `webarchiver[mcp]` wheel at
an exact version with `pip install --only-binary :all:`. It never installs the
source tree and builds no tools from source. The base image is Python 3.14 slim,
pinned by digest, and the server runs as a non-root user.

Publish the release first, then build the image for that version:

```bash
docker build --file docker/Dockerfile --target mcp --tag webarchiver:<version>-mcp .
```

For an enabled agent surface, select `--target agent`. The shared
[container workflow](https://github.com/Knuckles-Team/pipelines/blob/7b3d18d72b5622d455ece3bbe45a9482bc6e8b5e/.github/workflows/container_pipeline.yml)
also checks out the exact workflow commit. Build only on an approved image-build
host. Publish through the repository's approved process, then deploy the returned
image manifest digest through `MCP_IMAGE` (and `AGENT_IMAGE` when enabled).
A source commit does not freeze the index-resolved dependency closure. For a
qualified offline wheel build, use the shared
[runtime artifact contract](https://github.com/Knuckles-Team/pipelines/blob/7b3d18d72b5622d455ece3bbe45a9482bc6e8b5e/reference/container-runtime.md)
with its producer receipts and full hashes. This scaffold does not claim that
qualification or provision a producer, registry credentials or deployment.

> `webarchiver` ships an **MCP server** (console script `webarchiver-mcp`).

<!-- BEGIN GENERATED: deployment-options -->
## Deployment Options

`webarchiver` exposes its MCP server (console script `webarchiver-mcp`) four ways. Pick the
row that matches where the server runs relative to your MCP client, then copy the
matching `mcp_config.json` below.

| # | Option | Transport | Where it runs | `mcp_config.json` key |
|---|--------|-----------|---------------|------------------------|
| 1 | stdio | `stdio` | client launches a subprocess | `command` |
| 2 | Streamable-HTTP (local) | `streamable-http` | a local network port | `command` or `url` |
| 3 | Local container | `stdio` | reviewed Docker / Podman image on this host | `command` |
| 4 | Remote URL | `streamable-http` | operator-owned authenticated TLS ingress | `url` |

### 1. stdio (local subprocess)

```json
{
  "mcpServers": {
    "webarchiver-mcp": {
      "command": "webarchiver-mcp",
      "args": [],
      "env": {
        "SYSTEMTOOL": "true"
      }
    }
  }
}
```

### 2. Streamable-HTTP (local process)

```bash
webarchiver-mcp --transport streamable-http --host 127.0.0.1 --port 8000
curl -s http://loopback.invalid:8000/health        # {"status":"OK"}
```

Connect to the running process by URL:

```json
{
  "mcpServers": {
    "webarchiver-mcp": { "url": "http://loopback.invalid:8000/mcp" }
  }
}
```

### 3. Local container

Launch a container directly from `mcp_config.json` (swap `docker` for `podman` for a
daemonless runtime):

```json
{
  "mcpServers": {
    "webarchiver-mcp": {
      "command": "docker",
      "args": [
        "run", "-i", "--rm", "--read-only", "--cap-drop=ALL",
        "--security-opt=no-new-privileges", "--pids-limit=256",
        "--tmpfs", "/tmp:rw,noexec,nosuid,nodev,size=64m",
        "-e", "TRANSPORT=stdio",
        "<registry>/webarchiver@sha256:<digest>"
      ]
    }
  }
}
```

Supply the provider profile through the operator-owned connector configuration mount or secret
projection. The image and this document contain no endpoint, credential, or trust material.

### 4. Remote URL (authenticated TLS ingress)

When the server is deployed remotely, connect through its operator-supplied
authenticated HTTPS ingress; no local process or image is required:

```json
{
  "mcpServers": {
    "webarchiver-mcp": { "url": "https://service.example.invalid/mcp" }
  }
}
```

Configure outbound MCP identity and trust references in SDK configuration. The server
must use direct TLS or an explicitly trusted TLS-terminating ingress and an exact
`MCP_ALLOWED_HOSTS` policy; do not commit the endpoint, credentials, or trust paths.
<!-- END GENERATED: deployment-options -->

## Docker Compose

```bash
docker compose -f docker/mcp.compose.yml up -d
```
