# Shared MkDocs theme

This folder is the canonical source for the five ecosystem documentation sites. `scripts/sync_mkdocs_theme.py` copies its generated files into a consuming repository and checks that committed copies are byte-identical.

## Generated files

| Source | Consumer path |
| --- | --- |
| `extra.css` | `<content-source>/stylesheets/extra.css` |
| `overrides/main.html` | not synced: `custom_dir` serves it from the theme checkout (`.pipeline-theme/templates/mkdocs-theme/overrides`) |
| `assets/*` | `<content-source>/assets/*` |
| `glossary.md` | `<content-source>/glossary.md` |
| `base.mkdocs.yml` | inherited directly from the pinned pipelines checkout |

`<content-source>` is the explicitly declared `docs` or `pages` directory. Run `python scripts/sync_mkdocs_theme.py sync --root REPOSITORY --content-source docs` to update files, and the same command with `check` to check exact equality without writing. The Pages workflow checks the committed assets against its immutable workflow checkout before building.

## Runtime architecture diagram

The runtime architecture diagram is not a theme asset and is never copied into a consumer. There is exactly one file, `docs/assets/runtime-architecture.svg` in Knuckles-Team/epistemic-graph, and every page that shows it references the URL `https://raw.githubusercontent.com/Knuckles-Team/epistemic-graph/main/docs/assets/runtime-architecture.svg`. The `check` mode fails when a page under the content source references `runtime-architecture.svg` by any other path.

## MkDocs configuration

The repository's `mkdocs.yml` inherits `templates/mkdocs-theme/base.mkdocs.yml` and supplies `extra.ecosystem.current` with its own slug (`agent-webui`, `arbora`, `agent-utilities`, `epistemic-graph`, or `agent-connector-sdk`). It continues to own its site name, URL, content directory, and navigation. For local builds, check out the exact pinned `pipelines` revision into `.pipeline-theme`, run the `sync` command above, then run `mkdocs build --strict`.

Use `.site-hero`, `.site-card-grid` / `.site-card`, `.site-ownership__grid` / `.site-ownership__item`, and the ordered `.site-flow` components for landing-page structure. Prefer semantic HTML and retain visible keyboard focus. The common theme uses native `<details>` for the site switcher and does not require custom JavaScript.

The root `README.md` remains the short entry point. It keeps its exact ordered headings: Overview, Key capabilities, Documentation, Architecture, Quick start, Contributing, License. Deep reference material belongs in Pages. Public home pages describe the current bundled ecosystem in present tense. They contain no planning, migration, worktree, or future-release status.
