"""
Stage 5: Episodic & Temporal Memory API
Provides endpoints for logging, retrieving, and summarizing conversation events.
"""

from fastapi import APIRouter, HTTPException, Query
from typing import List, Dict, Any, Optional
from datetime import datetime
from pydantic import BaseModel

from ..core.dao import (
    add_event,
    list_episodic_events_stage5,
    summarize_episodic_events
)
from .schemas import EpisodicRequest

router = APIRouter()

class EpisodicEventRequest(BaseModel):
    """Request model for logging episodic events with Stage 5 fields."""
    session_id: Optional[str] = None
    event_type: Optional[str] = None  # 'user', 'ai', 'system', 'agent'
    message: Optional[str] = None
    summary: Optional[str] = None
    sensitive: bool = False

    # Backward compatibility fields - will be deprecated
    actor: Optional[str] = None
    action: Optional[str] = None
    payload: Optional[str] = None

class EpisodicSummaryRequest(BaseModel):
    """Request model for summarizing episodic events."""
    session_id: Optional[str] = None
    since: Optional[str] = None  # ISO datetime or timestamp
    limit: int = 100
    use_ai: bool = False  # Whether to use AI summarization

@router.post("/event")
async def log_episodic_event(request: EpisodicEventRequest):
    """Log an episodic event with Stage 5 temporal memory support.

    This endpoint supports both old and new episodic event formats.
    New format includes session_id, event_type, message, summary for conversation tracking.
    """
    # Stage 5 event logging - support both new and legacy formats
    success = add_event(
        user_id="default",  # TODO: Extract from auth/JWT in production
        session_id=request.session_id,
        event_type=request.event_type,
        message=request.message,
        summary=request.summary,
        sensitive=request.sensitive,
        # Legacy support
        actor=request.actor or "api",
        action=request.action or "episodic_event",
        payload=request.payload or "{}"
    )

    if not success:
        raise HTTPException(status_code=500, detail="Failed to log episodic event")

    return {"ok": True, "message": "Episodic event logged successfully"}

@router.get("/recent")
async def get_recent_episodic_events(
    session_id: Optional[str] = Query(None, description="Filter by conversation session ID"),
    event_type: Optional[str] = Query(None, description="Filter by event type: user, ai, system, agent"),
    since: Optional[str] = Query(None, description="Filter by timestamp (ISO format or unix timestamp)"),
    limit: int = Query(50, description="Maximum number of events to return", le=200)
) -> Dict[str, Any]:
    """Retrieve recent episodic events with Stage 5 temporal filtering.

    Supports session-based, type-based, and temporal filtering for conversation exploration.
    """
    try:
        # Validate event_type parameter
        if event_type and event_type not in ['user', 'ai', 'system', 'agent']:
            raise HTTPException(
                status_code=400,
                detail=f"Invalid event_type '{event_type}'. Must be one of: user, ai, system, agent"
            )

        events = list_episodic_events_stage5(
            user_id="default",  # TODO: Extract from auth/JWT in production
            session_id=session_id,
            event_type=event_type,
            since=since,
            limit=limit
        )

        return {
            "events": events,
            "count": len(events),
            "filters": {
                "session_id": session_id,
                "event_type": event_type,
                "since": since,
                "limit": limit
            }
        }

    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to retrieve episodic events: {str(e)}")

@router.post("/summarize")
async def summarize_episodic_session(request: EpisodicSummaryRequest) -> Dict[str, Any]:
    """Generate AI-powered or text-based summaries of conversation sessions.

    Can summarize entire conversations, recent activity, or session-specific interactions.
    Supports both AI-powered (if available) and fallback text-based summarization.
    """
    try:
        summary = summarize_episodic_events(
            user_id="default",  # TODO: Extract from auth/JWT in production
            session_id=request.session_id,
            since=request.since,
            limit=request.limit,
            use_ai=request.use_ai
        )

        return {
            "summary": summary,
            "parameters": {
                "session_id": request.session_id,
                "since": request.since,
                "limit": request.limit,
                "use_ai": request.use_ai
            },
            "method": "ai" if request.use_ai else "text"
        }

    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to generate episodic summary: {str(e)}")

# Backward compatibility endpoint for existing callers
@router.post("/log")
async def log_event_backward_compatibility(request: EpisodicRequest):
    """Deprecated: Log an episodic event (Stage 0-4 compatibility).

    This endpoint is maintained for backward compatibility.
    New code should use /event endpoint with Stage 5 fields.
    """
    success = add_event(
        user_id="default",  # TODO: Extract from auth/JWT in production
        actor=request.actor,
        action=request.action,
        payload=request.payload
    )

    if not success:
        raise HTTPException(status_code=500, detail="Failed to log event")

    return {"ok": True, "message": "Event logged (deprecated endpoint - use /event for new features)"}

@router.get("/sessions")
async def list_conversation_sessions(
    limit: int = Query(20, description="Maximum number of recent sessions to return", le=100)
) -> Dict[str, Any]:
    """Get a list of recent conversation sessions for session-based exploration."""
    try:
        # Get all recent events, then extract unique sessions
        events = list_episodic_events_stage5(
            user_id="default",  # TODO: Extract from auth/JWT in production
            limit=500  # Get enough events to cover multiple sessions
        )

        # Group events by session and compute session metadata
        sessions = {}
        for event in events:
            sess_id = event.get("session_id")
            if sess_id:
                if sess_id not in sessions:
                    sessions[sess_id] = {
                        "session_id": sess_id,
                        "event_count": 0,
                        "user_messages": 0,
                        "ai_messages": 0,
                        "start_time": event.get("timestamp"),
                        "end_time": event.get("timestamp"),
                        "sensitive_events": 0
                    }

                session = sessions[sess_id]
                session["event_count"] += 1
                session["end_time"] = max(session["end_time"], event.get("timestamp", session["end_time"]))

                if event.get("event_type") == "user":
                    session["user_messages"] += 1
                elif event.get("event_type") == "ai":
                    session["ai_messages"] += 1

                if event.get("sensitive"):
                    session["sensitive_events"] += 1

        # Convert to sorted list (most recent first)
        session_list = list(sessions.values())
        session_list.sort(key=lambda s: s["end_time"], reverse=True)
        session_list = session_list[:limit]

        return {
            "sessions": session_list,
            "count": len(session_list),
            "description": "Shows recent conversation sessions with basic statistics"
        }

    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to retrieve session list: {str(e)}")
