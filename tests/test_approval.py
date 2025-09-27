"""
Stage 4 scope only. Do not implement beyond this file's responsibilities.
Approval workflow tests - ensures comprehensive approval system functionality.
"""

import pytest
from unittest.mock import patch, MagicMock
import os
from datetime import datetime, timedelta

from src.core.approval import (
    ApprovalRequest,
    ApprovalWorkflow,
    create_approval_request,
    get_approval_status,
    approve_request,
    reject_request,
    wait_for_approval,
    list_pending_requests,
    cleanup_expired_requests
)


@pytest.fixture
def approval_workflow():
    """Create a fresh approval workflow for each test."""
    return ApprovalWorkflow()


@pytest.fixture
def approval_enabled():
    """Enable approval system for tests by patching the global flag."""
    from src.core import config
    original_value = config.APPROVAL_ENABLED
    config.APPROVAL_ENABLED = True
    yield
    config.APPROVAL_ENABLED = original_value


@pytest.fixture
def approval_disabled():
    """Disable approval system for tests by patching the global flag."""
    from src.core import config
    original_value = config.APPROVAL_ENABLED
    config.APPROVAL_ENABLED = False
    yield
    config.APPROVAL_ENABLED = original_value


class TestApprovalRequest:
    """Test ApprovalRequest dataclass functionality."""

    def test_approval_request_creation(self):
        """Test creating an approval request."""
        created_at = datetime.now()
        expires_at = created_at + timedelta(hours=1)

        request = ApprovalRequest(
            id="test-123",
            type="correction",
            payload={"key": "test", "action": "update"},
            requester="user123",
            status="pending",
            created_at=created_at,
            expires_at=expires_at,
            approver="admin",
            approval_reason="Approved for testing"
        )

        assert request.id == "test-123"
        assert request.type == "correction"
        assert request.payload == {"key": "test", "action": "update"}
        assert request.requester == "user123"
        assert request.status == "pending"
        assert request.approver == "admin"
        assert request.approval_reason == "Approved for testing"
        assert request.created_at == created_at
        assert request.expires_at == expires_at

    def test_to_dict_and_from_dict(self):
        """Test serialization and deserialization."""
        original = ApprovalRequest(
            id="test-456",
            type="correction",
            payload={"test": "data"},
            requester="user456",
            status="approved",
            created_at=datetime(2023, 1, 1, 12, 0, 0),
            expires_at=datetime(2023, 1, 1, 13, 0, 0),
            approver="admin123",
            approval_reason="Test approval"
        )

        # Convert to dict
        data = original.to_dict()
        assert isinstance(data, dict)
        assert data['id'] == 'test-456'
        assert data['created_at'] == '2023-01-01T12:00:00'
        assert data['expires_at'] == '2023-01-01T13:00:00'

        # Convert back from dict
        restored = ApprovalRequest.from_dict(data)
        assert restored.id == original.id
        assert restored.type == original.type
        assert restored.payload == original.payload
        assert restored.requester == original.requester
        assert restored.status == original.status
        assert restored.created_at == original.created_at
        assert restored.expires_at == original.expires_at
        assert restored.approver == original.approver
        assert restored.approval_reason == original.approval_reason


class TestApprovalWorkflowDisabled:
    """Test approval workflow behavior when disabled."""

    def test_create_request_disabled(self, approval_workflow, approval_disabled):
        """Test that create_request returns None when approval is disabled."""
        request = approval_workflow.create_request(
            "correction",
            {"key": "test"},
            "user123"
        )
        assert request is None

    def test_approve_request_disabled(self, approval_workflow, approval_disabled):
        """Test that approve_request returns True when approval is disabled."""
        success = approval_workflow.approve_request("fake-id", "admin", "reason")
        assert success is True

    def test_reject_request_disabled(self, approval_workflow, approval_disabled):
        """Test that reject_request returns True when approval is disabled."""
        success = approval_workflow.reject_request("fake-id", "admin", "reason")
        assert success is True

    def test_wait_for_approval_disabled(self, approval_workflow, approval_disabled):
        """Test that wait_for_approval returns 'approved' when disabled."""
        status = approval_workflow.wait_for_approval("fake-id")
        assert status == "approved"


