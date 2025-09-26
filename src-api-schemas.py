"""Pydantic schemas for API request/response validation."""

from typing import Optional, List, Dict, Any
from pydantic import BaseModel, Field
from datetime import datetime

class KVSetRequest(BaseModel):
    """Request schema for setting a KV pair."""
    key: str = Field(..., description="Key name", min_length=1, max_length=255)
    value: str = Field(..., description="Value to store")
    source: Optional[str] = Field("user", description="Source of the data")
    sensitive: Optional[bool] = Field(False, description="Mark as sensitive data")

class KVResponse(BaseModel):
    """Response schema for KV operations."""
    key: str
    value: str
    updated_at: str

class KVGetResponse(BaseModel):
    """Response schema for getting a single KV pair."""
    key: str
    value: str
    updated_at: str
    source: str
    sensitive: bool

class KVListItem(BaseModel):
    """Schema for KV list items."""
    key: str
    value: str
    updated_at: str
    sensitive: bool

class KVListResponse(BaseModel):
    """Response schema for listing KV pairs."""
    items: List[KVListItem]
    count: int

class EpisodicRequest(BaseModel):
    """Request schema for adding episodic events."""
    actor: str = Field(..., description="Who performed the action")
    action: str = Field(..., description="What action was performed")
    payload: Dict[str, Any] = Field(..., description="Action payload data")

class EpisodicResponse(BaseModel):
    """Response schema for episodic operations."""
    id: int
    ts: str

class EpisodicEvent(BaseModel):
    """Schema for episodic event items."""
    id: int
    ts: str
    actor: str
    action: str
    payload: str  # JSON string

class EpisodicListResponse(BaseModel):
    """Response schema for listing episodic events."""
    events: List[EpisodicEvent]
    count: int

class HealthResponse(BaseModel):
    """Response schema for health check."""
    status: str
    version: str
    db_ok: bool
    kv_count: int
    timestamp: str

class DebugResponse(BaseModel):
    """Response schema for debug endpoint."""
    recent_events: List[EpisodicEvent]
    debug_enabled: bool