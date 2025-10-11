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
    ApprovalListResponse,
    # Stage 2: Semantic Memory APIs
    SemanticIndexRequest,
    SemanticIndexResponse,
    SemanticQueryRequest,
    SemanticQueryResponse,
    SemanticHealthResponse,
    # Stage 3: Swarm Orchestration schemas
    SwarmMessageRequest,
    SwarmMessageResponse
)
from ..core.dao import (
    get_key,
    set_key,
    list_keys,
    delete_key,
    add_event,
    list_events,
    get_kv_count,
    DAO
)
from ..core.approval import (
    create_approval_request,
    get_approval_status,
    approve_request,
    reject_request,
    list_pending_requests
)
from ..core.db import health_check
from ..core.config import VERSION, debug_enabled, SEARCH_API_ENABLED, CHAT_API_ENABLED, get_vector_store, get_embedding_provider, are_vector_features_enabled

# Temporary debug log for CHAT_API_ENABLED
print(f"DEBUG: CHAT_API_ENABLED={CHAT_API_ENABLED}")

# Temporary debug log for CHAT_API_ENABLED

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
    allow_origins=["http://localhost:3000", "http://127.0.0.1:3000", "http://localhost:3001", "http://127.0.0.1:3001"],  # Allow web UI
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

# Define /kv/list endpoint BEFORE /kv/{key} to avoid path parameter conflict
@app.get("/kv/list", response_model=KVListResponse)
async def list_keys_endpoint(dao: DAO = Depends(DAO.dep)):
    items = await dao.list_keys()
    return KVListResponse(
        items=[
            KVGetResponse(
                key=i.key,
                value=i.value,
                casing=getattr(i, "casing", "preserve"),
                source=getattr(i, "source", "unknown"),
                updated_at=i.updated_at,
                sensitive=bool(getattr(i, "sensitive", False)),
            )
            for i in items
        ]
    )

@app.put("/kv", response_model=KVGetResponse)
async def put_kv(req: KVPutRequest, dao: DAO = Depends(DAO.dep)):
    import re
    if not re.match(r"^[A-Za-z][A-Za-z0-9_]*$", req.key):
        raise HTTPException(status_code=400, detail=f"Invalid key: {req.key}")

    await dao.set_key(
        key=req.key,
        value=req.value,
        source=req.source or "api",
        casing=req.casing or "preserve",
        sensitive=bool(req.sensitive),
    )

    rec = await dao.get_key(req.key)

    return KVGetResponse(
        key=rec.key, value=rec.value, casing=rec.casing, source=rec.source,
        updated_at=rec.updated_at, sensitive=rec.sensitive
    )

@app.get("/kv/{key}", response_model=KVGetResponse)
def get_key_endpoint(key: str, user_id: str = "default"):
    """Get a single key-value pair for a user."""
    kv_pair = get_key(user_id, key)
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

def _extract_user_id(request_data: Dict[str, Any] = None, headers: Dict[str, Any] = None) -> str:
    """Extract user_id from request data, headers, or default to 'default'.

    Priority order:
    1. request_data.get('user_id')
    2. headers.get('X-User-Id')
    3. 'default' (for backward compatibility)
    """
    if request_data and 'user_id' in request_data:
        return request_data['user_id'] or 'default'

    if headers and 'x-user-id' in headers:
        return headers['x-user-id'] or 'default'

    return 'default'

@app.post("/episodic", response_model=EpisodicResponse)
def add_episodic_event(request: EpisodicRequest, request_data: Dict[str, Any] = Body(...)):
    """Add a custom episodic event with user scoping."""
    # Extract user_id from request body or default
    user_id = _extract_user_id(request_data)

    success = add_event(
        user_id=user_id,
        actor=request.actor,
        action=request.action,
        payload=request.payload
    )

    # Note: We don't have the ID of inserted record, so we'll return a generic response
    return EpisodicResponse(success=success, id=0)  # Placeholder

@app.get("/debug/memory-insights", response_model=List[Dict[str, Any]])
def debug_memory_insights_endpoint(user_id: str = "default", limit: int = 20):
    """
    Educational endpoint: Get memory entries enriched with agent interaction history.
    Shows which agents processed each memory entry for teaching purposes.
    """
    if not debug_enabled():
        raise HTTPException(status_code=403, detail="Memory insights endpoint requires debug mode")

    try:
        from ..core import dao
        insights = dao.get_memory_insights(user_id, limit)
        return insights
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to get memory insights: {str(e)}")

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
        user_id="system",
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
        user_id="system",
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


