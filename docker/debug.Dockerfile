FROM python:3.14-slim@sha256:a2b82f3c48559aa0a8446d9af49826b6e2b2016f4cd2afabfe6013ec53729170
COPY --from=ghcr.io/astral-sh/uv:0.11.7@sha256:240fb85ab0f263ef12f492d8476aa3a2e4e1e333f7d67fbdd923d00a506a516a /uv /uvx /bin/

ARG HOST=127.0.0.1
ARG PORT=8000
ARG TRANSPORT="stdio"
ARG AUTH_TYPE="none"

ENV HOST=${HOST} \
    PORT=${PORT} \
    TRANSPORT=${TRANSPORT} \
    AUTH_TYPE=${AUTH_TYPE} \
    PYTHONUNBUFFERED=1 \
    PATH="/usr/local/cargo/bin:/root/.local/bin:/usr/local/bin:${PATH}" \
    UV_HTTP_TIMEOUT=3600 \
    UV_SYSTEM_PYTHON=1 \
    UV_COMPILE_BYTECODE=1

# Install bounded development dependencies from the base distribution.
RUN apt-get update \
    && apt-get install -y --no-install-recommends default-jre ripgrep tree fd-find nano build-essential cmake libssl-dev libcurl4-openssl-dev pkg-config cargo rustc \
    && apt-get clean \
    && rm -rf /var/lib/apt/lists/*

WORKDIR /app
COPY . /app

# Install the local MCP package for debugging.
RUN uv pip install --system --upgrade --verbose --no-cache --break-system-packages --prerelease=allow .[mcp]

CMD ["webarchiver-mcp"]
