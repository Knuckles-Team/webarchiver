# Installation

`webarchiver` is a standard Python package and a prebuilt container image.

## Requirements

- **Python 3.12–3.14**.
- Optional SDK configuration for the fetch policy; the connector needs no credentials.

## From PyPI (recommended)

```bash
pip install webarchiver
```

### Optional extras

| Extra | Install | Pulls in |
|---|---|---|
| `mcp` | `pip install "webarchiver[mcp]"` | MCP runtime (`scion-sdk`) |
| `all` | `pip install "webarchiver[all]"` | Everything above |

## From source

```bash
git clone https://github.com/Knuckles-Team/webarchiver.git
cd webarchiver
pip install -e ".[mcp]"
```

## Docker

```bash
IMAGE_REF='<registry>/webarchiver@sha256:<digest>'
docker pull "$IMAGE_REF"
```
