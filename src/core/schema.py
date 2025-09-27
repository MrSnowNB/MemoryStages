"""
Stage 4 scope only. Do not implement beyond this file's responsibilities.
Approval workflows and schema validation - ensures data integrity and auditability.
"""

from dataclasses import dataclass
from datetime import datetime
from typing import Dict, List


@dataclass
class KVRecord:
    key: str
    value: str
    source: str
    casing: str
    sensitive: bool
    updated_at: datetime


@dataclass
class VectorRecord:
    id: str
    vector: List[float]
    metadata: Dict
    updated_at: datetime


@dataclass
class EpisodicEvent:
    id: int
    ts: datetime
    actor: str
    action: str
    payload: Dict


@dataclass
class CorrectionAction:
    type: str  # ADD_VECTOR, UPDATE_VECTOR, REMOVE_VECTOR
    key: str
    metadata: Dict
    timestamp: datetime
