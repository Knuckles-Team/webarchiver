# Spec delivery

[Open the published delivery dashboard](https://knuckles-team.github.io/webarchiver/spec-delivery/).

The shared Pages pipeline builds this dashboard from canonical
`specs/*/status.json` files selected by `.config/spec-dashboard.json`.
The repository owns the source configuration; the pinned shared pipeline owns
rendering and validation. Update source specs through the reviewed spec process.

The starter capability is **SPECIFIED** with empty delivery receipts. Missing or
unverified evidence does not establish delivery, release, or deployment.
Regenerate status with the shared `pipelines-hook spec-status --write` command
after reviewed implementation commits and test bindings exist; commit the
resulting source status. Read the [spec index](https://github.com/Knuckles-Team/webarchiver/blob/main/specs/README.md)
and [architecture](architecture.md) for source mappings and declared dependencies.
The dashboard is a build-time snapshot, refreshed on every push to main or an
explicit Pages workflow run. Agent readiness uses the separate canonical
`docs/agent-readiness.json` and its packaged schema.
