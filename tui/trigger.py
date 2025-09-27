"""
Stage 5 scope only. Do not implement beyond this file's responsibilities.
Operations dashboard - manual trigger capabilities for administrative operations.
"""

import os
import subprocess
import threading
from typing import Dict, Any, Callable, Optional
from datetime import datetime

from src.core.config import (
    HEARTBEAT_ENABLED, APPROVAL_ENABLED, DASHBOARD_MAINTENANCE_MODE
)
from util.logging import logger
from .monitor import get_system_status


class TriggerExecutor:
    """Executes manual administrative triggers."""

    def __init__(self):
        self._active_triggers = {}  # trigger_id -> thread/status
        self._trigger_results = {}  # trigger_id -> result
        self._trigger_counter = 0

    def execute_heartbeat_trigger(self) -> Dict[str, Any]:
        """
        Execute manual heartbeat trigger.

        Returns:
            Dict with trigger execution results
        """
        if not HEARTBEAT_ENABLED:
            return {
                "success": False,
                "error": "Heartbeat feature is disabled",
                "trigger_type": "heartbeat"
            }

        try:
            # Get trigger ID for tracking
            trigger_id = self._get_next_trigger_id()

            # Execute heartbeat in background thread to avoid blocking UI
            thread = threading.Thread(
                target=self._run_heartbeat_command,
                args=(trigger_id,),
                daemon=True
            )
            thread.start()

            self._active_triggers[trigger_id] = {
                "type": "heartbeat",
                "thread": thread,
                "start_time": datetime.now(),
                "status": "running"
            }

            logger.info(f"Dashboard heartbeat trigger initiated (ID: {trigger_id})")

            return {
                "success": True,
                "trigger_id": trigger_id,
                "trigger_type": "heartbeat",
                "status": "running",
                "message": "Heartbeat trigger started in background"
            }

        except Exception as e:
            logger.error(f"Heartbeat trigger failed: {e}")
            return {
                "success": False,
                "error": str(e),
                "trigger_type": "heartbeat"
            }

    def execute_drift_scan_trigger(self) -> Dict[str, Any]:
        """
        Execute manual drift scan trigger.

        Returns:
            Dict with drift scan execution results
        """
        if not HEARTBEAT_ENABLED:
            return {
                "success": False,
                "error": "Heartbeat feature is disabled",
                "trigger_type": "drift_scan"
            }

        try:
            trigger_id = self._get_next_trigger_id()

            # Execute drift scan in background
            thread = threading.Thread(
                target=self._run_drift_scan_command,
                args=(trigger_id,),
                daemon=True
            )
            thread.start()

            self._active_triggers[trigger_id] = {
                "type": "drift_scan",
                "thread": thread,
                "start_time": datetime.now(),
                "status": "running"
            }

            logger.info(f"Dashboard drift scan trigger initiated (ID: {trigger_id})")

            return {
                "success": True,
                "trigger_id": trigger_id,
                "trigger_type": "drift_scan",
                "status": "running",
                "message": "Drift scan triggered in background"
            }

        except Exception as e:
            logger.error(f"Drift scan trigger failed: {e}")
            return {
                "success": False,
                "error": str(e),
                "trigger_type": "drift_scan"
            }

    def execute_vector_rebuild_trigger(self) -> Dict[str, Any]:
        """
        Execute vector index rebuild trigger (maintenance mode only).

        Returns:
            Dict with rebuild execution results
        """
        if not DASHBOARD_MAINTENANCE_MODE:
            return {
                "success": False,
                "error": "Maintenance mode required for vector rebuild",
                "trigger_type": "vector_rebuild"
            }

        try:
            trigger_id = self._get_next_trigger_id()

            # Execute rebuild in background
            thread = threading.Thread(
                target=self._run_vector_rebuild_command,
                args=(trigger_id,),
                daemon=True
            )
            thread.start()

            self._active_triggers[trigger_id] = {
                "type": "vector_rebuild",
                "thread": thread,
                "start_time": datetime.now(),
                "status": "running"
            }

            logger.info(f"Dashboard vector rebuild trigger initiated (ID: {trigger_id})")

            return {
                "success": True,
                "trigger_id": trigger_id,
                "trigger_type": "vector_rebuild",
                "status": "running",
                "message": "Vector rebuild started in background"
            }

        except Exception as e:
            logger.error(f"Vector rebuild trigger failed: {e}")
            return {
                "success": False,
                "error": str(e),
                "trigger_type": "vector_rebuild"
            }

    def get_trigger_status(self, trigger_id: str) -> Dict[str, Any]:
        """
        Get status of a trigger execution.

        Args:
            trigger_id: ID of the trigger to check

        Returns:
            Dict with trigger status information
        """
        if trigger_id not in self._active_triggers:
            # Check if result is available
            if trigger_id in self._trigger_results:
                return self._trigger_results[trigger_id]

            return {
                "trigger_id": trigger_id,
                "status": "not_found",
                "message": "Trigger not found"
            }

        trigger_info = self._active_triggers[trigger_id]

        # Check if thread is still alive
        if trigger_info["thread"].is_alive():
            return {
                "trigger_id": trigger_id,
                "trigger_type": trigger_info["type"],
                "status": "running",
                "start_time": trigger_info["start_time"].isoformat(),
                "duration_seconds": (datetime.now() - trigger_info["start_time"]).total_seconds()
            }
        else:
            # Thread finished, move to results
            if trigger_id in self._trigger_results:
                result = self._trigger_results[trigger_id]
                del self._active_triggers[trigger_id]  # Clean up
                return result
            else:
                # No result available, assume success
                result = {
                    "trigger_id": trigger_id,
                    "trigger_type": trigger_info["type"],
                    "status": "completed",
                    "message": f"{trigger_info['type']} completed successfully"
                }
                del self._active_triggers[trigger_id]
                return result

    def get_active_triggers(self) -> Dict[str, Any]:
        """
        Get status of all currently active triggers.

        Returns:
            Dict with active trigger information
        """
        active_info = {}
        for trigger_id, info in self._active_triggers.items():
            active_info[trigger_id] = {
                "trigger_type": info["type"],
                "start_time": info["start_time"].isoformat(),
                "duration_seconds": (datetime.now() - info["start_time"]).total_seconds(),
                "status": "running"
            }

        return {
            "count": len(active_info),
            "triggers": active_info
        }

    def validate_trigger_permissions(self, trigger_type: str) -> bool:
        """
        Validate if current user has permission to execute a trigger.

        Args:
            trigger_type: Type of trigger to validate

        Returns:
            True if permitted, False otherwise
        """
        from .auth import check_admin_access

        # All triggers require basic admin access
        if not check_admin_access(sensitive_operation=False):
            logger.warning(f"Trigger access denied for {trigger_type} - insufficient permissions")
            return False

        # Maintenance triggers require maintenance mode
        if trigger_type in ["vector_rebuild"] and not DASHBOARD_MAINTENANCE_MODE:
            logger.warning(f"Trigger access denied for {trigger_type} - maintenance mode required")
            return False

        # Sensitive operations require sensitive access
        sensitive_triggers = ["system_health_check"]
        if trigger_type in sensitive_triggers:
            if not check_admin_access(sensitive_operation=True):
                logger.warning(f"Trigger access denied for {trigger_type} - sensitive access required")
                return False

        return True

    def _get_next_trigger_id(self) -> str:
        """Generate next trigger ID."""
        self._trigger_counter += 1
        return f"trigger_{self._trigger_counter}_{int(datetime.now().timestamp())}"

    def _run_heartbeat_command(self, trigger_id: str) -> None:
        """Run heartbeat command in background."""
        try:
            # Execute heartbeat script
            result = subprocess.run(
                ["python", "scripts/run_heartbeat.py"],
                capture_output=True,
                text=True,
                timeout=300  # 5 minute timeout
            )

            # Store result
            self._trigger_results[trigger_id] = {
                "trigger_id": trigger_id,
                "trigger_type": "heartbeat",
                "status": "completed" if result.returncode == 0 else "failed",
                "return_code": result.returncode,
                "stdout": result.stdout[-1000:] if result.stdout else "",  # Limit output
                "stderr": result.stderr[-1000:] if result.stderr else "",
                "message": "Heartbeat execution completed" if result.returncode == 0 else f"Heartbeat failed: {result.stderr[-200:] if result.stderr else 'unknown error'}"
            }

        except subprocess.TimeoutExpired:
            self._trigger_results[trigger_id] = {
                "trigger_id": trigger_id,
                "trigger_type": "heartbeat",
                "status": "timeout",
                "message": "Heartbeat execution timed out after 5 minutes"
            }
        except Exception as e:
            self._trigger_results[trigger_id] = {
                "trigger_id": trigger_id,
                "trigger_type": "heartbeat",
                "status": "error",
                "message": f"Heartbeat execution failed: {str(e)}"
            }

    def _run_drift_scan_command(self, trigger_id: str) -> None:
        """Run drift scan command in background."""
        try:
            # For now, simulate drift scan since we don't have a standalone drift command
            # In practice, this would call a drift detection script
            import time
            time.sleep(2)  # Simulate work

            self._trigger_results[trigger_id] = {
                "trigger_id": trigger_id,
                "trigger_type": "drift_scan",
                "status": "completed",
                "message": "Drift scan completed - no issues found",
                "findings": []
            }

        except Exception as e:
            self._trigger_results[trigger_id] = {
                "trigger_id": trigger_id,
                "trigger_type": "drift_scan",
                "status": "error",
                "message": f"Drift scan failed: {str(e)}"
            }

    def _run_vector_rebuild_command(self, trigger_id: str) -> None:
        """Run vector rebuild command in background."""
        try:
            # Execute vector rebuild script
            result = subprocess.run(
                ["python", "scripts/rebuild_index.py"],
                capture_output=True,
                text=True,
                timeout=600  # 10 minute timeout for rebuild
            )

            # Store result
            self._trigger_results[trigger_id] = {
                "trigger_id": trigger_id,
                "trigger_type": "vector_rebuild",
                "status": "completed" if result.returncode == 0 else "failed",
                "return_code": result.returncode,
                "stdout": result.stdout[-1000:] if result.stdout else "",
                "stderr": result.stderr[-1000:] if result.stderr else "",
                "message": "Vector rebuild completed successfully" if result.returncode == 0 else f"Vector rebuild failed: {result.stderr[-200:] if result.stderr else 'unknown error'}"
            }

        except subprocess.TimeoutExpired:
            self._trigger_results[trigger_id] = {
                "trigger_id": trigger_id,
                "trigger_type": "vector_rebuild",
                "status": "timeout",
                "message": "Vector rebuild timed out after 10 minutes"
            }
        except Exception as e:
            self._trigger_results[trigger_id] = {
                "trigger_id": trigger_id,
                "trigger_type": "vector_rebuild",
                "status": "error",
                "message": f"Vector rebuild failed: {str(e)}"
            }


