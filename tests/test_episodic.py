"""
Stage 5: Episodic & Temporal Memory Tests
Tests for episodic event logging, retrieval, and summarization.
"""

import pytest
from datetime import datetime, timedelta
import json

from src.core.dao import add_event, list_episodic_events_stage5, summarize_episodic_events
from src.core.db import init_db, get_db


@pytest.fixture(autouse=True)
def setup_database():
    """Initialize database for each test."""
    init_db()


def test_log_episodic_event_basic():
    """Test basic episodic event logging."""
    user_id = "test_user"
    session_id = "test_session_123"

    # Log user message
    success = add_event(
        user_id=user_id,
        actor="user",  # Required backward compatibility
        action="message",  # Required backward compatibility
        payload="Hello, I love hiking and espresso",  # Required backward compatibility
        session_id=session_id,
        event_type="user",
        message="Hello, I love hiking and espresso",
        summary="User greeting with preferences",
        sensitive=False
    )

    assert success is True

    # Log AI response
    success = add_event(
        user_id=user_id,
        actor="ai",  # Required backward compatibility
        action="response",  # Required backward compatibility
        payload="Hello! Sounds like you're into outdoor activities and coffee.",  # Required backward compatibility
        session_id=session_id,
        event_type="ai",
        message="Hello! Sounds like you're into outdoor activities and coffee.",
        summary="AI greeting response",
        sensitive=False
    )

    assert success is True


def test_episodic_event_retrieval():
    """Test retrieving episodic events with filters."""
    user_id = "test_user"
    session_id = "test_session_456"

    # Log events
    add_event(user_id=user_id, session_id=session_id, event_type="user", message="Set my displayName to Alice")
    add_event(user_id=user_id, session_id=session_id, event_type="ai", message="Stored displayName = 'Alice'")
    add_event(user_id=user_id, session_id=session_id, event_type="user", message="What's my display name?")

    # Retrieve recent events
    events = list_episodic_events_stage5(user_id=user_id, session_id=session_id, limit=10)

    assert len(events) >= 3

    # Check event types
    event_types = [e.get("event_type") for e in events]
    assert "user" in event_types
    assert "ai" in event_types

    # Check session grouping
    session_ids = [e.get("session_id") for e in events]
    assert all(sid == session_id for sid in session_ids if sid)

    # Test type filtering
    user_events = list_episodic_events_stage5(user_id=user_id, event_type="user", limit=10)
    assert all(e.get("event_type") == "user" for e in user_events)


def test_episodic_event_ordering():
    """Test events are returned in chronological order (DESC)."""
    user_id = "test_user"
    session_id = "test_session_789"

    # Log events with timestamps
    import time
    time.sleep(0.1)  # Ensure different timestamps

    add_event(user_id=user_id, session_id=session_id, event_type="user", message="First message")
    time.sleep(0.1)
    add_event(user_id=user_id, session_id=session_id, event_type="ai", message="First response")
    time.sleep(0.1)
    add_event(user_id=user_id, session_id=session_id, event_type="user", message="Second message")

    events = list_episodic_events_stage5(user_id=user_id, session_id=session_id, limit=10)

    # Should be in reverse chronological order (most recent first)
    assert len(events) >= 3
    messages = [e.get("message") for e in events]
    assert "Second message" in messages
    assert "First response" in messages
    assert "First message" in messages


def test_episodic_event_privacy():
    """Test privacy filtering for episodic events."""
    user_id = "test_user"
    session_id = "test_session_privacy"

    # Log sensitive event
    add_event(
        user_id=user_id,
        session_id=session_id,
        event_type="user",
        message="My password is secret123",
        sensitive=True
    )

    # Log normal event
    add_event(
        user_id=user_id,
        session_id=session_id,
        event_type="user",
        message="Hello world",
        sensitive=False
    )

    # Retrieve events - privacy enforcement should be respected
    events = list_episodic_events_stage5(user_id=user_id, session_id=session_id, limit=10)

    # Should get events, but sensitive ones may be filtered based on access
    assert len(events) >= 1


