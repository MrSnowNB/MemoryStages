"""
Stage 2 scope only. Do not implement beyond this file's responsibilities.
Vector memory overlay - non-canonical, advisory layer over SQLite canonical truth.
"""

from abc import ABC, abstractmethod
from typing import List, Optional
import numpy as np

# Import VectorRecord and QueryResult from types module
from .types import VectorRecord, QueryResult


class IVectorStore(ABC):
    """Abstract interface for vector storage operations."""
    
    @abstractmethod
    def add(self, record: VectorRecord) -> None:
        """Add a single vector record to the store."""
        pass
    
    @abstractmethod
    def batch_add(self, records: List[VectorRecord]) -> None:
        """Add multiple vector records to the store."""
        pass
    
    @abstractmethod
    def search(self, query_vector: np.ndarray, top_k: int = 5) -> List[QueryResult]:
        """Search for similar vectors and return ranked results."""
        pass
    
    @abstractmethod
    def delete(self, record_id: str) -> None:
        """Delete a vector record by ID."""
        pass
    
    @abstractmethod  
    def clear(self) -> None:
        """Clear all records from the store."""
        pass


class SimpleInMemoryVectorStore(IVectorStore):
    """Simple in-memory implementation of IVectorStore using cosine similarity."""
    
    def __init__(self):
        self._vectors = {}  # record_id -> VectorRecord
        self._index = {}    # record_id -> normalized_vector (for fast lookup)
        
    def add(self, record: VectorRecord) -> None:
        """Add a single vector record to the store."""
        if record.id in self._vectors:
            # Update existing record
            self._vectors[record.id] = record
        else:
            # Add new record
            self._vectors[record.id] = record
            
        # Store normalized vector for similarity calculations 
        if record.vector is not None:
            norm = np.linalg.norm(record.vector)
            if norm > 0:
                self._index[record.id] = record.vector / norm
            else:
                self._index[record.id] = record.vector
    
    def batch_add(self, records: List[VectorRecord]) -> None:
        """Add multiple vector records to the store."""
        for record in records:
            self.add(record)
    
    def search(self, query_vector: np.ndarray, top_k: int = 5) -> List[QueryResult]:
        """Search for similar vectors and return ranked results."""
        if not self._index:
            return []
        
        # Normalize the query vector
        norm = np.linalg.norm(query_vector)
        if norm == 0:
            # Return empty results if query vector is zero
            return []
            
        normalized_query = query_vector / norm
        
        # Calculate cosine similarities
        similarities = {}
        for record_id, stored_vector in self._index.items():
            similarity = np.dot(normalized_query, stored_vector)
            similarities[record_id] = similarity
            
        # Sort by similarity (descending) and return top_k results  
        sorted_results = sorted(similarities.items(), key=lambda x: x[1], reverse=True)
        
        # Convert to QueryResult objects
        query_results = []
        for record_id, score in sorted_results[:top_k]:
            if record_id in self._vectors:
                original_record = self._vectors[record_id]
                result = QueryResult(
                    id=original_record.id,
                    score=score,
                    metadata=original_record.metadata
                )
                query_results.append(result)
                
        return query_results
    
    def delete(self, record_id: str) -> None:
        """Delete a vector record by ID."""
        if record_id in self._vectors:
            del self._vectors[record_id]
        if record_id in self._index:
            del self._index[record_id]
    
    def clear(self) -> None:
        """Clear all records from the store."""
        self._vectors.clear()
        self._index.clear()
