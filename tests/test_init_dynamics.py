import importlib

import pytest


@pytest.mark.concept("CONN-WEBARCHIVER-001")
def test_package_imports():
    """Top-level package exposes its public API. CONCEPT:CONN-WEBARCHIVER-001"""
    module = importlib.import_module("webarchiver")
    assert hasattr(module, "__all__")
