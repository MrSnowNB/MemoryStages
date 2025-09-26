"""
Stage 2 scope only. Do not implement beyond this file's responsibilities.
Vector memory overlay - non-canonical, advisory layer over SQLite canonical truth.
"""

from typing import Dict, Optional
import numpy as np
from dataclasses import dataclass


@dataclass
class VectorRecord:
    """Represents a vector record with metadata."""
    
    id: str
    """Unique identifier for the vector record"""
    
    vector: Optional[np.ndarray]
    """The vector representation of the content"""
    
    metadata: Dict[str, object]
    """Additional metadata associated with the vector"""


@dataclass 
class QueryResult:
    """Represents a search result from vector store."""
    
    id: str
    """Identifier for the matching record"""
    
    score: float
    """Similarity score of the match (0-1)"""
    
    metadata: Dict[str, object]
    """Metadata associated with the matched record"""
