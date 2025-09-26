"""
Stage 2 scope only. Do not implement beyond this file's responsibilities.
Vector memory overlay - non-canonical, advisory layer over SQLite canonical truth.
"""

# Package initialization for vector module
from .index import IVectorStore, SimpleInMemoryVectorStore
from .faiss_store import FaissVectorStore
from .types import VectorRecord, QueryResult

__all__ = [
    'IVectorStore', 
    'SimpleInMemoryVectorStore',
    'FaissVectorStore',
    'VectorRecord', 
    'QueryResult'
]
