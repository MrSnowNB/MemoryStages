"""
Stage 3 enhanced embeddings. Semantic recall with sentence-transformers.
Non-canonical, advisory layer over SQLite canonical truth.
"""

from abc import ABC, abstractmethod
import hashlib
import json
import numpy as np
from sentence_transformers import SentenceTransformer

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

class SentenceTransformerEmbedding(IEmbeddingProvider):
    """Sentence transformers embedding provider using pre-trained models.

    Uses the all-mpnet-base-v2 model for high-quality semantic embeddings.
    """

    def __init__(self, model_name: str = "all-mpnet-base-v2"):
        self.model_name = model_name
        self._model = None
        self._dimension = None

    @property
    def model(self):
        if self._model is None:
            self._model = SentenceTransformer(self.model_name)
        return self._model

    def embed_text(self, text: str) -> list[float]:
        """Generate embedding vector using sentence transformers."""
        embedding = self.model.encode(text, convert_to_tensor=False)
        return embedding.tolist()

    def get_dimension(self) -> int:
        """Get the dimension of the embedding vectors."""
        if self._dimension is None:
            # Get dimension by encoding a dummy string
            dummy_embedding = self.model.encode("test", convert_to_tensor=False)
            self._dimension = len(dummy_embedding)
        return self._dimension


class EmbeddingsService:
    """
    Stage 2 Embeddings Service using sentence-transformers.
    Provides batch embedding and versioning for semantic memory indexing.
    """

    def __init__(self, model_name: str = None):
        """
        Initialize the embeddings service.

        Args:
            model_name: Model name to use, defaults to config setting
        """
        from ..core.config import EMBED_MODEL_NAME
        self.model_name = model_name or EMBED_MODEL_NAME
        self._provider = None

    @property
    def provider(self):
        """Lazy-loaded embedding provider."""
        if self._provider is None:
            self._provider = SentenceTransformerEmbedding(self.model_name)
        return self._provider

    def embed_texts(self, texts: list[str]) -> np.ndarray:
        """
        Embed multiple texts into vectors.

        Args:
            texts: List of text strings to embed

        Returns:
            Numpy array of shape (len(texts), embedding_dim)
        """
        embeddings = []
        for text in texts:
            embedding = self.provider.embed_text(text)
            embeddings.append(embedding)
        return np.array(embeddings)

    def get_version(self) -> str:
        """Get the embedding model version for audit consistency."""
        from ..core.config import EMBEDDING_MODEL_VERSION
        return EMBEDDING_MODEL_VERSION
