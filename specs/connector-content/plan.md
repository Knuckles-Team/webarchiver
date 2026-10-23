# CONN-WEBARCHIVER-CONNECTOR-CONTENT — Design and implementation plan

Governing spec: [spec.md](spec.md).

## Architecture

`pyproject.toml` declares `webarchiver-mcp` as the connector identity. `create_mcp_server` resolves the packaged content of `webarchiver` from it.
