# syntax=docker/dockerfile:1
# MCP serving image. It installs the published wheel from PyPI, never the
# source tree, and builds no tools from source.
#
# The pin below tracks the package version through .bumpversion.cfg.
#
#   docker build --file docker/Dockerfile --target mcp -t webarchiver:<version>-mcp .
FROM python:3.14-slim@sha256:a2b82f3c48559aa0a8446d9af49826b6e2b2016f4cd2afabfe6013ec53729170 AS mcp
ARG HOST=127.0.0.1
ARG PORT=8000
ARG TRANSPORT="stdio"
ARG AUTH_TYPE="none"
ENV HOST=${HOST} \
    PORT=${PORT} \
    TRANSPORT=${TRANSPORT} \
    AUTH_TYPE=${AUTH_TYPE} \
    PYTHONUNBUFFERED=1 \
    PIP_NO_CACHE_DIR=1 \
    PIP_DISABLE_PIP_VERSION_CHECK=1 \
    PLAYWRIGHT_BROWSERS_PATH=/opt/ms-playwright
# The render and screenshot operations drive Playwright's prebuilt Chromium
# (downloaded, not compiled) with its system libraries.
RUN pip install --only-binary :all: webarchiver[mcp]==1.2.0 \
    && playwright install --with-deps --only-shell chromium \
    && rm -rf /var/lib/apt/lists/* \
    && chmod -R a+rX /opt/ms-playwright \
    && useradd --create-home --uid 10001 --shell /usr/sbin/nologin mcp
USER 10001
CMD ["webarchiver-mcp"]

FROM mcp AS default
