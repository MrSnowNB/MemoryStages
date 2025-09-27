"""
Stage 3 scope only. Do not implement beyond this file's responsibilities.
Heartbeat and drift correction - maintains vector overlay consistency with canonical SQLite.
"""

import logging
from datetime import datetime
from typing import Any, Dict, List

class StructuredLogger:
    """Structured logger for operations including Stage 3 heartbeat/drift/correction."""
    
    def __init__(self, name: str = "memory_scaffold"):
        self.logger = logging.getLogger(name)
        self.logger.setLevel(logging.INFO)
        
        # Create handler if not already set
        if not self.logger.handlers:
            handler = logging.StreamHandler()
            formatter = logging.Formatter(
                '%(asctime)s - %(name)s - %(levelname)s - %(message)s'
            )
            handler.setFormatter(formatter)
            self.logger.addHandler(handler)
    
    def log_operation(self, operation: str, status: str, details: Dict[str, Any] = None):
        """Log a structured operation."""
        message = f"Operation: {operation}, Status: {status}"
        if details:
            message += f", Details: {details}"
        
        self.logger.info(message)
    
    def log_kv_operation(self, operation: str, key: str, value: str = None, status: str = "success"):
        """Log a KV-specific operation."""
        details = {"key": key}
        if value is not None:
            details["value"] = value[:50] + "..." if len(value) > 50 else value
            
        self.log_operation(f"KV.{operation}", status, details)
    
    def log_episodic_event(self, actor: str, action: str, payload: str = None, status: str = "success"):
        """Log an episodic event."""
        details = {"actor": actor, "action": action}
        if payload is not None:
            details["payload"] = payload[:50] + "..." if len(payload) > 50 else payload

        self.log_operation("episodic", status, details)

    def log_vector_operation(self, operation: str, record_id: str, details: Dict[str, Any] = None, status: str = "success"):
        """Log a vector operation."""
        log_details = {"record_id": record_id}
        if details:
            log_details.update(details)

        self.log_operation(f"vector.{operation}", status, log_details)

    def log_heartbeat_task(self, task_name: str, start_time: float, end_time: float, status: str = "success", details: Dict[str, Any] = None):
        """Log heartbeat task execution."""
        duration_ms = round((end_time - start_time) * 1000, 2)
        log_details = {"duration_ms": duration_ms}
        if details:
            log_details.update(details)
        elif status == "success":
            log_details["message"] = f"Heartbeat task '{task_name}' completed in {duration_ms}ms"
        elif status == "failed":
            log_details["message"] = f"Heartbeat task '{task_name}' failed after {duration_ms}ms"

        self.log_operation(f"heartbeat.{task_name}", status, log_details)

    def log_drift_finding(self, finding_type: str, severity: str, kv_key: str, details: Dict[str, Any] = None):
        """Log drift detection findings."""
        log_details = {
            "finding_type": finding_type,
            "severity": severity,
            "kv_key": kv_key
        }
        if details:
            log_details.update(details)

        self.log_operation("drift.finding", "detected", log_details)

    def log_correction_proposal(self, plan_id: str, findings_count: int, actions_count: int, details: Dict[str, Any] = None):
        """Log correction plan proposal."""
        log_details = {
            "plan_id": plan_id,
            "findings_count": findings_count,
            "actions_count": actions_count,
            "mode": "propose"
        }
        if details:
            log_details.update(details)

        self.log_operation("correction.proposed", "success", log_details)

    def log_correction_application(self, plan_id: str, actions_count: int, status: str = "success", details: Dict[str, Any] = None):
        """Log correction plan execution."""
        log_details = {
            "plan_id": plan_id,
            "actions_count": actions_count,
            "mode": "apply"
        }
        if details:
            log_details.update(details)

        self.log_operation("correction.applied", status, log_details)

    def log_correction_reversal(self, plan_id: str, status: str = "success", details: Dict[str, Any] = None):
        """Log correction plan reversal."""
        log_details = {"plan_id": plan_id}
        if details:
            log_details.update(details)

        self.log_operation("correction.reverted", status, log_details)

# Global logger instance
logger = StructuredLogger()
