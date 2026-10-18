# Backing Platform — Webarchiver

`webarchiver` is a **client** of a backing service instance. This page provides a
Docker recipe for deploying one locally as an operator-selected provider endpoint.

!!! note "Backing-system recipe"
    Each connector in the ecosystem follows the same convention — a
    `docs/platform.md` recipe for the system it integrates with, accompanied by a
    sample Compose stack. Systems offered only as a managed service have no local
    recipe.

## Single-node deployment (Compose)

```yaml
# docker/platform.compose.yml — replace with the real backing-service recipe
services:
  platform:
    image: REPLACE_ME
    restart: unless-stopped
    ports:
      - "8080:8080"
```
