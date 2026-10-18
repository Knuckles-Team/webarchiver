from pathlib import Path

import pytest

CONCEPTS_DOC = Path(__file__).resolve().parents[1] / "docs" / "concepts.md"


@pytest.mark.concept("CONN-WEBARCHIVER-001")
def test_concepts_doc_exists():
    """Concept registry doc exists. CONCEPT:CONN-WEBARCHIVER-001"""
    assert CONCEPTS_DOC.is_file()


@pytest.mark.concept("CONN-WEBARCHIVER-001")
def test_prefix_registered():
    """Project concept prefix is registered. CONCEPT:CONN-WEBARCHIVER-001"""
    assert "CONCEPT:CONN-WEBARCHIVER-" in CONCEPTS_DOC.read_text(encoding="utf-8")