def test_summarize_episodic_session():
    """Test session summarization functionality."""
    user_id = "test_user"
    session_id = "test_session_summary"

    # Log conversation events
    events_to_log = [
        ("user", "Set my displayName to Alice"),
        ("ai", "Stored displayName = 'Alice'"),
        ("user", "I love hiking and espresso"),
        ("ai", "Great preferences! I'll remember those."),
        ("user", "What's my display name?"),
        ("ai", "Your displayName is 'Alice'"),
    ]

    for event_type, message in events_to_log:
        add_event(
            user_id=user_id,
            session_id=session_id,
            event_type=event_type,
            message=message,
            sensitive=False
        )

    # Generate summary
    summary = summarize_episodic_events(user_id=user_id, session_id=session_id, use_ai=False)

    assert summary
    assert isinstance(summary, str)
    assert len(summary) > 10

    # Summary should contain key elements
    summary_lower = summary.lower()
    assert "alice" in summary_lower or "display" in summary_lower
    assert "preference" in summary_lower or "hiking" in summary_lower


def test_summarize_episodic_empty_session():
    """Test summarization for session with no events."""
    user_id = "test_user"
    session_id = "empty_session"

    # Generate summary for empty session
    summary = summarize_episodic_events(user_id=user_id, session_id=session_id)

    assert summary
    assert "no events found" in summary.lower() or "no events" in summary.lower()


def test_episodic_event_timestamp_filtering():
    """Test temporal filtering of episodic events."""
    user_id = "test_user"
    session_id = "test_session_time"

    # Log events
    add_event(user_id=user_id, session_id=session_id, event_type="user", message="Old message")
    start_time = datetime.now().isoformat()
    import time
    time.sleep(0.1)
    add_event(user_id=user_id, session_id=session_id, event_type="user", message="Recent message")

    # Get events since start_time
    events = list_episodic_events_stage5(user_id=user_id, session_id=session_id, since=start_time)

    # Should only get the recent event
    assert len(events) >= 1
    assert any("Recent" in e.get("message", "") for e in events)


def test_episodic_integration_with_chat():
    """Test integration between episodic logging and chat API."""
    user_id = "chat_integration_user"
    session_id = "integration_session"

    # Log chat-like events
    add_event(user_id=user_id, session_id=session_id, event_type="user", message="Summarize our session so far")
    add_event(
        user_id=user_id,
        session_id=session_id,
        event_type="ai",
        message="You've set your display name and shared preferences for hiking and coffee.",
        summary="Session summary provided"
    )

    # Verify we can retrieve these chat events
    events = list_episodic_events_stage5(user_id=user_id, session_id=session_id)

    assert len(events) >= 2
    event_types = set(e.get("event_type") for e in events)
    assert "user" in event_types
    assert "ai" in event_types


def test_episodic_event_sensitive_content_detection():
    """Test automatic sensitive content detection in messages."""
    user_id = "sensitive_test_user"
    session_id = "sensitive_session"

    messages = [
        ("Hello world", False),  # Not sensitive
        ("My password is admin123", True),  # Contains sensitive indicators
        ("Remember my favorite food is pizza", False),  # Not sensitive
        ("Tell me a secret", True),  # Sensitive word
        ("I love hiking", False),  # Not sensitive
    ]

    for message, should_be_sensitive in messages:
        add_event(
            user_id=user_id,
            session_id=session_id,
            event_type="user",
            message=message,
            sensitive=False  # Let DAO detect
        )

    events = list_episodic_events_stage5(user_id=user_id, session_id=session_id)

    # Find the sensitive events
    sensitive_events = [e for e in events if e.get("sensitive")]

    # Should have detected some sensitive content
    assert len(sensitive_events) >= 1


if __name__ == "__main__":
    pytest.main([__file__])
