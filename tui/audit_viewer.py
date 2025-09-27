"""
Stage 5 scope only. Do not implement beyond this file's responsibilities.
Operations dashboard - audit log viewer with privacy controls and search capabilities.
"""

import re
from datetime import datetime, timedelta
from typing import Dict, Any, List, Optional, Tuple
from dataclasses import dataclass

from src.core.dao import list_events
from util.logging import sanitize_payload, logger
from .auth import check_admin_access


@dataclass
class AuditSearchCriteria:
    """Search criteria for audit log filtering."""
    start_date: Optional[datetime] = None
    end_date: Optional[datetime] = None
    actor: Optional[str] = None
    operation: Optional[str] = None
    search_text: Optional[str] = None
    status: Optional[str] = None
    limit: int = 50
    offset: int = 0


@dataclass
class AuditEvent:
    """Processed audit event for display."""
    id: int
    actor: str
    action: str
    data: str
    ts: datetime
    operation_type: str
    status: str
    details: Dict[str, Any]
    is_sensitive: bool
    requested_reveal: bool = False


class AuditLogViewer:
    """Audit log viewer with privacy controls and search functionality."""

    def __init__(self):
        self._sensitive_fields = {
            'value', 'data', 'payload', 'content', 'secret', 'password',
            'token', 'auth_token', 'api_key', 'private_key', 'access_token'
        }
        self._max_results = 1000  # Prevent excessive memory usage

    def search_events(self, criteria: AuditSearchCriteria) -> Tuple[List[AuditEvent], int]:
        """
        Search audit events based on criteria.

        Returns:
            Tuple of (filtered_events, total_count)
        """
        # Validate admin access for audit log viewing
        if not check_admin_access(sensitive_operation=False):
            logger.warning("Audit log access denied - insufficient permissions")
            return [], 0

        try:
            # Get raw events from database
            raw_events = list_events(limit=self._max_results)

            # Apply search criteria
            filtered_events = self._apply_search_criteria(raw_events, criteria)

            # Convert to AuditEvent objects with privacy controls
            audit_events = []
            for event in filtered_events[criteria.offset:criteria.offset + criteria.limit]:
                audit_event = self._process_event_for_display(event)
                audit_events.append(audit_event)

            return audit_events, len(filtered_events)

        except Exception as e:
            logger.error(f"Audit search failed: {e}")
            return [], 0

    def get_recent_events(self, limit: int = 10) -> List[AuditEvent]:
        """
        Get recent events for overview display.

        Args:
            limit: Number of recent events to return

        Returns:
            List of recent audit events
        """
        criteria = AuditSearchCriteria(
            limit=limit,
            end_date=datetime.now(),
            start_date=datetime.now() - timedelta(hours=24)  # Last 24 hours
        )

        events, _ = self.search_events(criteria)
        return events

    def get_event_details(self, event_id: int, reveal_sensitive: bool = False) -> Optional[AuditEvent]:
        """
        Get detailed view of a specific event.

        Args:
            event_id: Database ID of the event
            reveal_sensitive: Whether to reveal sensitive data (requires permission)

        Returns:
            AuditEvent with full details, or None if not found/permitted
        """
        # Check permissions for sensitive data access
        if reveal_sensitive and not check_admin_access(sensitive_operation=True):
            logger.warning(f"Sensitive audit data access denied for event {event_id}")
            reveal_sensitive = False

        try:
            # Get all events (inefficient but necessary for lookup by ID)
            raw_events = list_events(limit=self._max_results)
            target_event = next((e for e in raw_events if e.id == event_id), None)

            if not target_event:
                return None

            audit_event = self._process_event_for_display(target_event)
            audit_event.requested_reveal = reveal_sensitive

            return audit_event

        except Exception as e:
            logger.error(f"Failed to get event details for ID {event_id}: {e}")
            return None

    def get_audit_summary(self) -> Dict[str, Any]:
        """
        Get audit log summary statistics.

        Returns:
            Dict with summary statistics
        """
        try:
            all_events = list_events(limit=self._max_results)
            total_events = len(all_events)

            # Calculate time-based statistics
            now = datetime.now()
            last_24h = [e for e in all_events if (now - e.ts).total_seconds() < 86400]
            last_hour = [e for e in all_events if (now - e.ts).total_seconds() < 3600]

            # Operation type distribution
            operations = {}
            actors = {}
            statuses = {}

            for event in all_events:
                op_type = self._classify_operation(event.action)
                operations[op_type] = operations.get(op_type, 0) + 1
                actors[event.actor] = actors.get(event.actor, 0) + 1
                statuses[event.action.split('.')[-1]] = statuses.get(event.action.split('.')[-1], 0) + 1

            return {
                "total_events": total_events,
                "last_24h_count": len(last_24h),
                "last_hour_count": len(last_hour),
                "operation_types": dict(sorted(operations.items(), key=lambda x: x[1], reverse=True)),
                "top_actors": dict(list(sorted(actors.items(), key=lambda x: x[1], reverse=True))[:10]),
                "status_distribution": dict(sorted(statuses.items(), key=lambda x: x[1], reverse=True)),
                "sensitive_events": sum(1 for e in all_events if self._is_event_sensitive(e))
            }

        except Exception as e:
            logger.error(f"Failed to generate audit summary: {e}")
            return {"error": "Audit summary unavailable"}

    def _apply_search_criteria(self, events: List[Any], criteria: AuditSearchCriteria) -> List[Any]:
        """Apply search criteria to filter events."""
        filtered = events

        # Date range filtering
        if criteria.start_date:
            filtered = [e for e in filtered if e.ts >= criteria.start_date]
        if criteria.end_date:
            filtered = [e for e in filtered if e.ts <= criteria.end_date]

        # Actor filtering (case-insensitive)
        if criteria.actor:
            filtered = [e for e in filtered if criteria.actor.lower() in e.actor.lower()]

        # Operation filtering
        if criteria.operation:
            filtered = [e for e in filtered if criteria.operation.lower() in e.action.lower()]

        # Full-text search
        if criteria.search_text:
            search_lower = criteria.search_text.lower()
            filtered = [e for e in filtered if
                       search_lower in str(e.data).lower() or
                       search_lower in e.action.lower() or
                       search_lower in e.actor.lower()]

        # Status filtering (extract from action)
        if criteria.status:
            filtered = [e for e in filtered if criteria.status.lower() == e.action.split('.')[-1].lower()]

        return filtered

    def _process_event_for_display(self, raw_event: Any) -> AuditEvent:
        """Process raw database event into display-friendly format."""
        # Classify operation type
        operation_type = self._classify_operation(raw_event.action)

        # Determine if event contains sensitive data
        is_sensitive = self._is_event_sensitive(raw_event)

        # Get the data - from payload dict or data attribute
        if hasattr(raw_event, 'payload') and isinstance(raw_event.payload, dict):
            # Real EpisodicEvent from database
            event_data = str(raw_event.payload)
            details = raw_event.payload
        elif hasattr(raw_event, 'data'):
            # Test mock event
            event_data = raw_event.data if isinstance(raw_event.data, str) else str(raw_event.data)
            # Parse details field if available
            details = {}
            try:
                if raw_event.data:
                    # Try to extract structured data if present
                    import json
                    if '{' in raw_event.data and '}' in raw_event.data:
                        details_start = raw_event.data.find('{')
                        details_end = raw_event.data.rfind('}') + 1
                        if details_start >= 0 and details_end > details_start:
                            details_str = raw_event.data[details_start:details_end]
                            try:
                                details = json.loads(details_str)
                            except:
                                pass
            except Exception:
                # If parsing fails, details remain empty
                pass
        else:
            event_data = ""
            details = {}

        # Process event data for display
        processed_data = self._process_event_data(event_data)

        # Extract status from action
        status = self._extract_status(raw_event.action)

        return AuditEvent(
            id=raw_event.id,
            actor=raw_event.actor,
            action=raw_event.action,
            data=processed_data,
            ts=raw_event.ts,
            operation_type=operation_type,
            status=status,
            details=details,
            is_sensitive=is_sensitive
        )

    def _process_event_data(self, raw_data: str) -> str:
        """Process event data for safe display."""
        if not raw_data:
            return "No data"

        # Truncate very long entries
        if len(raw_data) > 500:
            raw_data = raw_data[:497] + "..."

        # Auto-redact sensitive information unless explicit reveal
        for field in self._sensitive_fields:
            pattern = rf'"{field}"\s*:\s*"[^"]*"'
            raw_data = re.sub(pattern, f'"{field}": "[REDACTED]"', raw_data, flags=re.IGNORECASE)

            # Also redact in other formats like key=value
            pattern = rf'\b{field}\b\s*=\s*[^\s,)]+'
            raw_data = re.sub(pattern, f'{field}=[REDACTED]', raw_data, flags=re.IGNORECASE)

        return raw_data

    def _classify_operation(self, action: str) -> str:
        """Classify operation type from action string."""
        action_lower = action.lower()

        if 'kv.' in action_lower:
            return 'key-value'
        elif 'vector.' in action_lower:
            return 'vector'
        elif 'approval.' in action_lower:
            return 'approval'
        elif 'schema.' in action_lower:
            return 'validation'
        elif 'correction.' in action_lower:
            return 'correction'
        elif 'drift.' in action_lower:
            return 'drift'
        elif 'dashboard.' in action_lower:
            return 'dashboard'
        else:
            return 'other'

    def _extract_status(self, action: str) -> str:
        """Extract status from action string."""
        # Extract the last part after the final dot
        parts = action.split('.')
        if len(parts) > 1:
            status = parts[-1].lower()
            if status in ['success', 'failure', 'error', 'warning', 'info']:
                return status

        return 'unknown'

    def _is_event_sensitive(self, event: Any) -> bool:
        """Determine if an event contains sensitive data."""
        data_str = str(event.data).lower()

        # Check for sensitive field patterns
        for field in self._sensitive_fields:
            if field in data_str:
                return True

        # Check for tokens, keys, or secrets in the data
        sensitive_indicators = ['Bearer', 'Token', 'Password', 'Secret', 'Auth', 'Credential']
        return any(indicator.lower() in data_str for indicator in sensitive_indicators)


# Global audit viewer instance
audit_viewer = AuditLogViewer()


def search_audit_events(criteria: AuditSearchCriteria) -> Tuple[List[AuditEvent], int]:
    """Search audit events."""
    return audit_viewer.search_events(criteria)


def get_recent_audit_events(limit: int = 10) -> List[AuditEvent]:
    """Get recent audit events."""
    return audit_viewer.get_recent_events(limit)


def get_audit_event_details(event_id: int, reveal_sensitive: bool = False) -> Optional[AuditEvent]:
    """Get detailed audit event."""
    return audit_viewer.get_event_details(event_id, reveal_sensitive)


def get_audit_summary() -> Dict[str, Any]:
    """Get audit summary statistics."""
    return audit_viewer.get_audit_summary()
