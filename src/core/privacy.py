"""
Stage 6 scope only. Do not implement beyond this file's responsibilities.
Privacy, backup, and maintenance - ensures data protection and system integrity.
"""

from dataclasses import dataclass
from datetime import datetime
from typing import Dict, Any, Optional, List
import logging

from util.logging import audit_event, sanitize_payload
from .dao import get_key, list_keys
from .db import get_db
from .config import VERSION

logger = logging.getLogger(__name__)


@dataclass
class SensitiveDataAccess:
    """Record of sensitive data access for compliance auditing."""
    timestamp: datetime
    accessor: str
    data_type: str
    access_reason: str
    access_level: str  # read, reveal, export
    audit_logged: bool = False


class PrivacyEnforcer:
    """Centralized privacy enforcement and audit system."""

    def __init__(self):
        self._privacy_enabled = False
        self._privacy_audit_level = "standard"

    def configure(self, enabled: bool = False, audit_level: str = "standard"):
        """Enable/disable privacy enforcement."""
        self._privacy_enabled = enabled
        self._privacy_audit_level = audit_level

        if enabled:
            logger.info(f"Privacy enforcement enabled with {audit_level} audit level")
            self._log_privacy_activation()
        else:
            logger.info("Privacy enforcement disabled")

    def validate_sensitive_access(self, accessor: str, data_type: str, reason: str) -> bool:
        """
        Validate and log sensitive data access requests.

        Args:
            accessor: Identity of the requester (e.g. 'dashboard', 'api', 'system')
            data_type: Type of data being accessed (e.g. 'kv_record', 'audit_event')
            reason: Reason for access (for audit trail)

        Returns:
            bool: True if access authorized, False otherwise
        """
        if not self._privacy_enabled:
            return True  # No enforcement when disabled

        # Basic authorization logic - can be extended with more sophisticated rules
        # For now, allow access with comprehensive audit logging
        authorized = True

        # Create comprehensive access record
        access_record = SensitiveDataAccess(
            timestamp=datetime.now(),
            accessor=accessor,
            data_type=data_type,
            access_reason=reason,
            access_level="request",
            audit_logged=True
        )

        # Log the access attempt
        audit_event(
            event_type="privacy_access_request",
            identifiers={"accessor": accessor, "data_type": data_type},
            payload={
                "access_granted": authorized,
                "reason": reason,
                "audit_level": self._privacy_audit_level
            }
        )

        logger.info(f"Sensitive data access {'GRANTED' if authorized else 'DENIED'} for {accessor} "
                   f"accessing {data_type}: {reason}")

        return authorized

    def redact_sensitive_for_backup(self, data: Dict[str, Any],
                                  include_sensitive: bool = False,
                                  admin_confirmed: bool = False) -> Dict[str, Any]:
        """
        Redact sensitive data for backup operations.

        Args:
            data: Data dictionary to process
            include_sensitive: Whether to include sensitive fields (requires admin confirmation)
            admin_confirmed: Admin confirmation for sensitive data inclusion

        Returns:
            Dict with sensitive data appropriately handled
        """
        if not self._privacy_enabled:
            return data  # No redaction when disabled

        processed_data = {}
        sensitive_fields_detected = []
        redaction_performed = False

        # Define private sensitive fields (values that should never be exported)
        private_fields = {'value', 'data', 'payload', 'content', 'secret', 'password',
                         'token', 'auth_token', 'session_key', 'credential'}

        for key, value in data.items():
            if key.lower() in private_fields:
                sensitive_fields_detected.append(key)

                if include_sensitive and admin_confirmed:
                    # Include the sensitive field but log the access
                    processed_data[key] = value
                    self.validate_sensitive_access(
                        accessor="backup_system",
                        data_type=f"backup_field_{key}",
                        reason="Admin confirmed sensitive data inclusion in backup"
                    )
                else:
                    # Redact sensitive field
                    processed_data[key] = "***REDACTED***"
                    redaction_performed = True
            else:
                # Non-sensitive field - include as-is
                processed_data[key] = value

        # Log backup operation with privacy details
        if sensitive_fields_detected or redaction_performed:
            audit_event(
                event_type="backup_redaction_operation",
                identifiers={"fields_processed": len(data), "redaction_performed": redaction_performed},
                payload={
                    "sensitive_fields_detected": len(sensitive_fields_detected),
                    "include_sensitive": include_sensitive,
                    "admin_confirmed": admin_confirmed,
                    "privacy_enabled": self._privacy_enabled
                }
            )

            if redaction_performed:
                logger.info(f"Redacted {len(sensitive_fields_detected)} sensitive fields for backup")
            if include_sensitive and admin_confirmed:
                logger.warning("Sensitive data included in backup with admin confirmation")

        return processed_data

    def privacy_audit_summary(self) -> Dict[str, Any]:
        """
        Generate comprehensive privacy audit report.

        Returns:
            Dict containing privacy compliance metrics and findings
        """
        if not self._privacy_enabled:
            return {"privacy_enforcement": "disabled", "status": "privacy_controls_inactive"}

        report = {
            "timestamp": datetime.now().isoformat(),
            "version": VERSION,
            "privacy_enforcement": "enabled",
            "audit_level": self._privacy_audit_level,
            "findings": [],
            "metrics": {},
            "recommendations": []
        }

        try:
            # Analyze current KV store for privacy compliance
            kv_compliance = self._audit_kv_privacy()
            report["metrics"].update(kv_compliance["metrics"])
            report["findings"].extend(kv_compliance["findings"])

            # Analyze system configuration for privacy gaps
            config_issues = self._audit_system_configuration()
            if config_issues:
                report["findings"].extend(config_issues)

            # Generate recommendations based on findings
            report["recommendations"] = self._generate_privacy_recommendations(report["findings"])

            # Overall compliance status
            critical_findings = [f for f in report["findings"] if f.get("severity") == "critical"]
            report["status"] = "non_compliant" if critical_findings else "compliant"

            logger.info(f"Privacy audit completed: {len(report['findings'])} findings, "
                       f"{len(report['recommendations'])} recommendations")

            # Log the audit operation
            audit_event(
                event_type="privacy_audit_completed",
                identifiers={"findings_count": len(report["findings"])},
                payload={
                    "status": report["status"],
                    "audit_level": self._privacy_audit_level
                }
            )

        except Exception as e:
            logger.error(f"Privacy audit failed: {e}")
            report["status"] = "audit_failed"
            report["findings"].append({
                "type": "audit_error",
                "description": f"Privacy audit failed: {str(e)}",
                "severity": "critical",
                "recommendation": "Investigate audit system failure"
            })

        return report

    def _audit_kv_privacy(self) -> Dict[str, Any]:
        """Audit KV store privacy compliance."""
        findings = []
        metrics = {
            "total_kv_count": 0,
            "sensitive_kv_count": 0,
            "non_sensitive_kv_count": 0,
            "tombstoned_kv_count": 0
        }

        try:
            kv_records = list_keys()
            metrics["total_kv_count"] = len(kv_records)

            for kv in kv_records:
                if kv.sensitive:
                    metrics["sensitive_kv_count"] += 1
                else:
                    metrics["non_sensitive_kv_count"] += 1

                if not kv.value.strip():  # Tombstone check
                    metrics["tombstoned_kv_count"] += 1

        except Exception as e:
            findings.append({
                "type": "kv_audit_error",
                "description": f"Failed to audit KV store: {str(e)}",
                "severity": "high",
                "recommendation": "Check database connectivity and permissions"
            })

        # Analyze findings
        sensitive_percentage = (metrics["sensitive_kv_count"] / metrics["total_kv_count"]) * 100 if metrics["total_kv_count"] > 0 else 0

        if sensitive_percentage > 50:  # Arbitrary threshold
            findings.append({
                "type": "high_sensitive_data_ratio",
                "description": f"High proportion of sensitive data: {sensitive_percentage:.1f}% of KV records",
                "severity": "medium",
                "recommendation": "Review data classification policies and ensure sensitive data handling is appropriate"
            })

        return {"metrics": metrics, "findings": findings}

    def _audit_system_configuration(self) -> List[Dict[str, Any]]:
        """Audit system configuration for privacy gaps."""
        issues = []

        # Check if debug mode exposes sensitive data (this would be a privacy violation)
        try:
            from .config import debug_enabled
            if debug_enabled():
                issues.append({
                    "type": "debug_mode_privacy_risk",
                    "description": "Debug mode is enabled, which may expose sensitive data in logs and API responses",
                    "severity": "high",
                    "recommendation": "Disable debug mode in production or ensure sensitive data is properly redacted in debug output"
                })
        except Exception as e:
            logger.debug(f"Could not check debug mode configuration: {e}")

        # Additional configuration audits would go here
        # For now, this is a minimal implementation

        return issues

    def _generate_privacy_recommendations(self, findings: List[Dict[str, Any]]) -> List[str]:
        """Generate privacy recommendations based on audit findings."""
        recommendations = []

        for finding in findings:
            if finding.get("recommendation"):
                recommendations.append(finding["recommendation"])

        # Standard recommendations if no issues found
        if not findings:
            recommendations.extend([
                "Regular privacy audits are recommended (quarterly)",
                "Review and update access controls periodically",
                "Ensure all system logs respect data minimization principles"
            ])

        return recommendations

    def _log_privacy_activation(self):
        """Log privacy enforcement activation."""
        audit_event(
            event_type="privacy_enforcement_activated",
            identifiers={"audit_level": self._privacy_audit_level},
            payload={
                "version": VERSION,
                "timestamp": datetime.now().isoformat()
            }
        )


# Global privacy enforcer instance
_privacy_enforcer = PrivacyEnforcer()


def validate_sensitive_access(accessor: str, data_type: str, reason: str) -> bool:
    """
    Validate and log sensitive data access requests.
    See PrivacyEnforcer.validate_sensitive_access for details.
    """
    return _privacy_enforcer.validate_sensitive_access(accessor, data_type, reason)


def redact_sensitive_for_backup(data: Dict[str, Any],
                              include_sensitive: bool = False,
                              admin_confirmed: bool = False) -> Dict[str, Any]:
    """
    Redact sensitive data for backup operations.
    See PrivacyEnforcer.redact_sensitive_for_backup for details.
    """
    return _privacy_enforcer.redact_sensitive_for_backup(data, include_sensitive, admin_confirmed)


def privacy_audit_summary() -> Dict[str, Any]:
    """
    Generate comprehensive privacy audit report.
    See PrivacyEnforcer.privacy_audit_summary for details.
    """
    return _privacy_enforcer.privacy_audit_summary()


def configure_privacy_enforcement(enabled: bool = False, audit_level: str = "standard"):
    """
    Configure privacy enforcement system.
    See PrivacyEnforcer.configure for details.
    """
    _privacy_enforcer.configure(enabled, audit_level)
