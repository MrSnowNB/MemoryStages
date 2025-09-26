"""
Stage 2 scope only. Do not implement beyond this file's responsibilities.
Vector memory overlay - non-canonical, advisory layer over SQLite canonical truth.
"""

# Package initialization for vector module
from .index import IVectorStore, SimpleInMemoryVectorStore
from .types import VectorRecord, QueryResult

__all__ = [
    'IVectorStore', 
    'SimpleInMemoryVectorStore',
    'VectorRecord', 
    'QueryResult'
]