class TestApprovalWorkflowEnabled:
    """Test approval workflow behavior when enabled."""

    def test_create_request_valid(self, approval_workflow, approval_enabled):
        """Test creating a valid approval request."""
        request = approval_workflow.create_request(
            "correction",
            {"key": "test_key", "action": "update"},
            "user123"
        )

        assert request is not None
        assert request.type == "correction"
        assert request.payload == {"key": "test_key", "action": "update"}
        assert request.requester == "user123"
        assert request.status == "pending"
        assert request.created_at is not None
        assert request.expires_at is not None
        assert request.expires_at > request.created_at
        assert request.approver is None
        assert request.approval_reason is None

    def test_create_request_invalid_type(self, approval_workflow, approval_enabled):
        """Test creating request with invalid type fails."""
        with pytest.raises(ValueError, match="Invalid request type"):
            approval_workflow.create_request("invalid_type", {}, "user")

    def test_get_request_existing(self, approval_workflow, approval_enabled):
        """Test getting an existing request."""
        created = approval_workflow.create_request("correction", {"test": "data"}, "user")
        retrieved = approval_workflow.get_request(created.id)

        assert retrieved is not None
        assert retrieved.id == created.id
        assert retrieved.status == "pending"

    def test_get_request_nonexistent(self, approval_workflow, approval_enabled):
        """Test getting a non-existent request returns None."""
        result = approval_workflow.get_request("nonexistent-id")
        assert result is None

    def test_get_request_expired(self, approval_workflow, approval_enabled):
        """Test that expired requests are auto-marked as expired."""
        # Create a request
        created = approval_workflow.create_request("correction", {"test": "data"}, "user")

        # Manually set expiration to past
        created.expires_at = datetime.now() - timedelta(hours=1)

        # Get the request (should mark as expired)
        retrieved = approval_workflow.get_request(created.id)
        assert retrieved.status == "expired"

    def test_approve_request_success(self, approval_workflow, approval_enabled):
        """Test successfully approving a request."""
        created = approval_workflow.create_request("correction", {"test": "data"}, "user")

        success = approval_workflow.approve_request(created.id, "admin", "Approved for testing")
        assert success is True

        # Check that request was updated
        updated = approval_workflow.get_request(created.id)
        assert updated.status == "approved"
        assert updated.approver == "admin"
        assert updated.approval_reason == "Approved for testing"

    def test_approve_request_not_found(self, approval_workflow, approval_enabled):
        """Test approving a non-existent request fails."""
        success = approval_workflow.approve_request("fake-id", "admin", "reason")
        assert success is False

    def test_approve_request_not_pending(self, approval_workflow, approval_enabled):
        """Test approving a non-pending request fails."""
        created = approval_workflow.create_request("correction", {"test": "data"}, "user")
        created.status = "expired"  # Manually set to non-pending

        success = approval_workflow.approve_request(created.id, "admin", "reason")
        assert success is False

    def test_reject_request_success(self, approval_workflow, approval_enabled):
        """Test successfully rejecting a request."""
        created = approval_workflow.create_request("correction", {"test": "data"}, "user")

        success = approval_workflow.reject_request(created.id, "admin", "Rejected for testing")
        assert success is True

        # Check that request was updated
        updated = approval_workflow.get_request(created.id)
        assert updated.status == "rejected"
        assert updated.approver == "admin"
        assert updated.approval_reason == "Rejected for testing"

    def test_reject_request_not_found(self, approval_workflow, approval_enabled):
        """Test rejecting a non-existent request fails."""
        success = approval_workflow.reject_request("fake-id", "admin", "reason")
        assert success is False

    def test_reject_request_not_pending(self, approval_workflow, approval_enabled):
        """Test rejecting a non-pending request fails."""
        created = approval_workflow.create_request("correction", {"test": "data"}, "user")
        created.status = "approved"  # Manually set to non-pending

        success = approval_workflow.reject_request(created.id, "admin", "reason")
        assert success is False

    def test_wait_for_approval_pending(self, approval_workflow, approval_enabled):
        """Test wait_for_approval returns current status."""
        created = approval_workflow.create_request("correction", {"test": "data"}, "user")

        # Should be pending initially
        status = approval_workflow.wait_for_approval(created.id)
        assert status == "pending"

        # Approve it
        approval_workflow.approve_request(created.id, "admin", "Approved")

        # Should now be approved
        status = approval_workflow.wait_for_approval(created.id)
        assert status == "approved"

    def test_wait_for_approval_not_found(self, approval_workflow, approval_enabled):
        """Test wait_for_approval for non-existent request."""
        status = approval_workflow.wait_for_approval("fake-id")
        assert status == "not_found"

    def test_list_pending_requests(self, approval_workflow, approval_enabled):
        """Test listing pending requests."""
        # Create multiple requests
        req1 = approval_workflow.create_request("correction", {"key": "test1"}, "user1")
        req2 = approval_workflow.create_request("correction", {"key": "test2"}, "user2")

        # Approve one
        approval_workflow.approve_request(req1.id, "admin", "Approved")

        # List pending should only show one
        pending = approval_workflow.list_pending_requests()
        assert len(pending) == 1
        assert pending[0].id == req2.id

    def test_cleanup_expired_requests(self, approval_workflow, approval_enabled):
        """Test cleaning up expired requests."""
        # Create a request and expire it
        created = approval_workflow.create_request("correction", {"test": "data"}, "user")
        created.expires_at = datetime.now() - timedelta(hours=1)

        # Cleanup should mark as expired and return 1
        cleaned = approval_workflow.cleanup_expired_requests()
        assert cleaned == 1

        # Request should now be expired
        updated = approval_workflow.get_request(created.id)
        assert updated.status == "expired"


