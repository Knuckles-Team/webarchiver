#!/usr/bin/python
"""Pydantic response models for Webarchiver API payloads."""

from typing import Any

from pydantic import BaseModel, Field


class SystemStatusResponse(BaseModel):
    """Response model for system status queries."""

    status: str | None = Field(default=None, description="Service status string.")
    raw: dict[str, Any] | None = Field(
        default=None, description="Raw response payload."
    )
