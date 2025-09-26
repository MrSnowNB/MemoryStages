"""FastAPI main application for bot-swarm memory system."""

import logging
from datetime import datetime
from typing import List

from fastapi import FastAPI, HTTPException, Depends
from fastapi.responses import JSONResponse

from ..core.config import config
from ..core.db import init_database, check_db_health
from ..core import dao
from .schemas import (
    KVSetRequest, KVResponse, KVGetResponse, KVListResponse, KVListItem,
    EpisodicRequest, EpisodicResponse, EpisodicListResponse, EpisodicEvent,
    HealthResponse, DebugResponse
)

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

# Initialize FastAPI app
app = FastAPI(
    title="Bot-Swarm Memory System",
    description="Stage 1: SQLite canonical memory with KV store and episodic logging",
    version=config.VERSION,
    docs_url="/docs" if config.DEBUG else None,
    redoc_url="/redoc" if config.DEBUG else None
)

@app.on_event("startup")
async def startup():
    """Initialize database on startup."""
    init_database()
    logger.info("Bot-swarm memory system started")

@app.get("/health", response_model=HealthResponse)
async def health_check():
    """Health check endpoint."""
    db_ok = check_db_health()
    kv_count = dao.get_kv_count() if db_ok else 0
    
    return HealthResponse(
        status="ok" if db_ok else "degraded",
        version=config.VERSION,
        db_ok=db_ok,
        kv_count=kv_count,
        timestamp=datetime.utcnow().isoformat()
    )

@app.get("/kv/{key}", response_model=KVGetResponse)
async def get_kv(key: str):
    """Get a specific KV pair."""
    result = dao.get_key(key)
    if not result:
        raise HTTPException(status_code=404, detail=f"Key '{key}' not found")
    
    # Redact sensitive values unless DEBUG mode
    value = result.value
    if result.sensitive and not config.DEBUG:
        value = "***REDACTED***"
    
    return KVGetResponse(
        key=result.key,
        value=value,
        updated_at=result.updated_at,
        source=result.source,
        sensitive=result.sensitive
    )

@app.put("/kv", response_model=KVResponse)
async def set_kv(request: KVSetRequest):
    """Set a KV pair."""
    try:
        # Validate source
        valid_sources = {'user', 'system', 'import', 'test'}
        if request.source not in valid_sources:
            raise HTTPException(
                status_code=400, 
                detail=f"Invalid source. Must be one of: {valid_sources}"
            )
        
        result = dao.set_key(
            key=request.key,
            value=request.value,
            source=request.source or 'user',
            casing=request.key,  # Preserve exact casing
            sensitive=int(request.sensitive or False)
        )
        
        return KVResponse(
            key=result['key'],
            value=result['value'],
            updated_at=result['updated_at']
        )
    except Exception as e:
        logger.error(f"Error setting KV: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/kv/list", response_model=KVListResponse)
async def list_kv():
    """List all KV pairs."""
    try:
        items = dao.list_keys()
        
        # Redact sensitive values unless DEBUG mode
        kv_items = []
        for item in items:
            value = item['value']
            if item['sensitive'] and not config.DEBUG:
                value = "***REDACTED***"
            
            # Skip tombstones (empty values)
            if value:
                kv_items.append(KVListItem(
                    key=item['key'],
                    value=value,
                    updated_at=item['updated_at'],
                    sensitive=item['sensitive']
                ))
        
        return KVListResponse(
            items=kv_items,
            count=len(kv_items)
        )
    except Exception as e:
        logger.error(f"Error listing KV: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@app.post("/episodic", response_model=EpisodicResponse)
async def add_episodic(request: EpisodicRequest):
    """Add an episodic event."""
    try:
        result = dao.add_event(
            actor=request.actor,
            action=request.action,
            payload=request.payload
        )
        
        return EpisodicResponse(
            id=result['id'],
            ts=result['ts']
        )
    except Exception as e:
        logger.error(f"Error adding episodic event: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/debug", response_model=DebugResponse)
async def debug_info():
    """Debug endpoint - only available in DEBUG mode."""
    if not config.DEBUG:
        raise HTTPException(status_code=403, detail="Debug mode disabled")
    
    try:
        events = dao.list_events(limit=20)
        
        return DebugResponse(
            recent_events=[
                EpisodicEvent(
                    id=event.id,
                    ts=event.ts,
                    actor=event.actor,
                    action=event.action,
                    payload=event.payload
                )
                for event in events
            ],
            debug_enabled=config.DEBUG
        )
    except Exception as e:
        logger.error(f"Error getting debug info: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@app.exception_handler(Exception)
async def global_exception_handler(request, exc):
    """Global exception handler for structured error responses."""
    logger.error(f"Unhandled exception: {exc}")
    return JSONResponse(
        status_code=500,
        content={"detail": "Internal server error", "debug": str(exc) if config.DEBUG else None}
    )