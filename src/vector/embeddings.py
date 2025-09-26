"""
Stage 2 scope only. Do not implement beyond this file's responsibilities.
Vector memory overlay - non-canonical, advisory layer over SQLite canonical truth.
"""

from abc import ABC, abstractmethod
import hashlib
import json

class IEmbeddingProvider(ABC):
    """Abstract interface for embedding providers."""
    
    @abstractmethod
    def embed_text(self, text: str) -> list[float]:
        """Generate embedding vector for given text."""
        pass
    
    @abstractmethod
    def get_dimension(self) -> int:
        """Get the dimension of the embedding vectors."""  
        pass

class DeterministicHashEmbedding(IEmbeddingProvider):
    """Deterministic hash-based embedding provider for testing purposes.
    
    This implementation uses a consistent hashing approach to generate
    reproducible embeddings from text, which is useful for testing 
    without requiring external model dependencies.
    """
    
    def __init__(self, dimension: int = 384):
        self.dimension = dimension
    
    def embed_text(self, text: str) -> list[float]:
        """Generate deterministic embedding vector using hash function."""
        # Create a consistent hash of the input text
        hash_object = hashlib.md5(text.encode())
        hex_dig = hash_object.hexdigest()
        
        # Convert hex string to int values and normalize to 0-1 range
        vector = []
        for i in range(0, len(hex_dig), 8):
            if len(vector) >= self.dimension:
                break
                
            chunk = hex_dig[i:i+8]
            value = int(chunk, 16) % (2**32)
            
            # Normalize to [0, 1] and then map to [-1, 1] for cosine similarity
            normalized = (value / (2**32)) * 2 - 1
            vector.append(normalized)
        
        # If we don't have enough dimensions, pad with zeros
        while len(vector) < self.dimension:
            vector.append(0.0)
            
        return vector[:self.dimension]
    
    def get_dimension(self) -> int:
        """Get the dimension of the embedding vectors."""
        return self.dimension