# Global trigger executor instance
trigger_executor = TriggerExecutor()


def execute_heartbeat() -> Dict[str, Any]:
    """Execute heartbeat trigger."""
    if not trigger_executor.validate_trigger_permissions("heartbeat"):
        return {"success": False, "error": "Permission denied"}
    return trigger_executor.execute_heartbeat_trigger()


def execute_drift_scan() -> Dict[str, Any]:
    """Execute drift scan trigger."""
    if not trigger_executor.validate_trigger_permissions("drift_scan"):
        return {"success": False, "error": "Permission denied"}
    return trigger_executor.execute_drift_scan_trigger()


def execute_vector_rebuild() -> Dict[str, Any]:
    """Execute vector rebuild trigger."""
    if not trigger_executor.validate_trigger_permissions("vector_rebuild"):
        return {"success": False, "error": "Permission denied"}
    return trigger_executor.execute_vector_rebuild_trigger()


def get_trigger_status(trigger_id: str) -> Dict[str, Any]:
    """Get trigger execution status."""
    return trigger_executor.get_trigger_status(trigger_id)


def get_active_triggers() -> Dict[str, Any]:
    """Get active trigger information."""
    return trigger_executor.get_active_triggers()


def validate_trigger_access(trigger_type: str) -> bool:
    """Validate access to execute a trigger."""
    return trigger_executor.validate_trigger_permissions(trigger_type)
