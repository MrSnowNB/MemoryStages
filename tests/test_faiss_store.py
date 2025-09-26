"""
Test cases for FaissVectorStore implementation.
"""

import pytest
import numpy as np
from src.vector import FaissVectorStore, VectorRecord


def test_faiss_store_initialization():
    """Test that FaissVectorStore can be initialized correctly."""
    store = FaissVectorStore(dimension=384)
    
    assert store is not None
    assert hasattr(store, 'index')
    assert hasattr(store, 'dimension')
    

def test_faiss_store_add_single_record():
    """Test adding a single vector record to the FAISS store."""
    store = FaissVectorStore(dimension=384)
    
    # Create a simple vector record
    record = VectorRecord(
        id="test_id_1",
        vector=np.array([0.5, 0.5, 0.5, 0.5], dtype=np.float32),  # 4D vector for testing
        metadata={"test": "data"}
    )
    
    store.add(record)
    
    # Should have added the record  
    assert len(store.id_to_vector_index) == 1
    assert "test_id_1" in store.id_to_vector_index


def test_faiss_store_add_multiple_records():
    """Test adding multiple vector records to the FAISS store."""
    store = FaissVectorStore(dimension=384)
    
    # Create multiple vector records  
    records = [
        VectorRecord(
            id=f"test_id_{i}",
            vector=np.array([float(i)] * 4, dtype=np.float32),
            metadata={"index": i}
        ) for i in range(5)
    ]
    
    store.batch_add(records)
    
    # Should have added all records
    assert len(store.id_to_vector_index) == 5
    
    for i in range(5):
        assert f"test_id_{i}" in store.id_to_vector_index


def test_faiss_store_search():
    """Test searching for similar vectors."""
    store = FaissVectorStore(dimension=384)
    
    # Add some records
    records = [
        VectorRecord(
            id="record_1",
            vector=np.array([1.0, 0.0, 0.0], dtype=np.float32),
            metadata={}
        ),
        VectorRecord(
            id="record_2", 
            vector=np.array([0.0, 1.0, 0.0], dtype=np.float32),
            metadata={}
        )
    ]
    
    store.batch_add(records)
    
    # Search with a query vector similar to record_1
    query_vector = np.array([1.0, 0.0, 0.0], dtype=np.float32)
    results = store.search(query_vector, top_k=2)
    
    assert len(results) >= 1
    assert any(result.id == "record_1" for result in results)


def test_faiss_store_clear():
    """Test clearing all records from the FAISS store."""
    store = FaissVectorStore(dimension=384)
    
    # Add some records
    record = VectorRecord(
        id="test_id",
        vector=np.array([0.5, 0.5, 0.5], dtype=np.float32),
        metadata={}
    )
    
    store.add(record)
    
    # Should have a record
    assert len(store.id_to_vector_index) == 1
    
    # Clear the store
    store.clear()
    
    # Should be empty now
    assert len(store.id_to_vector_index) == 0


def test_faiss_store_delete_not_implemented():
    """Test that delete operation raises NotImplementedError."""
    store = FaissVectorStore(dimension=384)
    
    with pytest.raises(NotImplementedError):
        store.delete("nonexistent_id")


def test_faiss_store_empty_search():
    """Test searching when the store is empty."""
    store = FaissVectorStore(dimension=384)
    
    # Search with an empty store
    query_vector = np.array([1.0, 0.0, 0.0], dtype=np.float32)
    results = store.search(query_vector, top_k=5)
    
    assert len(results) == 0


if __name__ == "__main__":
    # Run the tests directly if needed
    test_faiss_store_initialization()
    test_faiss_store_add_single_record()  
    test_faiss_store_add_multiple_records()
    test_faiss_store_search()
    test_faiss_store_clear()
    test_faiss_store_delete_not_implemented()
    test_faiss_store_empty_search()
    
    print("All FaissVectorStore tests passed!")
