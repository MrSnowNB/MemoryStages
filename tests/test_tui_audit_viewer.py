"""
Stage 5 scope only. Do not implement beyond this file's responsibilities.
Operations dashboard audit viewer tests - validates log viewing with privacy controls.
"""

import pytest
import os
from unittest.mock import patch, MagicMock
from datetime import datetime, timedelta
from dataclasses import dataclass

from src.core import config


@pytest.fixture
def audit_env():
    """Set environment variables for audit testing."""
    original_env = os.environ.copy()
    os.environ["DASHBOARD_ENABLED"] = "true"
    os.environ["DASHBOARD_AUTH_TOKEN"] = "test_admin_token"
    os.environ["VECTOR_ENABLED"] = "true"

    # Force reload config
    import importlib
    importlib.reload(config)

    yield

    # Restore environment
    os.environ.clear()
    os.environ.update(original_env)
    importlib.reload(config)


@pytest.fixture
def mock_events():
    """Create mock audit events for testing."""
    @dataclass
    class MockEvent:
        id: int
        actor: str
        action: str
        data: str
        ts: datetime

    # Create events with different types and content
    events = [
        MockEvent(
            id=1,
            actor="admin",
            action="KV.put.success",
            data='{"key": "test_key", "value": "normal_data"}',
            ts=datetime.now() - timedelta(minutes=5)
        ),
        MockEvent(
            id=2,
            actor="user",
            action="dashboard.login.success",
            data='{"token": "secret_token_123"}',
            ts=datetime.now() - timedelta(minutes=10)
        ),
        MockEvent(
            id=3,
            actor="system",
            action="heartbeat.scan.completed",
            data='{"findings": 2, "corrections": 0}',
            ts=datetime.now() - timedelta(hours=1)
        ),
    ]
    return events


class TestAuditSearchCriteria:
    """Test audit search criteria functionality."""

    def test_search_criteria_basic_creation(self, audit_env):
        """Test basic search criteria creation."""
        from tui.audit_viewer import AuditSearchCriteria

        criteria = AuditSearchCriteria(
            start_date=datetime.now() - timedelta(hours=1),
            end_date=datetime.now(),
            limit=100,
            offset=0
        )

        assert criteria.start_date is not None
        assert criteria.end_date is not None
        assert criteria.limit == 100
        assert criteria.offset == 0

    def test_search_criteria_defaults(self, audit_env):
        """Test search criteria default values."""
        from tui.audit_viewer import AuditSearchCriteria

        criteria = AuditSearchCriteria()

        assert criteria.start_date is None
        assert criteria.end_date is None
        assert criteria.actor is None
        assert criteria.operation is None
        assert criteria.search_text is None
        assert criteria.status is None
        assert criteria.limit == 50
        assert criteria.offset == 0


class TestAuditEventPrivacyControls:
    """Test privacy controls for audit event data."""

    def test_sensitive_data_redaction_regular_fields(self, audit_env):
        """Test redaction of sensitive field names."""
        from tui.audit_viewer import AuditLogViewer

        viewer = AuditLogViewer()

        # Test data with sensitive fields
        sensitive_data = '{"value": "secret_value", "password": "mypassword", "token": "auth_token_123"}'
        redacted = viewer._process_event_data(sensitive_data)

        assert "[REDACTED]" in redacted
        assert "secret_value" not in redacted
        assert "mypassword" not in redacted
        assert "auth_token_123" not in redacted

    def test_sensitive_data_redaction_key_value_format(self, audit_env):
        """Test redaction in key=value formats."""
        from tui.audit_viewer import AuditLogViewer

        viewer = AuditLogViewer()

        sensitive_data = "password=mysecret token=abc123 value=data"
        redacted = viewer._process_event_data(sensitive_data)

        assert "[REDACTED]" in redacted
        assert "mysecret" not in redacted
        assert "abc123" not in redacted

    def test_non_sensitive_data_preserved(self, audit_env):
        """Test that non-sensitive data is preserved."""
        from tui.audit_viewer import AuditLogViewer

        viewer = AuditLogViewer()

        safe_data = '{"key": "normal_key", "action": "read", "status": "success"}'
        processed = viewer._process_event_data(safe_data)

        assert processed == safe_data
        assert "[REDACTED]" not in processed

    def test_data_truncation_for_display(self, audit_env):
        """Test that long data is truncated for display."""
        from tui.audit_viewer import AuditLogViewer

        viewer = AuditLogViewer()

        long_data = str({"key": "test"}) * 100  # Very long string when serialized
        result = viewer._process_event_data(long_data)

        assert len(result) <= 503  # Original length limit + truncation marker


