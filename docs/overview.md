# webarchiver — Concept Overview

> **Category**: Integration | **Ecosystem Role**: MCP Server
> Built on [`scion-sdk`](https://github.com/Knuckles-Team/scion-sdk).

## Description

Governed web fetch, extract, render, screenshot and link connector

## Architecture

This project follows the standardized agent-package pattern:

- **Modular Design**: split into `api/` (client mixins) and `mcp/` (one tool per operation
  tool modules) for cleaner organization.
- **Dynamic Tool Registration**: per-operation tools, strictly
  lowercase, each togglable with a `*TOOL` environment flag.

## Concept Registry

Project concepts are listed in [Concepts](concepts.md).
