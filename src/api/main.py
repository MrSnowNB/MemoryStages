"""
Stage 1 Implementation - SQLite Foundation Only
DO NOT IMPLEMENT BEYOND STAGE 1 SCOPE
"""

from fastapi import FastAPI, HTTPException, Depends, Body
from fastapi.responses import JSONResponse
from fastapi.middleware.cors import CORSMiddleware
from typing import List, Dict, Any
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
    DebugResponse,
    SearchResult,
    SearchResponse,
    # Stage 4: Approval workflow schemas
    ApprovalCreateRequest,
    ApprovalResponse,
    ApprovalStatus,
    ApprovalDecisionRequest,
    ApprovalListResponse
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
from ..core.approval import (
    create_approval_request,
    get_approval_status,
    approve_request,
    reject_request,
    list_pending_requests
)
from ..core.db import health_check
from ..core.config import VERSION, debug_enabled, SEARCH_API_ENABLED, CHAT_API_ENABLED

# Conditionally import chat router (feature-flagged)
if CHAT_API_ENABLED:
    try:
        from .chat import router as chat_router
        CHAT_ROUTER_AVAILABLE = True
    except ImportError:
        CHAT_ROUTER_AVAILABLE = False
else:
    CHAT_ROUTER_AVAILABLE = False

from ..core.search_service import semantic_search

# Initialize the FastAPI application
app = FastAPI(
    title="Memory Scaffold API",
    version=VERSION,
    description="Local-first multi-agent memory scaffold with SQLite backend",
    docs_url="/docs" if debug_enabled() else None,
    redoc_url="/redoc" if debug_enabled() else None
)

# Add CORS middleware to allow frontend connections
app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:3000"],  # Allow web UI
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
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
def set_key_endpoint(request_data: Dict[str, Any] = Body(...)):
    """Set a key-value pair."""
    from ..core.config import SCHEMA_VALIDATION_STRICT

    # Conditionally validate request based on flag
    if SCHEMA_VALIDATION_STRICT:
        # Strict validation mode - use Pydantic model
        try:
            request = KVSetRequest(**request_data)
        except Exception as e:
            raise HTTPException(status_code=422, detail=str(e))

        # Extract values from validated request
        key = request.key
        value = request.value
        source = request.source
        casing = request.casing
        sensitive = request.sensitive
    else:
        # Loose validation mode - accept any data, let DAO handle validation
        key = request_data.get('key', '')
        value = request_data.get('value', '')
        source = request_data.get('source', 'api')
        casing = request_data.get('casing', 'preserve')
        sensitive = request_data.get('sensitive', False)

    # Add an episodic event for this operation
    add_event(
        actor="api",
        action="set_key",
        payload=f"Setting key {key}"
    )

    try:
        result = set_key(
            key=key,
            value=value,
            source=source,
            casing=casing,
            sensitive=sensitive
        )

        # Check if DAO returned an Exception (error case)
        if isinstance(result, Exception):
            success = False
            logging.error(f"Database error during set_key operation: {result}")
        else:
            success = result

    except Exception as e:
        # Fallback for any unexpected exceptions
        success = False
        logging.error(f"Unexpected error during set_key operation: {e}")

    return KVResponse(success=success, key=key)

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

@app.get("/search", response_model=SearchResponse)
def search_endpoint(query: str = "", k: int = 5):
    """Search knowledge base using semantic similarity (BETA feature)."""
    if not SEARCH_API_ENABLED:
        raise HTTPException(status_code=404, detail="Search endpoint disabled")

    results = semantic_search(query=query, top_k=k)

    # Convert dict results to SearchResult models
    search_results = [
        SearchResult(**result) for result in results
    ]

    return SearchResponse(results=search_results)


# Stage 4: Approval workflow endpoints
@app.post("/approval/request", response_model=ApprovalResponse)
def create_approval_request_endpoint(request: ApprovalCreateRequest):
    """Create a new approval request (feature-flagged)."""
    approval_req = create_approval_request(
        type=request.type,
        payload=request.payload,
        requester=request.requester
    )

    if not approval_req:
        raise HTTPException(status_code=403, detail="Approval system disabled")

    return ApprovalResponse(
        success=True,
        request_id=approval_req.id,
        message="Approval request created"
    )

@app.get("/approval/{request_id}", response_model=ApprovalStatus)
def get_approval_status_endpoint(request_id: str):
    """Get approval request status."""
    request = get_approval_status(request_id)
    if not request:
        raise HTTPException(status_code=404, detail="Approval request not found")

    return ApprovalStatus(
        id=request.id,
        type=request.type,
        payload=request.payload,
        requester=request.requester,
        status=request.status,
        created_at=request.created_at,
        expires_at=request.expires_at
    )

@app.post("/approval/{request_id}/approve")
def approve_approval_request_endpoint(request_id: str, decision: ApprovalDecisionRequest):
    """Approve an approval request (manual mode)."""
    success = approve_request(
        request_id=request_id,
        approver=decision.approver,
        reason=decision.reason
    )

    if not success:
        raise HTTPException(status_code=404, detail="Approval request not found or cannot be approved")

    # Log the approval event
    add_event(
        actor=decision.approver,
        action="approval_granted",
        payload=f"Approved request {request_id}: {decision.reason}"
    )

    return {"success": True, "message": "Request approved", "request_id": request_id}

@app.post("/approval/{request_id}/reject")
def reject_approval_request_endpoint(request_id: str, decision: ApprovalDecisionRequest):
    """Reject an approval request (manual mode)."""
    success = reject_request(
        request_id=request_id,
        approver=decision.approver,
        reason=decision.reason
    )

    if not success:
        raise HTTPException(status_code=404, detail="Approval request not found or cannot be rejected")

    # Log the rejection event
    add_event(
        actor=decision.approver,
        action="approval_denied",
        payload=f"Rejected request {request_id}: {decision.reason}"
    )

    return {"success": True, "message": "Request rejected", "request_id": request_id}

@app.get("/approval/pending", response_model=ApprovalListResponse)
def list_pending_approvals_endpoint():
    """List pending approval requests (debug mode)."""
    if not debug_enabled():
        raise HTTPException(status_code=403, detail="Approval debug endpoint requires debug mode")

    pending_requests = list_pending_requests()

    requests_list = []
    for req in pending_requests:
        requests_list.append(ApprovalStatus(
            id=req.id,
            type=req.type,
            payload=req.payload,
            requester=req.requester,
            status=req.status,
            created_at=req.created_at,
            expires_at=req.expires_at
        ))

    return ApprovalListResponse(pending_requests=requests_list)


# Stage 7: Chat API endpoints (feature-flagged)
if CHAT_ROUTER_AVAILABLE:
    app.include_router(
        chat_router,
        prefix="/chat",
        tags=["chat"]
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