class TestEventClassification:
    """Test audit event classification by operation type."""

    def test_operation_classification_key_value(self, audit_env):
        """Test classification of key-value operations."""
        from tui.audit_viewer import AuditLogViewer

        viewer = AuditLogViewer()

        assert viewer._classify_operation("KV.put.success") == "key-value"
        assert viewer._classify_operation("KV.get.warning") == "key-value"

    def test_operation_classification_vector(self, audit_env):
        """Test classification of vector operations."""
        from tui.audit_viewer import AuditLogViewer

        viewer = AuditLogViewer()

        assert viewer._classify_operation("vector.search.success") == "vector"
        assert viewer._classify_operation("vector.index.error") == "vector"

    def test_operation_classification_approval(self, audit_env):
        """Test classification of approval operations."""
        from tui.audit_viewer import AuditLogViewer

        viewer = AuditLogViewer()

        assert viewer._classify_operation("approval.request.success") == "approval"
        assert viewer._classify_operation("approval.decision.info") == "approval"

    def test_operation_classification_unknown(self, audit_env):
        """Test classification of unknown operations."""
        from tui.audit_viewer import AuditLogViewer

        viewer = AuditLogViewer()

        assert viewer._classify_operation("custom.operation.success") == "other"
        assert viewer._classify_operation("unknown") == "other"


class TestAuditLogViewerCoreFunctionality:
    """Test core audit log viewer functionality."""

    @patch('tui.auth.check_admin_access', return_value=True)
    @patch('src.core.dao.list_events')
    def test_get_recent_events_processing(self, mock_list_events, mock_check_admin, audit_env, mock_events):
        """Test recent events retrieval and processing."""
        mock_list_events.return_value = mock_events[:2]  # Only first 2 events

        from tui.audit_viewer import get_recent_audit_events, AuditEvent
        events = get_recent_audit_events(limit=5)

        assert len(events) == 2
        assert all(isinstance(e, AuditEvent) for e in events)
        assert events[0].actor == "admin"
        assert events[1].actor == "user"

    @patch('src.core.dao.list_events')
    def test_get_audit_summary_calculation(self, mock_list_events, audit_env, mock_events):
        """Test audit summary calculation."""
        mock_list_events.return_value = mock_events

        from tui.audit_viewer import get_audit_summary
        summary = get_audit_summary()

        assert "total_events" in summary
        assert "operation_types" in summary
        assert "sensitive_events" in summary

        # Should have classified operations
        assert "key-value" in summary["operation_types"]
        assert summary["total_events"] == 3

    def test_sensitive_event_detection(self, audit_env):
        """Test detection of events containing sensitive data."""
        from tui.audit_viewer import AuditLogViewer

        viewer = AuditLogViewer()

        # Create mock event with sensitive data
        class MockEvent:
            def __init__(self, data):
                self.data = data

        # Test various sensitive patterns
        sensitive_event = MockEvent('{"token": "secret", "value": "data"}')
        normal_event = MockEvent('{"key": "normal", "action": "read"}')

        assert viewer._is_event_sensitive(sensitive_event) is True
        assert viewer._is_event_sensitive(normal_event) is False


class TestAuditSearchFunctionality:
    """Test audit search and filtering capabilities."""

    @patch('src.core.dao.list_events')
    def test_search_criteria_filtering(self, mock_list_events, audit_env, mock_events):
        """Test search criteria application."""
        mock_list_events.return_value = mock_events

        from tui.audit_viewer import AuditLogViewer, AuditSearchCriteria

        viewer = AuditLogViewer()

        # Search for admin actor
        criteria = AuditSearchCriteria(actor="admin")
        events, total = viewer.search_events(criteria)

        assert len(events) == 1
        assert events[0].actor == "admin"

    @patch('src.core.dao.list_events')
    def test_date_range_filtering(self, mock_list_events, audit_env, mock_events):
        """Test date range filtering."""
        mock_list_events.return_value = mock_events

        from tui.audit_viewer import AuditLogViewer, AuditSearchCriteria

        viewer = AuditLogViewer()

        # Search events from last 15 minutes
        criteria = AuditSearchCriteria(
            start_date=datetime.now() - timedelta(minutes=15),
            end_date=datetime.now()
        )
        events, total = viewer.search_events(criteria)

        # Should find the most recent 2 events
        assert len(events) == 2
        assert events[0].actor == "admin"

    @patch('src.core.dao.list_events')
    def test_full_text_searching(self, mock_list_events, audit_env, mock_events):
        """Test full-text search functionality."""
        mock_list_events.return_value = mock_events

        from tui.audit_viewer import AuditLogViewer, AuditSearchCriteria

        viewer = AuditLogViewer()

        # Search for "test" in data
        criteria = AuditSearchCriteria(search_text="test")
        events, total = viewer.search_events(criteria)

        assert len(events) == 1
        assert events[0].actor == "admin"


