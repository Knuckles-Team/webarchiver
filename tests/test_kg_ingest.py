"""Contract checks for source mapping; no engine or service connection."""

import asyncio
from types import SimpleNamespace

import pytest

from webarchiver import kg_ingest


class FakeIngest:
    def __init__(self):
        self.calls = []

    async def submit(self, binding, changes):
        self.calls.append((binding, changes))
        return SimpleNamespace(affected_count=1, relationship_count=0)


def test_ingest_maps_record_and_uses_submit():
    fake = FakeIngest()
    assert asyncio.run(
        kg_ingest.ingest_records([{"id": 0, "name": "first"}], ingest=fake)
    ) == {"nodes": 1, "edges": 0}
    binding, changes = fake.calls[0]
    assert binding.connector
    assert changes.entities[0].id == "0"
    assert changes.entities[0].properties == {"name": "first"}
    assert changes.withdrawals == ()


def test_missing_identity_fails_before_submit():
    fake = FakeIngest()
    with pytest.raises(ValueError, match="stable id"):
        asyncio.run(kg_ingest.ingest_records([{"name": "missing"}], ingest=fake))
    assert not fake.calls


def test_documents_and_media_use_typed_changes():
    fake = FakeIngest()
    asyncio.run(
        kg_ingest.ingest_documents([{"id": "doc", "text": "content"}], ingest=fake)
    )
    asyncio.run(kg_ingest.ingest_blob(b"content", mime_type="text/plain", ingest=fake))
    assert fake.calls[0][1].documents[0].text == "content"
    assert fake.calls[1][1].media[0].data == b"content"


def test_submit_failure_propagates():
    class RejectedIngest:
        async def submit(self, binding, changes):
            raise RuntimeError("rejected source")

    with pytest.raises(RuntimeError, match="rejected source"):
        asyncio.run(kg_ingest.ingest_records([{"id": "one"}], ingest=RejectedIngest()))
