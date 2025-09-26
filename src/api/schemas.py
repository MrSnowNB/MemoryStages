"""
Stage 1 Implementation - SQLite Foundation Only
DO NOT IMPLEMENT BEYOND STAGE 1 SCOPE
"""

from pydantic import BaseModel
from typing import Optional, List
from datetime import datetime

class KVSetRequest(BaseModel):
    key: str
    value: str
    source: str
    casing: str
    sensitive: bool = False

class KVResponse(BaseModel):
    success: bool
    key: str

class KVGetResponse(BaseModel):
    key: str
    value: str
    casing: str
    source: str
    updated_at: datetime
    sensitive: bool

class KVListResponse(BaseModel):
    keys: List[KVGetResponse]

class EpisodicRequest(BaseModel):
    actor: str
    action: str
    payload: str

class EpisodicResponse(BaseModel):
    success: bool
    id: int

class EpisodicListResponse(BaseModel):
    events: List[dict]  # Will be filled with actual event data in response

class HealthResponse(BaseModel):
    status: str
    version: str
    db_health: bool
    kv_count: int

class DebugResponse(BaseModel):
    message: str
    timestamp: datetime
