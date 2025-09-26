"""
Stage 2 scope only. Do not implement beyond this file's responsibilities.
Vector memory overlay - non-canonical, advisory layer over SQLite canonical truth.
"""

import pytest
import numpy as np
from src.vector.index import IVectorStore, SimpleInMemoryVectorStore
from src.vector.types import VectorRecord, QueryResult


def test_vector_store_interface():
    """Test that SimpleInMemoryVectorStore implements IVectorStore interface."""
    store = SimpleInMemoryVectorStore()
    
    # Check that it's an instance of the interface
    assert isinstance(store, IVectorStore)


def test_add_single_record():
    """Test adding a single vector record."""
    store = SimpleInMemoryVectorStore()
    
    record = VectorRecord(
        id="test_id",
        vector=np.array([1.0, 0.0, 0.0]),
        metadata={"key": "value"}
    )
    
    store.add(record)
    
    # Test that the record was stored
    results = store.search(np.array([1.0, 0.0, 0.0]), top_k=1)
    assert len(results) == 1
    assert results[0].id == "test_id"
    assert results[0].metadata["key"] == "value"


def test_batch_add_records():
    """Test adding multiple vector records."""
    store = SimpleInMemoryVectorStore()
    
    records = [
        VectorRecord(
            id="record_1",
            vector=np.array([1.0, 0.0, 0.0]),
            metadata={"key": "value1"}
        ),
        VectorRecord(
            id="record_2", 
            vector=np.array([0.0, 1.0, 0.0]),
            metadata={"key": "value2"}
        )
    ]
    
    store.batch_add(records)
    
    # Test that both records were stored
    results = store.search(np.array([1.0, 0.0, 0.0]), top_k=2)
    assert len(results) == 2
    result_ids = [r.id for r in results]
    assert "record_1" in result_ids
    assert "record_2" in result_ids


def test_search_similarity():
    """Test that search returns results ordered by similarity."""
    store = SimpleInMemoryVectorStore()
    
    # Add records with different vectors
    record_a = VectorRecord(
        id="a",
        vector=np.array([1.0, 0.0]),
        metadata={"text": "vector a"}
    )
    
    record_b = VectorRecord(
        id="b", 
        vector=np.array([0.0, 1.0]),
        metadata={"text": "vector b"}
    )
    
    store.add(record_a)
    store.add(record_b)
    
    # Search for first vector - should return a as most similar
    results = store.search(np.array([1.0, 0.0]), top_k=2)
    assert len(results) == 2
    assert results[0].id == "a"  # Most similar
    assert results[1].id == "b"  # Less similar


def test_delete_record():
    """Test deleting a vector record."""
    store = SimpleInMemoryVectorStore()
    
    record = VectorRecord(
        id="delete_test",
        vector=np.array([1.0, 0.0]),
        metadata={"key": "value"}
    )
    
    store.add(record)
    
    # Verify it exists
    results = store.search(np.array([1.0, 0.0]), top_k=1)
    assert len(results) == 1
    
    # Delete the record
    store.delete("delete_test")
    
    # Verify it's gone
    results = store.search(np.array([1.0, 0.0]), top_k=1)
    assert len(results) == 0


def test_clear_store():
    """Test clearing all records from the store."""
    store = SimpleInMemoryVectorStore()
    
    record = VectorRecord(
        id="clear_test",
        vector=np.array([1.0, 0.0]),
        metadata={"key": "value"}
    )
    
    store.add(record)
    
    # Verify it exists
    results = store.search(np.array([1.0, 0.0]), top_k=1)
    assert len(results) == 1
    
    # Clear the store
    store.clear()
    
    # Verify it's gone
    results = store.search(np.array([1.0, 0.0]), top_k=1)
    assert len(results) == 0


def test_tombstone_awareness():
    """Test that tombstoned entries are handled properly."""
    store = SimpleInMemoryVectorStore()
    
    # Add a record
    record = VectorRecord(
        id="tombstone_test",
        vector=np.array([1.0, 0.0]),
        metadata={"key": "value"}
    )
    
    store.add(record)
    
    # Search should find it  
    results = store.search(np.array([1.0, 0.0]), top_k=1)
    assert len(results) == 1
    
    # Add a new record with same ID but different vector (simulate update)
    updated_record = VectorRecord(
        id="tombstone_test",
        vector=np.array([0.0, 1.0]),
        metadata={"key": "updated_value"}
    )
    
    store.add(updated_record)
    
    # Search should find the updated record
    results = store.search(np.array([0.0, 1.0]), top_k=1)
    assert len(results) == 1
    assert results[0].metadata["key"] == "updated_value"


def test_empty_search():
    """Test searching an empty store."""
    store = SimpleInMemoryVectorStore()
    
    # Should not crash on empty search
    results = store.search(np.array([1.0, 0.0]), top_k=5)
    assert len(results) == 0


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
