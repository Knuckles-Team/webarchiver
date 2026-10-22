"""Typed source observations for Webarchiver, submitted through the SDK.

The configured ingest service owns durable checkpoints and engine transport.
These helpers perform no work at import time; missing configuration and rejected
submissions propagate to the caller. Invoke only for authorized source reads.
"""

from __future__ import annotations

from typing import Any

from agent_connector_sdk.ingest import (
    ChangeSet,
    Document,
    Entity,
    IngestBinding,
    KnowledgeIngest,
    MediaAsset,
    current_ingest,
)

_BINDING = IngestBinding(connector="webarchiver-mcp", stream="webarchiver")


async def _submit(changes: ChangeSet, ingest: KnowledgeIngest | None) -> dict[str, int]:
    service = ingest if ingest is not None else current_ingest()
    receipt = await service.submit(_BINDING, changes)
    return {"nodes": receipt.affected_count, "edges": receipt.relationship_count}


async def ingest_records(
    records: list[dict[str, Any]], *, ingest: KnowledgeIngest | None = None
) -> dict[str, int]:
    """Submit records as the starter manifest resource; adapt the mapping first."""
    entities = []
    for record in records:
        record_id = record.get("id")
        if record_id is None or not str(record_id).strip():
            raise ValueError("each source record needs a stable id")
        entities.append(
            Entity(
                id=str(record_id),
                node_type="WebarchiverResource",
                properties={
                    "name": record.get("name") or record.get("title") or str(record_id)
                },
            )
        )
    if not entities:
        raise ValueError("ingest_records needs at least one record")
    return await _submit(ChangeSet(entities=tuple(entities)), ingest)


async def ingest_documents(
    docs: list[dict[str, Any]], *, ingest: KnowledgeIngest | None = None
) -> dict[str, int]:
    """Submit text through SDK Document models, preserving the source identity."""
    if not docs:
        raise ValueError("ingest_documents needs at least one document")
    documents = tuple(
        Document(
            id=str(doc["id"]),
            text=doc["text"],
            title=doc.get("title"),
            source_uri=doc.get("source_uri"),
        )
        for doc in docs
    )
    return await _submit(ChangeSet(documents=documents), ingest)


async def ingest_blob(
    data: bytes,
    *,
    mime_type: str,
    name: str = "",
    ingest: KnowledgeIngest | None = None,
) -> dict[str, int]:
    """Submit media through SDK MediaAsset; storage belongs to the engine."""
    if not data or not mime_type.strip():
        raise ValueError("media requires non-empty bytes and a MIME type")
    return await _submit(
        ChangeSet(
            media=(
                MediaAsset(
                    data=data,
                    mime_type=mime_type,
                    name=name,
                ),
            )
        ),
        ingest,
    )