# Stage 4: Vector administration endpoints
@app.get("/memory/health")
def get_memory_health():
    """Get comprehensive memory system health status."""
    if not are_vector_features_enabled():
        return {
            "vector_system": "disabled",
            "message": "Vector features not enabled"
        }

    try:
        # Get current stats
        kv_count = get_kv_count()
        vector_store = get_vector_store()

        if not vector_store:
            return {
                "vector_system": "error",
                "message": "Vector store not available"
            }

        # Get vector store stats (simplified - would need enhancement for full indexing)
        vector_count = getattr(vector_store, 'next_vector_index', 0) if hasattr(vector_store, 'next_vector_index') else 0

        # Get drift detection status
        from ..core.drift_rules import detect_drift
        findings = detect_drift()
        drift_count = len(findings)
        critical_findings = [f for f in findings if f.severity == "high"]

        # Heartbeat status
        from ..core.heartbeat import get_status
        heartbeat_stats = get_status()

        return {
            "vector_system": "healthy" if drift_count == 0 else ("warning" if len(critical_findings) == 0 else "critical"),
            "kv_records": kv_count,
            "vector_records": vector_count,
            "drift_findings": drift_count,
            "critical_drift": len(critical_findings),
            "sync_ratio": f"{(vector_count/max(kv_count, 1))*100:.1f}%" if kv_count > 0 else "0%",
            "heartbeat_status": heartbeat_stats.get("status", "unknown"),
            "last_heartbeat": heartbeat_stats.get("uptime_sec", 0)
        }

    except Exception as e:
        return {
            "vector_system": "error",
            "message": str(e)
        }

@app.post("/admin/reindex_vectors")
def reindex_vectors_endpoint():
    """Force reindex all eligible KV entries to vector store."""
    if not debug_enabled():
        raise HTTPException(status_code=403, detail="Admin endpoints require debug mode")

    if not are_vector_features_enabled():
        raise HTTPException(status_code=400, detail="Vector features not enabled")

    try:
        # Clear vector store and reindex all KV entries
        vector_store = get_vector_store()
        embedding_provider = get_embedding_provider()

        if not vector_store or not embedding_provider:
            raise HTTPException(status_code=500, detail="Vector system not available")

        # Clear existing vectors
        vector_store.clear()

        # Reindex all non-sensitive KV entries
        kv_entries = list_keys()  # Get all users' keys
        success_count = 0
        error_count = 0

        for kv in kv_entries:
            if not kv.sensitive:  # Skip sensitive data
                try:
                    # Recreate vector from KV data
                    vector_key = f"{kv.key}"  # Simplified - assumes no user scoping issues for now
                    content_to_embed = f"{kv.key}: {kv.value}"
                    embedding = embedding_provider.embed_text(content_to_embed)

                    from ..vector.types import VectorRecord
                    vector_record = VectorRecord(
                        id=vector_key,
                        vector=embedding,
                        metadata={"source": kv.source, "updated_at": kv.updated_at.isoformat()}
                    )

                    vector_store.add(vector_record)
                    success_count += 1
                except Exception as e:
                    logging.error(f"Failed to reindex KV {kv.key}: {e}")
                    error_count += 1

        # Log admin operation
        add_event(
            user_id="system",
            actor="admin_api",
            action="vector_reindex",
            payload=f"Reindexed {success_count} vectors, {error_count} errors"
        )

        return {
            "success": True,
            "message": f"Reindexed {success_count} vectors",
            "errors": error_count
        }

    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Reindex failed: {str(e)}")


# Stage 5: Episodic & Temporal Memory endpoints
try:
    from .episodic import router as episodic_router
    EPISODIC_ROUTER_AVAILABLE = True
    print("DEBUG: Episodic router imported successfully")
except ImportError as e:
    EPISODIC_ROUTER_AVAILABLE = False
    print(f"DEBUG: Episodic router import failed: {e}")

# Stage 7: Chat API endpoints (feature-flagged)
if CHAT_API_ENABLED:
    try:
        from .chat import router as chat_router
        app.include_router(chat_router, prefix="/chat", tags=["chat"])
        print("[BOOT] Chat router mounted at /chat/* (CHAT_API_ENABLED=true)")
    except Exception as e:
        print(f"[BOOT] Chat router failed to mount: {e}")

# Stage 5: Episodic Memory endpoints (always available)
if EPISODIC_ROUTER_AVAILABLE:
    app.include_router(
        episodic_router,
        prefix="/episodic",
        tags=["episodic"]
    )


# Stage 3: Swarm Orchestration chat endpoint
_swarm_orchestrator = None

