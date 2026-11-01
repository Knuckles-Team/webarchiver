# CONN-WEBARCHIVER-WEB-SOURCE — Quickstart

The shortest path that shows the served behaviour working.

```text
uv run pytest tests/test_conformance.py tests/test_crawl.py tests/test_extract.py tests/test_fleet_name.py tests/test_kg_ingest.py tests/test_served.py
```

The command starts the connector in process and calls the served tools through the MCP client. A test marked planned in `test-spec.md` runs once the code change that lands its row adds it.
