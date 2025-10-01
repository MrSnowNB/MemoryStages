"""
Stage 5 scope only. Do not implement beyond this file's responsibilities.
Operations dashboard - live monitoring and system health tracking.
"""

import psutil
import os
from typing import Dict, Any, List
from datetime import datetime, timedelta

from src.core import config
from src.core.dao import get_kv_count
from src.core.approval import list_pending_requests
from src.core import db
from util.logging import logger


class SystemHealthMonitor:
    """Monitors system health and provides real-time status information."""

    def __init__(self):
        self._last_refresh = None
        self._cached_status = None
        self._cache_timeout = 5  # seconds

    def get_system_status(self) -> Dict[str, Any]:
        """
        Get comprehensive system health status.

        Returns:
            Dict with system status information
        """
        # Skip cache for integration testing - always get fresh status
        # if self._cached_status and self._is_cache_valid():
        #     return self._cached_status

        status = {
            "timestamp": datetime.now().isoformat(),
            "dashboard": {
                "enabled": os.getenv("DASHBOARD_ENABLED", "false").lower() == "true",
                "type": os.getenv("DASHBOARD_TYPE", "tui")
            },
            "stages": {
                "1_foundation": True,  # Always available
                "2_vector": os.getenv("VECTOR_ENABLED", "false").lower() == "true",
                "3_heartbeat": os.getenv("HEARTBEAT_ENABLED", "false").lower() == "true",
                "4_approval": os.getenv("APPROVAL_ENABLED", "false").lower() == "true"
            },
            "system": {
                "database": self._check_database_health(),
                "memory_usage": self._get_memory_usage(),
                "cpu_usage": psutil.cpu_percent(interval=0.1)
            },
            "features": {
                "kv_operations": True,
                "vector_search": self._check_vector_system(),
                "heartbeat_monitoring": os.getenv("HEARTBEAT_ENABLED", "false").lower() == "true",
                "approval_workflow": os.getenv("APPROVAL_ENABLED", "false").lower() == "true",
                "schema_validation": os.getenv("SCHEMA_VALIDATION_STRICT", "false").lower() == "true",
                "sensitive_data_redaction": True
            },
            "operations": {
                "total_kv_entries": self._safe_get_kv_count(),
                "pending_approvals": self._safe_get_pending_approvals(),
                "health_score": self._calculate_health_score()
            },
            "recent_activity": self._get_recent_activity()
        }

        self._cached_status = status
        self._last_refresh = datetime.now()
        return status

    def get_feature_flags_status(self) -> Dict[str, Any]:
        """
        Get status of all feature flags.

        Returns:
            Dict with feature flag states and interactions
        """
        flags = {
            "dashboard_enabled": config.DASHBOARD_ENABLED,
            "vector_enabled": config.VECTOR_ENABLED,
            "heartbeat_enabled": config.HEARTBEAT_ENABLED,
            "approval_enabled": config.APPROVAL_ENABLED,
            "schema_validation_strict": config.SCHEMA_VALIDATION_STRICT,
            "sensitive_access": os.getenv("DASHBOARD_SENSITIVE_ACCESS", "false").lower() == "true",
            "maintenance_mode": os.getenv("DASHBOARD_MAINTENANCE_MODE", "false").lower() == "true"
        }

        # Add dependency information
        flags["dependencies"] = {
            "heartbeat_requires_vector": config.HEARTBEAT_ENABLED and not config.VECTOR_ENABLED,
            "dashboard_requires_auth_token": config.DASHBOARD_ENABLED and not os.getenv("DASHBOARD_AUTH_TOKEN"),
            "warnings": self._get_flag_warnings(flags)
        }

        return flags

    def get_drift_status(self) -> Dict[str, Any]:
        """
        Get drift detection and correction status.

        Returns:
            Dict with drift detection state
        """
        status = {
            "heartbeat_feature": config.HEARTBEAT_ENABLED,
            "drift_detection_enabled": config.HEARTBEAT_ENABLED,
            "correction_enabled": config.HEARTBEAT_ENABLED and os.getenv("CORRECTION_MODE", "propose") != "off",
            "last_heartbeat": "Not available",  # Would need to track this in a real implementation
            "pending_corrections": 0,  # Would query correction tables
            "drift_findings": []  # Would query drift finding logs
        }

        # Add mode information
        correction_mode = os.getenv("CORRECTION_MODE", "propose")
        status["correction_mode"] = {
            "current": correction_mode,
            "description": {
                "off": "No automatic corrections",
                "propose": "Log corrections, require manual approval",
                "apply": "Automatically apply corrections"
            }.get(correction_mode, "Unknown")
        }

        return status

    def update_monitor_display(self, app) -> None:
        """
        Update the monitoring display in the dashboard.

        Args:
            app: Dashboard app instance to update
        """
        try:
            status = self.get_system_status()

            # Update health indicators
            health_text = f"""● Database: {'✓ Ready' if status['system']['database'] else '✗ Issues'}
● Memory: {status['system']['memory_usage']:.1f}%
● CPU: {status['system']['cpu_usage']:.1f}%
● Stages: {'✓' if all(status['stages'].values()) else '⚠'}"""

            app.query_one("#health-section").query_one("Static.system-health").update(health_text)

            logger.info("Dashboard monitoring display updated")
        except Exception as e:
            logger.error(f"Failed to update monitoring display: {e}")

    def _is_cache_valid(self) -> bool:
        """Check if cached status is still valid."""
        if not self._last_refresh:
            return False
        return (datetime.now() - self._last_refresh).total_seconds() < self._cache_timeout

    def _check_database_health(self) -> bool:
        """Check database connectivity and basic health."""
        try:
            with db.get_db() as connection:  # Use context manager properly
                cursor = connection.cursor()
                cursor.execute("SELECT 1")  # Simple health check
                cursor.fetchone()
                return True
        except Exception as e:
            logger.error(f"Database health check failed: {e}")
            return False

    def _check_vector_system(self) -> bool:
        """Check if vector system is available."""
        try:
            # Try to import and check vector components
            from src.core.config import get_vector_store, get_embedding_provider
            store = get_vector_store()
            provider = get_embedding_provider()
            return store is not None and provider is not None
        except Exception:
            return False

    def _get_memory_usage(self) -> float:
        """Get current memory usage percentage."""
        try:
            return psutil.virtual_memory().percent
        except Exception:
            return 0.0

    def _calculate_health_score(self) -> int:
        """Calculate overall system health score (0-100)."""
        try:
            score = 0

            # Database health (30 points)
            if self._check_database_health():
                score += 30

            # Feature availability (40 points) - Calculate directly to avoid recursion
            features = {
                "kv_operations": True,
                "vector_search": self._check_vector_system(),
                "heartbeat_monitoring": os.getenv("HEARTBEAT_ENABLED", "false").lower() == "true",
                "approval_workflow": os.getenv("APPROVAL_ENABLED", "false").lower() == "true",
                "schema_validation": os.getenv("SCHEMA_VALIDATION_STRICT", "false").lower() == "true",
                "sensitive_data_redaction": True
            }

            feature_points = sum([
                features["kv_operations"] * 15,
                features["vector_search"] * 10,
                features["schema_validation"] * 10,
                features["sensitive_data_redaction"] * 5
            ])
            score += min(feature_points, 40)

            # Memory usage penalty (up to 30 points deduction)
            try:
                memory_usage = self._get_memory_usage()
                memory_penalty = min(memory_usage / 100 * 30, 30)
                score = max(0, score - memory_penalty)
            except (TypeError, ValueError, AttributeError):
                # If memory data is invalid (e.g., mock), skip penalty
                pass

            return int(min(100, max(0, score)))
        except Exception as e:
            logger.error(f"Health score calculation failed: {e}")
            return 0

    def _get_recent_activity(self) -> List[Dict[str, Any]]:
        """Get recent system activity summary."""
        try:
            # Get recent events from episodic table - needs user_id parameter
            from src.core.dao import list_events
            recent_events = list_events(user_id="default", limit=5)

            activity = []
            for event in recent_events:
                if hasattr(event, 'action') and hasattr(event, 'ts'):
                    activity.append({
                        "type": event.action,
                        "timestamp": event.ts.isoformat() if hasattr(event.ts, 'isoformat') else str(event.ts),
                        "description": event.action.replace("_", " ").title()
                    })

            return activity
        except Exception as e:
            logger.error(f"Failed to get recent activity: {e}")
            return [{"type": "error", "timestamp": datetime.now().isoformat(), "description": "Activity monitoring unavailable"}]

    def _safe_get_kv_count(self) -> int:
        """Safely get KV count, return 0 on failure."""
        try:
            return get_kv_count()
        except Exception:
            return 0

    def _safe_get_pending_approvals(self) -> int:
        """Safely get pending approvals count, return 0 on failure."""
        if not config.APPROVAL_ENABLED:
            return 0
        try:
            return len(list_pending_requests())
        except Exception:
            return 0

    def _get_flag_warnings(self, flags: Dict[str, Any]) -> List[str]:
        """Get warnings about feature flag configurations."""
        warnings = []

        if flags["heartbeat_enabled"] and not flags["vector_enabled"]:
            warnings.append("HEARTBEAT_ENABLED requires VECTOR_ENABLED=true")

        if flags["dashboard_enabled"] and not os.getenv("DASHBOARD_AUTH_TOKEN"):
            warnings.append("Dashboard enabled but no auth token configured")

        return warnings


# Global monitor instance
system_monitor = SystemHealthMonitor()


def get_system_status() -> Dict[str, Any]:
    """Get system status information."""
    return system_monitor.get_system_status()


def get_feature_flags_status() -> Dict[str, Any]:
    """Get feature flags status."""
    return system_monitor.get_feature_flags_status()


def get_drift_status() -> Dict[str, Any]:
    """Get drift detection status."""
    return system_monitor.get_drift_status()


def update_monitor_display(app) -> None:
    """Update monitoring display in dashboard."""
    system_monitor.update_monitor_display(app)
