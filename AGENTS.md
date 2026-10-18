# Webarchiver engineering contract

## Architecture

`webarchiver/api/` owns service operations; `mcp/` adapts them to tools.
The connector SDK owns HTTP, credential references, TLS, server policy,
registration, content publication and ingestion transport. The graph engine
owns durable storage and semantics. Connectors are MCP-only and depend on
`agent-connector-sdk` alone; there is no agent mode.

## Setup and commands

Use the repository's locked environment. Install its declared test dependencies
and pre-commit before running `pre-commit run --all-files` and `pytest -q`.
The shared pipelines hooks own scanner versions and gate policy; provision
those tools through the approved development environment, never a hook-time
installer. Generate schemas with `python scripts/generate_tool_schemas.py`,
then check them with `--check`. Run `mkdocs build --strict` for documentation.

## Development rules

Keep configuration as operator-provided references. Do not generate credentials,
commit resolved secrets, bypass failing gates, or infer publication/deployment
permission from a scaffolding request. Test real contract behavior with fakes
at outbound boundaries. A schema fingerprint is not release certification.

## Documentation and delivery

[README.md](README.md) contains install/start instructions; [docs/](docs/index.md)
contains usage and constraints. Keep both synchronized with code and examples.
Follow the current shared pipelines spec standard for requirement bundles and
its generators for status and the delivery dashboard; do not hand-maintain status.

## Branching and isolation

Use a distinct topic branch and real Git worktree. Stage reviewed paths only;
never stash another session's work or disable verification. Commit, push, open
a PR, merge, publish and deploy each require the applicable user authorization
and checks. Do not automatically merge or remove worktrees after scaffolding.
