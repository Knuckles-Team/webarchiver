# Changelog

All notable changes to this project will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.1.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [1.2.6] - 2026-11-06

### Changed
- Surface backfill: declare the Connector (entry point webarchiver:connector), 4 tool-use contracts, data locations, policy resource, agent definitions for both prompts, scion-sdk 0.9

## [1.2.5] - 2026-11-06

### Added
- Domain ontology for every tool result, rolled up to the medulla core web resource, web capture, dataset and observation classes.
- Tool-use contracts, feature, skill and prompt links in `pack.ttl`; live access contracts in `access_contracts.ttl`.
- Prompts `webarchiver_operator` and `webarchiver_market_researcher`, written as agent definitions.
- Skills `webarchiver-web-capture` and `webarchiver-market-research-capture`.

### Removed
- The starter skill `webarchiver-starter` and the stub prompt `webarchiver_specialist`.

## [1.2.3] - 2026-10-30

### Changed
- Migrated to the `scion_sdk` import package; requires `scion-sdk>=0.6.4,<0.7.0`.

## [1.2.2] - 2026-10-23

### Changed
- Requires `agent-connector-sdk>=0.4.1`; data sources are declared in code (`connector_sources`).

## [Unreleased]

Scaffold generated: 2026-10-18. This is not a release or delivery date.

### Added
- Initial scaffold; release and delivery remain unclaimed.
- Modular subfolders for API wrappers (`api/`) and action-routed MCP tools (`mcp/`).
- Material-theme mkdocs documentation site (7 standard pages).
- Full pre-commit quality gate and flat `tests/` structure.
