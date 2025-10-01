"""
Stage 5 scope only. Do not implement beyond this file's responsibilities.
Operations dashboard - advanced maintenance tools with safety controls.
"""

import os
import shutil
from datetime import datetime, timedelta
from typing import Dict, Any, List

from src.core.config import DASHBOARD_MAINTENANCE_MODE
from src.core.maintenance import (
    get_maintenance_status,
    schedule_maintenance_task,
    get_backup_schedule
)
from util.logging import logger
from .auth import check_admin_access


class MaintenanceTools:
    """Advanced maintenance tools with safety controls."""

    def __init__(self):
        self._confirmation_tokens = {}  # Store pending confirmation tokens

    def get_maintenance_status(self) -> Dict[str, Any]:
        """
        Get overall maintenance status.

        Returns:
            Dict with maintenance status information
        """
        if not check_admin_access(sensitive_operation=False):
            return {"error": "Access denied"}

        try:
            # Get core maintenance status
            status = get_maintenance_status()

            # Add dashboard-specific maintenance info
            status.update({
                "maintenance_mode": DASHBOARD_MAINTENANCE_MODE,
                "available_tools": [
                    "vector_index_rebuild",
                    "system_backup",
                    "maintenance_scheduling",
                    "integrity_checks"
                ] if DASHBOARD_MAINTENANCE_MODE else [],
                "pending_confirmations": len(self._confirmation_tokens)
            })

            return status

        except Exception as e:
            logger.error(f"Failed to get maintenance status: {e}")
            return {"error": "Maintenance status unavailable"}

    def backup_system_state(self, include_sensitive: bool = False, confirm_token: str = None) -> Dict[str, Any]:
        """
        Create system backup with safety controls.

        Args:
            include_sensitive: Whether to include sensitive data
            confirm_token: Confirmation token for destructive operations

        Returns:
            Dict with backup operation results
        """
        if not check_admin_access(sensitive_operation=include_sensitive):
            return {"success": False, "error": "Access denied"}

        if include_sensitive and not confirm_token:
            # Generate confirmation token for sensitive data backup
            token = f"backup_sensitive_{int(datetime.now().timestamp())}"
            self._confirmation_tokens[token] = {
                "operation": "backup_sensitive",
                "expires": datetime.now() + timedelta(minutes=10),
                "params": {"include_sensitive": True}
            }
            return {
                "success": False,
                "requires_confirmation": True,
                "confirmation_token": token,
                "message": "Sensitive data backup requires explicit confirmation. Token expires in 10 minutes."
            }

        if include_sensitive and confirm_token:
            # Validate confirmation token
            if confirm_token not in self._confirmation_tokens:
                return {"success": False, "error": "Invalid confirmation token"}

            token_info = self._confirmation_tokens[confirm_token]
            if token_info["operation"] != "backup_sensitive" or token_info["expires"] < datetime.now():
                del self._confirmation_tokens[confirm_token]
                return {"success": False, "error": "Expired or invalid confirmation token"}

            # Token valid - clean up and proceed
            del self._confirmation_tokens[confirm_token]

        try:
            # Create backup using core backup functionality
            from src.core.backup import create_backup

            backup_result = create_backup(
                backup_path=f"./backups/backup_{int(datetime.now().timestamp())}",
                include_sensitive=include_sensitive
            )

            logger.info(f"Dashboard backup completed: {backup_result}")

            return {
                "success": backup_result["success"],
                "message": backup_result.get("message", "Backup completed"),
                "backup_path": backup_result.get("backup_path")
            }

        except Exception as e:
            logger.error(f"Backup operation failed: {e}")
            return {"success": False, "error": str(e)}

    def rebuild_vector_index(self, force: bool = False, confirm_token: str = None) -> Dict[str, Any]:
        """
        Rebuild vector index with safety controls.

        Args:
            force: Force rebuild even if not needed
            confirm_token: Confirmation token for forced rebuild

        Returns:
            Dict with rebuild operation results
        """
        if not check_admin_access(sensitive_operation=False):
            return {"success": False, "error": "Access denied"}

        if force and not confirm_token:
            # Generate confirmation token for forced rebuild
            token = f"rebuild_force_{int(datetime.now().timestamp())}"
            self._confirmation_tokens[token] = {
                "operation": "rebuild_force",
                "expires": datetime.now() + timedelta(minutes=10),
                "params": {"force": True}
            }
            return {
                "success": False,
                "requires_confirmation": True,
                "confirmation_token": token,
                "message": "Forced vector rebuild requires explicit confirmation. Token expires in 10 minutes."
            }

        if force and confirm_token:
            # Validate confirmation token
            if confirm_token not in self._confirmation_tokens:
                return {"success": False, "error": "Invalid confirmation token"}

            token_info = self._confirmation_tokens[confirm_token]
            if token_info["operation"] != "rebuild_force" or token_info["expires"] < datetime.now():
                del self._confirmation_tokens[confirm_token]
                return {"success": False, "error": "Expired or invalid confirmation token"}

            # Token valid - clean up and proceed
            del self._confirmation_tokens[confirm_token]

        try:
            # Execute vector index rebuild
            import subprocess

            cmd = ["python", "scripts/rebuild_index.py"]
            if force:
                cmd.append("--force")

            result = subprocess.run(
                cmd,
                capture_output=True,
                text=True,
                timeout=600  # 10 minutes
            )

            success = result.returncode == 0

            logger.info(f"Dashboard vector rebuild completed: return_code={result.returncode}")

            return {
                "success": success,
                "message": "Vector index rebuild completed" if success else f"Rebuild failed: {result.stderr[-200:] if result.stderr else 'unknown error'}",
                "stdout": result.stdout[-1000:] if result.stdout else "",
                "stderr": result.stderr[-1000:] if result.stderr else "",
                "return_code": result.returncode
            }

        except subprocess.TimeoutExpired:
            return {"success": False, "error": "Vector rebuild timed out after 10 minutes"}
        except Exception as e:
            logger.error(f"Vector rebuild operation failed: {e}")
            return {"success": False, "error": str(e)}

    def validate_system_integrity(self) -> Dict[str, Any]:
        """
        Validate system integrity and consistency.

        Returns:
            Dict with integrity check results
        """
        if not check_admin_access(sensitive_operation=False):
            return {"success": False, "error": "Access denied"}

        try:
            # Run integrity checks using core maintenance
            from src.core.maintenance import run_integrity_check

            result = run_integrity_check()

            return {
                "success": result["success"],
                "checks_performed": result.get("checks", []),
                "issues_found": result.get("issues_found", 0),
                "recommendations": result.get("recommendations", []),
                "details": result
            }

        except Exception as e:
            logger.error(f"Integrity check failed: {e}")
            return {"success": False, "error": str(e)}

    def schedule_maintenance_task(self, task_type: str, schedule_time: datetime,
                                  parameters: Dict[str, Any] = None) -> Dict[str, Any]:
        """
        Schedule a maintenance task for future execution.

        Args:
            task_type: Type of maintenance task
            schedule_time: When to execute the task
            parameters: Task-specific parameters

        Returns:
            Dict with scheduling results
        """
        if not check_admin_access(sensitive_operation=False):
            return {"success": False, "error": "Access denied"}

        # Maintenance scheduling requires maintenance mode
        if not DASHBOARD_MAINTENANCE_MODE:
            return {"success": False, "error": "Maintenance mode required for task scheduling"}

        try:
            result = schedule_maintenance_task(
                task_type=task_type,
                schedule_time=schedule_time,
                parameters=parameters or {}
            )

            return {
                "success": result["success"],
                "task_id": result.get("task_id"),
                "message": result.get("message", "Task scheduled")
            }

        except Exception as e:
            logger.error(f"Task scheduling failed: {e}")
            return {"success": False, "error": str(e)}

    def get_maintenance_history(self, limit: int = 20) -> Dict[str, Any]:
        """
        Get maintenance operation history.

        Returns:
            Dict with maintenance history
        """
        if not check_admin_access(sensitive_operation=False):
            return {"error": "Access denied"}

        try:
            # Get maintenance history from core system
            from src.core.maintenance import get_maintenance_history

            history = get_maintenance_history(limit=limit)

            return {
                "history": history,
                "count": len(history)
            }

        except Exception as e:
            logger.error(f"Failed to get maintenance history: {e}")
            return {"error": "Maintenance history unavailable"}

    def cancel_pending_confirmation(self, token: str) -> Dict[str, Any]:
        """
        Cancel a pending confirmation token.

        Args:
            token: Confirmation token to cancel

        Returns:
            Dict with cancellation results
        """
        if token in self._confirmation_tokens:
            del self._confirmation_tokens[token]
            return {"success": True, "message": "Confirmation cancelled"}
        else:
            return {"success": False, "error": "Token not found"}


# Global maintenance tools instance
maintenance_tools = MaintenanceTools()


def get_maintenance_status_info() -> Dict[str, Any]:
    """Get maintenance status information."""
    return maintenance_tools.get_maintenance_status()


def perform_system_backup(include_sensitive: bool = False, confirm_token: str = None) -> Dict[str, Any]:
    """Perform system backup."""
    return maintenance_tools.backup_system_state(include_sensitive, confirm_token)


def perform_vector_rebuild(force: bool = False, confirm_token: str = None) -> Dict[str, Any]:
    """Perform vector index rebuild."""
    return maintenance_tools.rebuild_vector_index(force, confirm_token)


def perform_integrity_check() -> Dict[str, Any]:
    """Perform system integrity check."""
    return maintenance_tools.validate_system_integrity()


def get_maintenance_operation_history(limit: int = 20) -> Dict[str, Any]:
    """Get maintenance operation history."""
    return maintenance_tools.get_maintenance_history(limit)


def cancel_confirmation_token(token: str) -> Dict[str, Any]:
    """Cancel a pending confirmation token."""
    return maintenance_tools.cancel_pending_confirmation(token)
