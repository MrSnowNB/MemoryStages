#!/usr/bin/env python3
"""
Test for Stage 2 config settings.
"""

import os
from src.core.config import SEMANTIC_ENABLED, EMBED_MODEL_NAME, EMBEDDING_MODEL_VERSION

def test_stage2_config():
    """Test that Stage 2 semantic config loads properly."""
    print(f"SEMANTIC_ENABLED: {SEMANTIC_ENABLED}")
    print(f"EMBED_MODEL_NAME: {EMBED_MODEL_NAME}")
    print(f"EMBEDDING_MODEL_VERSION: {EMBEDDING_MODEL_VERSION}")

    assert isinstance(SEMANTIC_ENABLED, bool)
    assert isinstance(EMBED_MODEL_NAME, str)
    assert isinstance(EMBEDDING_MODEL_VERSION, str)
    assert EMBED_MODEL_NAME  # Not empty
    assert EMBEDDING_MODEL_VERSION  # Not empty

    print("✅ All Stage 2 config tests passed")

if __name__ == "__main__":
    test_stage2_config()
