"""
Stage 4 scope only. Do not implement beyond this file's responsibilities.
Approval workflows - provides human oversight for corrections and sensitive operations.
"""

import uuid
from datetime import datetime, timedelta
from dataclasses import dataclass, asdict
from typing import Dict, Optional, List
from .config import APPROVAL_ENABLED, APPROVAL_TIMEOUT_SEC

# Import logger safely to avoid circular imports
try:
    from ...util.logging import logger
except ImportError:
    # Fallback for direct module execution
    import logging
    logger = logging.getLogger("approval_fallback")
    logger.setLevel(logging.INFO)
    if not logger.handlers:
        logger.addHandler(logging.StreamHandler())

def debug_enabled():
    """Check if debug mode is enabled (from config)."""
    from .config import debug_enabled as debug_enabled_config
    return debug_enabled_config()


@dataclass
class ApprovalRequest:
    id: str
    type: str  # 'correction', 'sensitive_operation'
    payload: Dict
    requester: str
    status: str  # pending, approved, rejected, expired
    created_at: datetime
    expires_at: datetime
    approver: Optional[str] = None
    approval_reason: Optional[str] = None

    def to_dict(self) -> Dict:
        """Convert to dictionary for storage."""
        data = asdict(self)
        # Convert datetime objects to ISO format strings
        data['created_at'] = self.created_at.isoformat()
        data['expires_at'] = self.expires_at.isoformat()
        return data

    @classmethod
    def from_dict(cls, data: Dict) -> 'ApprovalRequest':
        """Create from dictionary (for loading from storage)."""
        # Convert ISO format strings back to datetime objects
        data['created_at'] = datetime.fromisoformat(data['created_at'])
        data['expires_at'] = datetime.fromisoformat(data['expires_at'])
        return cls(**data)


