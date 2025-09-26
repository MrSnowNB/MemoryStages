"""
Stage 1 Implementation - SQLite Foundation Only
DO NOT IMPLEMENT BEYOND STAGE 1 SCOPE
"""

from fastapi import FastAPI, HTTPException, Depends
from fastapi.responses import JSONResponse
from typing import List
import logging
from datetime import datetime

from .schemas import (
    KVSetRequest, 
    KVResponse, 
    KVGetResponse, 
    KVListResponse,
    EpisodicRequest,
    EpisodicResponse,
    EpisodicListResponse,
    HealthResponse,
    DebugResponse
)
from ..core.dao import (
    get_key, 
    set_key, 
    list_keys, 
    delete_key,
    add_event,
    list_events,
    get_kv_count
)
from ..core.db import health_check
from ..core.config import VERSION, debug_enabled

# Initialize the FastAPI application
app = FastAPI(
    title="Memory Scaffold API",
    version=VERSION,
    description="Local-first multi-agent memory scaffold with SQLite backend",
    docs_url="/docs" if debug_enabled() else None,
    redoc_url="/redoc" if debug_enabled() else None
)

@app.get("/health", response_model=HealthResponse)
def health_check_endpoint():
    """Check system health."""
    db_health = health_check()
    kv_count = get_kv_count()
    
    return HealthResponse(
        status="healthy" if db_health else "unhealthy",
        version=VERSION,
        db_health=db_health,
        kv_count=kv_count
    )

@app.put("/kv", response_model=KVResponse)
def set_key_endpoint(request: KVSetRequest):
    """Set a key-value pair."""
    # Add an episodic event for this operation
    add_event(
        actor="api",
        action="set_key",
        payload=f"Setting key {request.key}"
    )
    
    success = set_key(
        key=request.key,
        value=request.value,
        source=request.source,
        casing=request.casing,
        sensitive=request.sensitive
    )
    
    return KVResponse(success=success, key=request.key)

@app.get("/kv/{key}", response_model=KVGetResponse)
def get_key_endpoint(key: str):
    """Get a single key-value pair."""
    kv_pair = get_key(key)
    if not kv_pair:
        raise HTTPException(status_code=404, detail="Key not found")
    
    return KVGetResponse(
        key=kv_pair.key,
        value=kv_pair.value,
        casing=kv_pair.casing,
        source=kv_pair.source,
        updated_at=kv_pair.updated_at,
        sensitive=kv_pair.sensitive
    )

@app.get("/kv/list", response_model=KVListResponse)
def list_keys_endpoint():
    """List all non-tombstone key-value pairs."""
    kv_pairs = list_keys()
    
    # Convert to the response format
    keys = [
        KVGetResponse(
            key=pair.key,
            value=pair.value,
            casing=pair.casing,
            source=pair.source,
            updated_at=pair.updated_at,
            sensitive=pair.sensitive
        )
        for pair in kv_pairs
    ]
    
    return KVListResponse(keys=keys)

@app.post("/episodic", response_model=EpisodicResponse)
def add_episodic_event(request: EpisodicRequest):
    """Add a custom episodic event."""
    success = add_event(
        actor=request.actor,
        action=request.action,
        payload=request.payload
    )
    
    # Note: We don't have the ID of inserted record, so we'll return a generic response
    return EpisodicResponse(success=success, id=0)  # Placeholder

@app.get("/debug", response_model=DebugResponse)
def debug_endpoint():
    """Debug information (only available in DEBUG mode)."""
    if not debug_enabled():
        raise HTTPException(status_code=403, detail="Debug endpoint disabled")
    
    return DebugResponse(
        message="Debug endpoint active",
        timestamp=datetime.now()
    )

# Global exception handler is for Stage 1

@app.exception_handler(Exception)
async def global_exception_handler(request, exc):
    """Handle all unhandled exceptions."""
    logging.error(f"Unhandled exception: {exc}")
    content = {"detail": "Internal server error"}
    if debug_enabled():
        content["debug"] = str(exc)
    status_code = 500
    return JSONResponse(
        status_code=status_code,
        content=content,
    )