class TestApprovalFunctions:
    """Test the global approval functions."""

    def test_global_functions_disabled(self, approval_disabled):
        """Test global functions return None/safe defaults when disabled."""
        request = create_approval_request("correction", {}, "user")
        assert request is None

        status = wait_for_approval("fake-id")
        assert status == "approved"  # Auto-approved when disabled

    def test_global_functions_enabled(self, approval_enabled):
        """Test global functions work when enabled."""
        request = create_approval_request("correction", {"test": "data"}, "user")
        assert request is not None

        # Test getting status
        retrieved = get_approval_status(request.id)
        assert retrieved is not None
        assert retrieved.id == request.id

        # Test listing pending
        pending = list_pending_requests()
        assert len(pending) >= 1

        # Test cleanup (should be 0 since not expired)
        cleaned = cleanup_expired_requests()
        assert cleaned == 0


class TestIntegrationWithCorrections:
    """Test integration points with corrections system."""

    @patch('src.core.corrections.create_approval_request')
    @patch('src.core.corrections.wait_for_approval')
    def test_apply_correction_with_approval_enabled(self, mock_wait, mock_create):
        """Test corrections require approval when enabled."""
        from src.core.corrections import _apply_correction_with_approval

        # Mock approval workflow
        mock_request = MagicMock()
        mock_request.id = "test-request-id"
        mock_create.return_value = mock_request
        mock_wait.return_value = "approved"

        # Mock the actual correction execution
        from unittest.mock import patch
        with patch('src.core.corrections._apply_correction_action') as mock_apply:
            with patch('src.core.corrections._log_correction_application') as mock_log:
                # Execute with approval enabled
                success, message = _apply_correction_with_approval("test-plan", MagicMock(), MagicMock(), MagicMock())

                assert success is True
                assert "Applied" in message
                mock_create.assert_called_once()
                mock_wait.assert_called_once()
                mock_apply.assert_called_once()
                mock_log.assert_called_once()

    @patch('src.core.corrections.create_approval_request')
    def test_apply_correction_approval_disabled(self, mock_create):
        """Test corrections don't require approval when disabled."""
        from src.core.corrections import _apply_correction_with_approval

        # With approval disabled, should return None from create_approval_request
        mock_create.return_value = None

        # Mock the actual correction execution
        from unittest.mock import patch
        with patch('src.core.corrections._apply_correction_action') as mock_apply:
            with patch('src.core.corrections._log_correction_application') as mock_log:
                # Execute with approval disabled
                success, message = _apply_correction_with_approval("test-plan", MagicMock(), MagicMock(), MagicMock())

                assert success is False
                assert "Approval system disabled" in message
                mock_create.assert_called_once()
                mock_apply.assert_not_called()
                mock_log.assert_not_called()

    @patch('src.core.corrections.create_approval_request')
    @patch('src.core.corrections.wait_for_approval')
    def test_apply_correction_approval_denied(self, mock_wait, mock_create):
        """Test corrections fail when approval is denied."""
        from src.core.corrections import _apply_correction_with_approval

        # Mock approval workflow
        mock_request = MagicMock()
        mock_request.id = "test-request-id"
        mock_create.return_value = mock_request
        mock_wait.return_value = "rejected"  # Approval denied

        # Execute
        success, message = _apply_correction_with_approval("test-plan", MagicMock(), MagicMock(), MagicMock())

        assert success is False
        assert "not approved" in message
        mock_create.assert_called_once()
        mock_wait.assert_called_once()