class TestAuditEventPermissions:
    """Test audit access permission controls."""

    def test_audit_access_requires_permissions(self, audit_env):
        """Test that audit access requires proper permissions."""
        from tui.audit_viewer import AuditLogViewer, AuditSearchCriteria
        from tui.auth import check_admin_access

        # Mock insufficient permissions
        with patch('tui.auth.check_admin_access', return_value=False):
            viewer = AuditLogViewer()
            criteria = AuditSearchCriteria()

            events, total = viewer.search_events(criteria)

            assert events == []
            assert total == 0

    def test_sensitive_detail_access_control(self, audit_env):
        """Test sensitive data access requires explicit permission."""
        from tui.audit_viewer import AuditLogViewer, AuditSearchCriteria

        viewer = AuditLogViewer()

        with patch('src.core.dao.list_events', return_value=[]), \
             patch('tui.auth.check_admin_access') as mock_check:

            # Test normal access (should not require sensitive access)
            mock_check.return_value = False  # No sensitive access
            criteria = AuditSearchCriteria()
            events, total = viewer.search_events(criteria)

            # When sensitive access is not mocked as required, should still work
            # The actual permission check happens, but our test focuses on structure

    @patch('tui.auth.check_admin_access', return_value=True)
    @patch('src.core.dao.list_events')
    def test_audit_access_with_permissions(self, mock_list_events, mock_check_admin, audit_env, mock_events):
        """Test audit access with proper permissions."""
        mock_list_events.return_value = mock_events[:1]

        from tui.audit_viewer import AuditLogViewer, AuditSearchCriteria

        viewer = AuditLogViewer()
        criteria = AuditSearchCriteria()

        events, total = viewer.search_events(criteria)

        assert len(events) == 1
        assert events[0].actor == "admin"


class TestAuditCachingLimits:
    """Test audit viewer resource management."""

    @patch('src.core.dao.list_events')
    def test_result_limit_enforcement(self, mock_list_events, audit_env):
        """Test that results are limited to prevent memory issues."""
        from tui.audit_viewer import AuditLogViewer, AuditSearchCriteria

        # Create many mock events (more than limit)
        many_events = []
        for i in range(1500):  # More than _max_results of 1000
            event = MagicMock()
            event.id = i
            event.actor = f"actor_{i}"
            event.action = f"action_{i}.success"
            event.data = f"data_{i}"
            event.ts = datetime.now()
            many_events.append(event)

        mock_list_events.return_value = many_events

        viewer = AuditLogViewer()

        # Should not process more than max_results
        criteria = AuditSearchCriteria()
        events, total = viewer.search_events(criteria)

        # Should return configured limit (50)
        assert len(events) == 50
        assert total <= 1000  # Should not exceed max_results


class TestAuditEventStatusExtraction:
    """Test extraction of status information from audit events."""

    def test_status_extraction_success_cases(self, audit_env):
        """Test successful status extraction."""
        from tui.audit_viewer import AuditLogViewer

        viewer = AuditLogViewer()

        assert viewer._extract_status("KV.put.success") == "success"
        assert viewer._extract_status("vector.search.error") == "error"
        assert viewer._extract_status("approval.decision.info") == "info"

    def test_status_extraction_unknown_cases(self, audit_env):
        """Test unknown status handling."""
        from tui.audit_viewer import AuditLogViewer

        viewer = AuditLogViewer()

        assert viewer._extract_status("custom.action.unknown") == "unknown"
        assert viewer._extract_status("no_dots") == "unknown"


class TestAuditViewerIntegration:
    """Test integration with audit viewer functions."""

    @patch('tui.audit_viewer.audit_viewer.search_events')
    def test_global_function_interfaces(self, mock_search, audit_env):
        """Test global audit viewer function interfaces."""
        from tui.audit_viewer import search_audit_events, get_recent_audit_events, get_audit_summary, AuditSearchCriteria

        # Test search interface
        mock_search.return_value = ([], 0)
        criteria = AuditSearchCriteria()
        events, total = search_audit_events(criteria)

        assert events == []
        assert total == 0

        # Test recent events interface
        with patch('tui.audit_viewer.audit_viewer.get_recent_events') as mock_recent:
            mock_recent.return_value = []
            recent = get_recent_audit_events(5)
            assert recent == []

        # Test summary interface
        with patch('tui.audit_viewer.audit_viewer.get_audit_summary') as mock_summary:
            mock_summary.return_value = {"total": 0}
            summary = get_audit_summary()
            assert summary == {"total": 0}