def get_swarm_orchestrator():
    """Lazy initialization of swarm orchestrator."""
    global _swarm_orchestrator
    if _swarm_orchestrator is None:
        from ..agents.orchestrator import OrchestratorService
        _swarm_orchestrator = OrchestratorService()
    return _swarm_orchestrator

@app.post("/chat", response_model=SwarmMessageResponse)
async def swarm_chat_endpoint(request: SwarmMessageRequest):
    """
    Stage 3 Swarm Orchestration chat endpoint.

    Processes queries through multi-agent swarm:
    1. Safety pre-validation
    2. Planning and tool coordination
    3. Memory reconciliation (KV-wins)
    4. Answer synthesis with citations
    5. Safety post-validation

    Returns comprehensive response with provenance, timeline, and audit trail.
    """
    try:
        orchestrator = get_swarm_orchestrator()
        response = await orchestrator.process_message(request)
        return response
    except Exception as e:
        # Fallback error response
        logging.error(f"Swarm orchestration failed: {str(e)}")
        return SwarmMessageResponse(
            message_id=f"error_{int(datetime.now().timestamp())}",
            content="I encountered an error processing your request. Please try again.",
            provenance={"error": str(e)},
            timeline=[],
            memory_facts=[],
            safety_blocked=False,
            conversation_id=request.conversation_id,
            turn_id=None,
            model_used="swarm-orchestrator-fallback",
            processing_time_ms=0
        )


# Stage 2: Semantic Memory API endpoints
@app.post("/semantic/index", response_model=SemanticIndexResponse)
def semantic_index_endpoint(request: SemanticIndexRequest):
    """Index documents into semantic memory with provenance tracking."""
    from ..vector.semantic_memory import SemanticMemoryService
    from ..core.config import SEMANTIC_ENABLED

    if not SEMANTIC_ENABLED:
        raise HTTPException(status_code=404, detail="Semantic memory features disabled")

    try:
        service = SemanticMemoryService()
        indexed_ids = service.index_documents(request.docs)

        # Count skipped and failed documents
        total_processed = len(request.docs)
        skipped_sensitive = total_processed - len(indexed_ids)
        failed = 0  # All failures are logged but we don't track exact count here

        return SemanticIndexResponse(
            indexed_ids=indexed_ids,
            skipped_sensitive=skipped_sensitive,
            failed=failed,
            total_processed=total_processed
        )

    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Semantic indexing failed: {str(e)}")

@app.post("/semantic/query", response_model=SemanticQueryResponse)
def semantic_query_endpoint(request: SemanticQueryRequest):
    """Query semantic memory and return relevant results."""
    from ..vector.semantic_memory import SemanticMemoryService
    from ..core.config import SEMANTIC_ENABLED

    if not SEMANTIC_ENABLED:
        raise HTTPException(status_code=404, detail="Semantic memory features disabled")

    try:
        service = SemanticMemoryService()
        hits = service.query(request.text, request.k, request.filters)
        validated_hits = service.rehydrate_and_validate(hits)

        # Extract reconciled facts and conflicts
        reconciled_facts = []
        conflicts = []

        for hit in validated_hits:
            if 'reconciled_facts' in hit:
                reconciled_facts.extend(hit['reconciled_facts'])
            if 'kv_conflicts' in hit:
                conflicts.extend(hit['kv_conflicts'])

        return SemanticQueryResponse(
            hits=hits,
            reconciled_facts=reconciled_facts,
            conflicts=conflicts
        )

    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Semantic query failed: {str(e)}")

@app.get("/semantic/health", response_model=SemanticHealthResponse)
def semantic_health_endpoint():
    """Get semantic memory system health status."""
    from ..vector.semantic_memory import SemanticMemoryService
    from ..core.config import SEMANTIC_ENABLED

    if not SEMANTIC_ENABLED:
        return SemanticHealthResponse(
            status="disabled",
            size=0,
            model_version="n/a",
            index_schema_version="n/a",
            stale=False,
            embeddings_enabled=False,
            sensitive_exclusion=False,
            last_checked=datetime.now().isoformat()
        )

    try:
        service = SemanticMemoryService()
        health = service.health()

        return SemanticHealthResponse(**health)

    except Exception as e:
        return SemanticHealthResponse(
            status="unhealthy",
            size=0,
            model_version="unknown",
            index_schema_version="unknown",
            stale=True,
            embeddings_enabled=False,
            sensitive_exclusion=False,
            error=str(e),
            last_checked=datetime.now().isoformat()
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
