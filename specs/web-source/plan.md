# CONN-WEBARCHIVER-WEB-SOURCE — Design and implementation plan

Governing spec: [spec.md](spec.md).

## Existing system and reuse

`Webarchiver.launch_browser` at `webarchiver/webarchiver.py:63` holds the existing browser capture with ad removal. It becomes the render and screenshot path. The fetch and extraction tools are new. The SDK supplies the contract types, the server factory, the egress policy and the conformance kit.

## Architecture

Call path: arbora `research.web` -> engine work item of kind `WebPage` -> SDK ingest worker -> `WebFetchSourceAdapter.extract` -> this connector `web_extract` -> engine `SourceIngest`.

The connector holds no store and no selection rule. It returns one page result or one typed refusal per call.

## Interfaces and data model

The tool arguments and results are the SDK contract types of `SCION-SOURCE-INGEST-R005.40.1`. No connector-local result type exists.

## Live integration path

The production caller is `WebFetchSourceAdapter.extract` in the SDK. arbora reaches it through the engine work item of `ARBORA-OPS-R067.2`.

## Quality and release gates

The SDK conformance kit of `SCION-SOURCE-INGEST-R005.40.2` must pass against the served connector.

## Risks, alternatives, and decisions

A spec-only change on `main` must not publish a release. Merge commits for spec text carry `[skip ci]`.