class ApprovalWorkflow:
    """Manages approval requests in memory (for development/testing).

    In production, this would use a database or external approval service.
    """

    def __init__(self):
        self._requests: Dict[str, ApprovalRequest] = {}
        # Track outstanding approvals that need to be waited on
        self._pending_promises: Dict[str, any] = {}

    def create_request(self, request_type: str, payload: Dict, requester: str) -> ApprovalRequest:
        """Create a new approval request."""
        if request_type not in ['correction', 'sensitive_operation']:
            raise ValueError(f"Invalid request type: {request_type}")

        request_id = str(uuid.uuid4())
        created_at = datetime.now()
        expires_at = created_at + timedelta(seconds=APPROVAL_TIMEOUT_SEC)

        request = ApprovalRequest(
            id=request_id,
            type=request_type,
            payload=payload,
            requester=requester,
            status='pending',
            created_at=created_at,
            expires_at=expires_at
        )

        self._requests[request_id] = request

        # Log creation
        logger.info(f"Created approval request {request_id} by {requester} for {request_type}")

        # Add episodic event (would be done by calling component)
        self._log_episodic_event('approval_created', request.to_dict())

        return request

    def get_request(self, request_id: str) -> Optional[ApprovalRequest]:
        """Get an approval request by ID."""
        request = self._requests.get(request_id)
        if request:
            # Check for expiration
            if request.status == 'pending' and datetime.now() > request.expires_at:
                request.status = 'expired'
                self._log_episodic_event('approval_expired', {'request_id': request_id})
        return request

    def approve_request(self, request_id: str, approver: str, reason: str = "") -> bool:
        """Approve an approval request."""
        if not APPROVAL_ENABLED:
            logger.warning("Approval system disabled, approval bypassed")
            return True

        request = self._requests.get(request_id)
        if not request:
            return False

        if request.status != 'pending':
            return False

        request.status = 'approved'
        request.approver = approver
        request.approval_reason = reason

        # Log approval
        logger.info(f"Approved request {request_id} by {approver}: {reason}")

        # Add episodic event
        self._log_episodic_event('approval_granted', {
            'request_id': request_id,
            'approver': approver,
            'reason': reason
        })

        # Release any waiting promises (in async implementations)
        if request_id in self._pending_promises:
            # This would wake up any waiting coroutines/processes
            pass

        return True

    def reject_request(self, request_id: str, approver: str, reason: str = "") -> bool:
        """Reject an approval request."""
        if not APPROVAL_ENABLED:
            logger.warning("Approval system disabled, rejection bypassed")
            return True

        request = self._requests.get(request_id)
        if not request:
            return False

        if request.status != 'pending':
            return False

        request.status = 'rejected'
        request.approver = approver
        request.approval_reason = reason

        # Log rejection
        logger.info(f"Rejected request {request_id} by {approver}: {reason}")

        # Add episodic event
        self._log_episodic_event('approval_denied', {
            'request_id': request_id,
            'approver': approver,
            'reason': reason
        })

        return True

    def wait_for_approval(self, request_id: str) -> str:
        """Wait for an approval request to be resolved (blocking)."""
        if not APPROVAL_ENABLED:
            return 'approved'  # Auto-approve when disabled

        request = self._requests.get(request_id)
        if not request:
            return 'not_found'

        # In a real implementation, this would be async or use threading
        # For now, just return current status (simulating immediate decision)
        if request.status == 'pending':
            return 'pending'
        return request.status

    def list_pending_requests(self) -> List[ApprovalRequest]:
        """List all pending approval requests."""
        return [r for r in self._requests.values() if r.status == 'pending']

    def cleanup_expired_requests(self) -> int:
        """Clean up expired requests and return count cleaned up."""
        expired = []
        for req_id, request in self._requests.items():
            if request.status == 'pending' and datetime.now() > request.expires_at:
                request.status = 'expired'
                expired.append(req_id)

        for req_id in expired:
            self._log_episodic_event('approval_expired', {'request_id': req_id})

        return len(expired)

    def _log_episodic_event(self, action: str, payload: Dict):
        """Log an episodic event for audit trail."""
        try:
            from .dao import add_event
            add_event(user_id="system", actor="approval_system", action=action, payload=str(payload))
        except Exception as e:
            logger.error(f"Failed to log episodic event {action}: {e}")
            if debug_enabled():
                print(f"Episodic event {action}: {payload}")


# Global approval workflow instance
approval_workflow = ApprovalWorkflow()


def create_approval_request(type: str, payload: Dict, requester: str) -> Optional[ApprovalRequest]:
    """Create a new approval request."""
    return approval_workflow.create_request(type, payload, requester)


def get_approval_status(request_id: str) -> Optional[ApprovalRequest]:
    """Get approval request status."""
    return approval_workflow.get_request(request_id)


def approve_request(request_id: str, approver: str, reason: str) -> bool:
    """Approve an approval request."""
    return approval_workflow.approve_request(request_id, approver, reason)


def reject_request(request_id: str, approver: str, reason: str) -> bool:
    """Reject an approval request."""
    return approval_workflow.reject_request(request_id, approver, reason)


def wait_for_approval(request_id: str) -> str:
    """Wait for approval decision (blocking)."""
    return approval_workflow.wait_for_approval(request_id)


def list_pending_requests() -> List[ApprovalRequest]:
    """List pending approval requests."""
    return approval_workflow.list_pending_requests()


def cleanup_expired_requests() -> int:
    """Clean up expired approval requests."""
    return approval_workflow.cleanup_expired_requests()


# Stage 4 stub class for audit testing
class ApprovalService:
    """Stub service class for Stage 4 audit testing."""

    def __init__(self):
        self.workflow = approval_workflow

    def create_request(self, type: str, payload: Dict, requester: str) -> Optional[ApprovalRequest]:
        """Create approval request through service."""
        return self.workflow.create_request(type, payload, requester)

    def approve_request(self, request_id: str, approver: str, reason: str = "") -> bool:
        """Approve request through service."""
        return self.workflow.approve_request(request_id, approver, reason)
