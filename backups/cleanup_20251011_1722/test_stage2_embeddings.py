#!/usr/bin/env python3
"""
Test Stage 2 Embeddings Service
"""

import numpy as np
from src.vector.embeddings import EmbeddingsService

def test_embeddings():
    """Test embeddings service basic functionality."""
    print("Testing EmbeddingsService...")

    # Initialize service
    service = EmbeddingsService()
    print(f"Model: {service.model_name}")

    # Test embed_texts
    texts = ["Hello world", "This is a test", "Semantic embeddings"]
    embeddings = service.embed_texts(texts)

    # Check shape
    print(f"Embeddings shape: {embeddings.shape}")
    assert embeddings.shape[0] == len(texts), "Wrong number of embeddings"
    assert embeddings.shape[1] > 0, "Wrong embedding dimension"

    # Check version
    version = service.get_version()
    print(f"Version: {version}")
    assert version, "Version should not be empty"

    # Test determinism (same text should give same embedding)
    embedding1 = service.embed_texts(["Hello world"])
    embedding2 = service.embed_texts(["Hello world"])
    np.testing.assert_array_equal(embedding1, embedding2, "Embeddings should be deterministic")

    print("✅ All embeddings tests passed")

if __name__ == "__main__":
    test_embeddings()
