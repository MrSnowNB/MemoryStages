"""
Stage 2 scope only. Do not implement beyond this file's responsibilities.
Vector memory overlay - non-canonical, advisory layer over SQLite canonical truth.
"""

import pytest
from src.vector.embeddings import IEmbeddingProvider, DeterministicHashEmbedding

def test_embedding_interface():
    """Test that the embedding provider implements the interface correctly."""
    # Create an instance of our implementation
    embedder = DeterministicHashEmbedding(dimension=384)
    
    # Test that it's an instance of the abstract class
    assert isinstance(embedder, IEmbeddingProvider)
    
    # Test dimension retrieval
    assert embedder.get_dimension() == 384

def test_deterministic_embedding():
    """Test that the same input always produces the same output."""
    embedder = DeterministicHashEmbedding(dimension=384)
    
    # Test with a simple string
    text = "Hello, world!"
    vector1 = embedder.embed_text(text)
    vector2 = embedder.embed_text(text)
    
    # Should be identical
    assert vector1 == vector2
    
    # Should have correct dimension
    assert len(vector1) == 384

def test_different_inputs_produce_different_vectors():
    """Test that different inputs produce different vectors."""
    embedder = DeterministicHashEmbedding(dimension=384)
    
    vector1 = embedder.embed_text("Hello, world!")
    vector2 = embedder.embed_text("Goodbye, world!")
    
    # Should be different (though not guaranteed, very unlikely to be the same)
    assert vector1 != vector2

def test_consistent_output_across_runs():
    """Test that the same input produces consistent output across multiple runs."""
    # Create two separate instances
    embedder1 = DeterministicHashEmbedding(dimension=384)
    embedder2 = DeterministicHashEmbedding(dimension=384)
    
    text = "This is a test string"
    vector1 = embedder1.embed_text(text)
    vector2 = embedder2.embed_text(text)
    
    # Should be identical
    assert vector1 == vector2

def test_embedding_with_different_dimensions():
    """Test embedding with different dimension sizes."""
    # Test with smaller dimension
    small_embedder = DeterministicHashEmbedding(dimension=64)
    small_vector = small_embedder.embed_text("test")
    assert len(small_vector) == 64
    
    # Test with larger dimension  
    large_embedder = DeterministicHashEmbedding(dimension=512)
    large_vector = large_embedder.embed_text("test")
    assert len(large_vector) == 512

def test_embedding_edge_cases():
    """Test embedding with edge cases."""
    embedder = DeterministicHashEmbedding(dimension=384)
    
    # Test empty string
    empty_vector = embedder.embed_text("")
    assert len(empty_vector) == 384
    
    # Test very long string
    long_string = "A" * 1000
    long_vector = embedder.embed_text(long_string)
    assert len(long_vector) == 384
    
    # Test special characters
    special_vector = embedder.embed_text("Hello\n\t\rWorld!@#$%^&*()")
    assert len(special_vector) == 384

if __name__ == "__main__":
    pytest.main([__file__, "-v"])
