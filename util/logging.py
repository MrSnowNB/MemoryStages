"""
Stage 4 scope only. Do not implement beyond this file's responsibilities.
Approval workflows and schema validation - ensures data integrity and auditability.
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

    # Schema Validation Audit Logging (Stage 4)
    def log_schema_validation_success(self, operation: str, target_identifier: str, validation_level: str = "strict", source: str = "api"):
        """Log successful schema validation."""
        log_details = {
            "operation": operation,
            "target_identifier": target_identifier,
            "validation_level": validation_level,
            "source": source
        }
        self.log_operation("schema_validation.success", "validated", log_details)

    def log_schema_validation_error(self, operation: str, errors: List[Any], source_record: Dict[str, Any] = None):
        """Log schema validation errors with sanitized details."""
        # Sanitize error details to avoid leaking sensitive information
        sanitized_errors = []
        for error in errors:
            if isinstance(error, dict):
                sanitized_error = error.copy()
                # Remove any field values that might contain sensitive data
                for field in ['field_values', 'value']:
                    if field in sanitized_error:
                        sanitized_error[field] = "[REDACTED]"
                sanitized_errors.append(sanitized_error)
            else:
                sanitized_errors.append(str(error)[:100])  # Limit error message length

        log_details = {
            "operation": operation,
            "errors": sanitized_errors,
            "error_count": len(sanitized_errors)
        }

        if source_record:
            # Only log identifiers, not sensitive values
            if "key" in source_record:
                log_details["target_identifier"] = source_record["key"]

        self.log_operation("schema_validation.error", "rejected", log_details)

    # Approval Workflow Audit Logging (Stage 4)
    def log_approval_request(self, request_id: str, request_type: str, requester: str):
        """Log approval request creation."""
        log_details = {
            "request_id": request_id,
            "request_type": request_type,
            "requester": requester
        }
        self.log_operation("approval.request_created", "pending", log_details)

    def log_approval_decision(self, request_id: str, decision: str, approver: str, reason: str = ""):
        """Log approval decision."""
        log_details = {
            "request_id": request_id,
            "decision": decision,
            "approver": approver,
            "reason": reason[:100] if reason else ""  # Limit reason length
        }
        status = "approved" if decision == "approved" else "rejected"
        self.log_operation("approval.decision", status, log_details)

    def log_approval_bypass(self, request_id: str, reason: str = "system_config"):
        """Log approval bypass."""
        log_details = {
            "request_id": request_id,
            "reason": reason
        }
        self.log_operation("approval.bypass", "allowed", log_details)

    # Correction Operation Audit Logging (Stage 4)
    def log_correction_applied(self, correction_id: str, correction_type: str, target_key: str, drift_finding_id: str, success: bool = True, metadata: Dict[str, Any] = None):
        """Log correction application."""
        log_details = {
            "correction_id": correction_id,
            "correction_type": correction_type,
            "target_key": target_key,
            "drift_finding_id": drift_finding_id,
            "success": success
        }
        if metadata:
            # Sanitize metadata
            sanitized_metadata = {}
            for k, v in metadata.items():
                if k in ['reason', 'severity']:
                    sanitized_metadata[k] = v  # Safe fields
                elif isinstance(v, str) and len(v) > 50:
                    sanitized_metadata[k] = v[:47] + "..."  # Truncate long values
                else:
                    sanitized_metadata[k] = v
            log_details["metadata"] = sanitized_metadata

        status = "success" if success else "failed"
        self.log_operation("correction.applied", status, log_details)

    def log_correction_blocked(self, correction_id: str, correction_type: str, target_key: str, block_reason: str, approval_request_id: str = None):
        """Log correction blocking due to approval or validation."""
        log_details = {
            "correction_id": correction_id,
            "correction_type": correction_type,
            "target_key": target_key,
            "block_reason": block_reason
        }
        if approval_request_id:
            log_details["approval_request_id"] = approval_request_id

        self.log_operation("correction.blocked", "waiting", log_details)

    # Standard logging methods for compatibility
    def info(self, message: str) -> None:
        """Log an info message."""
        self.logger.info(message)

    def warning(self, message: str) -> None:
        """Log a warning message."""
        self.logger.warning(message)

    def error(self, message: str) -> None:
        """Log an error message."""
        self.logger.error(message)

    def debug(self, message: str) -> None:
        """Log a debug message."""
        self.logger.debug(message)

# Global logger instance
logger = StructuredLogger()

# Export audit functions for external use (Stage 4)
def log_schema_validation_success(operation: str, target_identifier: str, validation_level: str = "strict", source: str = "api"):
    """Log successful schema validation."""
    logger.log_schema_validation_success(operation, target_identifier, validation_level, source)

def log_approval_request(request_id: str, request_type: str, requester: str):
    """Log approval request creation."""
    logger.log_approval_request(request_id, request_type, requester)

def log_approval_decision(request_id: str, decision: str, approver: str, reason: str = ""):
    """Log approval decision."""
    logger.log_approval_decision(request_id, decision, approver, reason)

def log_correction_applied(correction_id: str, correction_type: str, target_key: str, drift_finding_id: str, success: bool = True, metadata: Dict[str, Any] = None):
    """Log correction application."""
    logger.log_correction_applied(correction_id, correction_type, target_key, drift_finding_id, success, metadata)

def log_correction_blocked(correction_id: str, correction_type: str, target_key: str, block_reason: str, approval_request_id: str = None):
    """Log correction blocking due to approval or validation."""
    logger.log_correction_blocked(correction_id, correction_type, target_key, block_reason, approval_request_id)

def log_schema_validation_error(operation: str, errors: List[Any], source_record: Dict[str, Any] = None):
    """Log schema validation errors with sanitized details."""
    logger.log_schema_validation_error(operation, errors, source_record)

# General audit event function (Stage 4)
def audit_event(event_type: str, identifiers: Dict[str, Any], payload: Dict[str, Any] = None, sensitive_fields: List[str] = None):
    """General audit event logging with privacy controls."""
    # Auto-sanitize sensitive fields if not specified
    if sensitive_fields is None:
        sensitive_fields = ['value', 'data', 'payload', 'content', 'secret', 'password']

    log_details = identifiers.copy() if identifiers else {}

    if payload:
        sanitized_payload = {}
        for k, v in payload.items():
            if k not in sensitive_fields:
                # Truncate long values and sanitize
                if isinstance(v, str) and len(v) > 100:
                    sanitized_payload[k] = v[:97] + "..."
                else:
                    sanitized_payload[k] = v
            else:
                sanitized_payload[k] = "[REDACTED]"
        log_details["payload"] = sanitized_payload

    # Determine operation type from event_type
    if event_type.startswith("approval"):
        operation = "approval"
    elif event_type.startswith("schema"):
        operation = "validation"
    elif event_type.startswith("correction"):
        operation = "correction"
    else:
        operation = event_type.replace(".", "_")

    logger.log_operation(operation, "audit", log_details)

# Payload sanitization utility (Stage 4)
def sanitize_payload(payload: Any, reveal_sensitive: bool = False, sensitive_fields: List[str] = None) -> Any:
    """Sanitize payloads for audit logging."""
    if sensitive_fields is None:
        sensitive_fields = ['value', 'data', 'payload', 'content', 'secret', 'password']

    if isinstance(payload, dict):
        sanitized = {}
        for k, v in payload.items():
            if reveal_sensitive or k not in sensitive_fields:
                sanitized[k] = sanitize_payload(v, reveal_sensitive, sensitive_fields)
            else:
                sanitized[k] = "[REDACTED]"
        return sanitized
    elif isinstance(payload, str):
        # Truncate long strings
        return payload[:100] + "..." if len(payload) > 100 else payload
    elif isinstance(payload, list):
        return [sanitize_payload(item, reveal_sensitive, sensitive_fields) for item in payload]
    else:
        return payload
