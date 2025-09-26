"""
Stage 2 scope only. Do not implement beyond this file's responsibilities.
Vector memory overlay - non-canonical, advisory layer over SQLite canonical truth.
"""

from abc import ABC
from typing import List, Optional
import numpy as np

# Import VectorRecord and QueryResult from types module
from .types import VectorRecord, QueryResult
from .index import IVectorStore


class FaissVectorStore(IVectorStore, ABC):
    """FAISS-backed implementation of IVectorStore."""
    
    def __init__(self, dimension: int = 384):
        """
        Initialize FAISS vector store.
        
        Args:
            dimension: Dimension of the vectors (default: 384 for hash embeddings)
        """
        try:
            import faiss
            self.faiss = faiss
            self.dimension = dimension
            
            # Create a flat index (inner product metric for cosine similarity)
            self.index = faiss.IndexFlatIP(dimension)
            
            # Keep track of record IDs and their corresponding vector indices 
            self.id_to_vector_index = {}
            self.vector_id_map = {}  # Vector index -> record ID
            self.next_vector_index = 0
            
        except ImportError:
            raise ImportError("FAISS not installed. Please install faiss-cpu package.")
    
    def add(self, record: VectorRecord) -> None:
        """Add a single vector record to the FAISS store."""
        if record.vector is None or len(record.vector) == 0:
            return
            
        # Check dimension match and normalize vector for cosine similarity
        if len(record.vector) != self.dimension:
            raise ValueError(f"Vector dimension {len(record.vector)} does not match expected dimension {self.dimension}")
            
        norm = np.linalg.norm(record.vector)
        if norm == 0:  # Handle zero vectors to prevent division by zero
            return
            
        normalized_vector = record.vector / norm
        
        # Convert to numpy array of correct dtype (float32 for FAISS)
        vector_array = np.array(normalized_vector, dtype=np.float32)
        
        # Add to FAISS index  
        self.index.add(vector_array.reshape(1, -1))
        
        # Store mapping from ID to vector index
        self.id_to_vector_index[record.id] = self.next_vector_index
        self.vector_id_map[self.next_vector_index] = record.id
        self.next_vector_index += 1
    
    def batch_add(self, records: List[VectorRecord]) -> None:
        """Add multiple vector records to the FAISS store."""
        if not records:
            return
            
        # Prepare all vectors for batch addition  
        vectors_to_add = []
        valid_records = []
        
        for record in records:
            if record.vector is not None and len(record.vector) > 0:
                # Check dimension match and normalize vector for cosine similarity
                if len(record.vector) != self.dimension:
                    raise ValueError(f"Vector dimension {len(record.vector)} does not match expected dimension {self.dimension}")
                
                norm = np.linalg.norm(record.vector)
                if norm == 0:  # Handle zero vectors to prevent division by zero
                    continue
                
                normalized_vector = record.vector / norm
                vector_array = np.array(normalized_vector, dtype=np.float32)
                vectors_to_add.append(vector_array)
                valid_records.append(record)
        
        if not vectors_to_add:
            return
            
        # Convert to numpy array of correct shape and dtype
        batch_vectors = np.vstack(vectors_to_add).astype(np.float32)
        
        # Add to FAISS index 
        self.index.add(batch_vectors)
        
        # Store mappings for each record
        for i, record in enumerate(valid_records):
            self.id_to_vector_index[record.id] = self.next_vector_index + i
            self.vector_id_map[self.next_vector_index + i] = record.id
            
        self.next_vector_index += len(vectors_to_add)
    
    def search(self, query_vector: np.ndarray, top_k: int = 5) -> List[QueryResult]:
        """Search for similar vectors and return ranked results."""
        if not self.index.ntotal:
            return []
            
        # Normalize the query vector
        norm = np.linalg.norm(query_vector)
        if norm == 0:
            return []
            
        normalized_query = query_vector / norm
        
        # Convert to numpy array of correct dtype (float32 for FAISS)  
        query_array = np.array(normalized_query, dtype=np.float32).reshape(1, -1)
        
        # Perform search
        scores, indices = self.index.search(query_array, min(top_k, self.index.ntotal))
        
        # Convert results to QueryResult objects
        query_results = []
        for i in range(len(indices[0])):
            vector_index = indices[0][i]
            if vector_index in self.vector_id_map:
                record_id = self.vector_id_map[vector_index]
                score = scores[0][i]  # FAISS returns inner product (cosine similarity)
                
                # For now, we'll just return the ID since we don't have metadata stored
                # In a full implementation, this would need to retrieve original metadata 
                result = QueryResult(
                    id=record_id,
                    score=float(score),
                    metadata={}  # This would be filled in a more complete implementation
                )
                query_results.append(result)
                
        return query_results
    
    def delete(self, record_id: str) -> None:
        """Delete a vector record by ID - note: FAISS doesn't support true deletion.
        
        For simplicity and to maintain the interface contract with IVectorStore,
        we'll raise an exception when trying to delete from FAISS store.
        
        In a production implementation, this would require rebuilding the index
        or using FAISS's more complex deletion mechanisms.
        """
        # Since FAISS doesn't support efficient deletions, we cannot implement this properly here.
        # This is a limitation of the current approach - in practice you'd need to rebuild 
        # the entire index when deleting records.
        raise NotImplementedError("FAISS vector store does not support direct deletion. "
                                "Use rebuild utilities or memory store for deletion operations.")
    
    def clear(self) -> None:
        """Clear all records from the FAISS store."""
        # Create a new index with same parameters
        self.index = self.faiss.IndexFlatIP(self.dimension)
        self.id_to_vector_index.clear()
        self.vector_id_map.clear()
        self.next_vector_index = 0
