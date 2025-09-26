"""
Stage 1 Implementation - SQLite Foundation Only
DO NOT IMPLEMENT BEYOND STAGE 1 SCOPE
"""

import os
from pathlib import Path

# Database path configuration
DB_PATH = os.getenv("DB_PATH", "./data/memory.db")

# Debug flag is now a function to be dynamic

# Vector system configuration (Stage 2 - default disabled)
VECTOR_PROVIDER = os.getenv("VECTOR_PROVIDER", "memory")  # memory|faiss
EMBED_PROVIDER = os.getenv("EMBED_PROVIDER", "hash")  # hash|custom
SEARCH_API_ENABLED = os.getenv("SEARCH_API_ENABLED", "false").lower() == "true"

# Version string
VERSION = "1.0.0-stage1"

def get_vector_store():
    """Get configured vector store implementation. Returns None if vector features disabled."""
    if not are_vector_features_enabled():
        return None

    if VECTOR_PROVIDER == "memory":
        from src.vector.index import SimpleInMemoryVectorStore
        return SimpleInMemoryVectorStore()
    elif VECTOR_PROVIDER == "faiss":
        try:
            from src.vector.faiss_store import FaissVectorStore
            return FaissVectorStore()
        except ImportError:
            # Gracefully degrade to memory store if FAISS not available
            from src.vector.index import SimpleInMemoryVectorStore
            return SimpleInMemoryVectorStore()
    else:
        # Default to memory store for unknown providers
        from src.vector.index import SimpleInMemoryVectorStore
        return SimpleInMemoryVectorStore()


def get_embedding_provider():
    """Get configured embedding provider implementation. Returns None if vector features disabled."""
    if not are_vector_features_enabled():
        return None

    if EMBED_PROVIDER == "hash":
        from src.vector.embeddings import DeterministicHashEmbedding
        return DeterministicHashEmbedding()
    elif EMBED_PROVIDER == "custom":
        # TODO: Implement custom embedding provider in future slice
        from src.vector.embeddings import DeterministicHashEmbedding
        return DeterministicHashEmbedding()
    else:
        from src.vector.embeddings import DeterministicHashEmbedding
        return DeterministicHashEmbedding()


def are_vector_features_enabled():
    """Check if vector features are enabled."""
    return os.getenv("VECTOR_ENABLED", "false").lower() == "true"


def debug_enabled():
    """Check if debug mode is enabled."""
    return os.getenv("DEBUG", "true").lower() == "true"


def ensure_db_directory():
    """Ensure the database directory exists."""
    Path(DB_PATH).parent.mkdir(parents=True, exist_ok=True)
