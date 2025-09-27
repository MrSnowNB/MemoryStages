"""
Stage 6 scope only. Do not implement beyond this file's responsibilities.
Privacy, backup, and maintenance - ensures data protection and system integrity.
"""

import pytest
from unittest.mock import patch, MagicMock
from datetime import datetime

from src.core.privacy import (
    PrivacyEnforcer,
    validate_sensitive_access,
    redact_sensitive_for_backup,
    privacy_audit_summary,
    configure_privacy_enforcement,
    SensitiveDataAccess
)


class TestPrivacyEnforcement:
    """Test privacy enforcement and audit capabilities."""

    def setup_method(self):
        """Reset privacy configuration before each test."""
        configure_privacy_enforcement(enabled=False)

    def teardown_method(self):
        """Clean up after each test."""
        configure_privacy_enforcement(enabled=False)

    def test_privacy_enforcement_disabled_by_default(self):
        """Test that privacy enforcement is disabled by default."""
        # Default state should be disabled
        result = validate_sensitive_access("test", "test_data", "test_reason")
        assert result is True  # Should allow access when disabled

    @patch('src.core.privacy.audit_event')
    def test_privacy_access_validation_and_audit(self, mock_audit_event):
        """Test sensitive data access validation with audit logging."""
        # Enable privacy enforcement
        configure_privacy_enforcement(enabled=True, audit_level="verbose")

        # Test access validation
        result = validate_sensitive_access("dashboard", "kv_record", "Viewing sensitive customer data")

        # Should allow access (our current logic) but log the attempt
        assert result is True

        # Verify audit event was logged
        mock_audit_event.assert_called_once()
        call_args = mock_audit_event.call_args
        assert call_args[1]["event_type"] == "privacy_access_request"
        assert call_args[1]["identifiers"]["accessor"] == "dashboard"
        assert call_args[1]["identifiers"]["data_type"] == "kv_record"
        assert call_args[1]["payload"]["access_granted"] is True

    @patch('src.core.privacy.audit_event')
    def test_privacy_backup_redaction(self, mock_audit_event):
        """Test sensitive data redaction for backup operations."""
        configure_privacy_enforcement(enabled=True)

        # Test data with sensitive fields
        test_data = {
            "key": "user_profile",
            "value": "sensitive_user_data",
            "normal_field": "normal_value",
            "password": "secret123"
        }

        # Test redaction (default behavior)
        redacted = redact_sensitive_for_backup(test_data)

        assert redacted["key"] == "user_profile"
        assert redacted["normal_field"] == "normal_value"
        assert redacted["value"] == "***REDACTED***"
        assert redacted["password"] == "***REDACTED***"

        # Verify audit event was logged
        mock_audit_event.assert_called_once()
        call_args = mock_audit_event.call_args
        assert call_args[1]["event_type"] == "backup_redaction_operation"

    @patch('src.core.privacy.audit_event')
    def test_privacy_backup_admin_confirmed_sensitive_inclusion(self, mock_audit_event):
        """Test sensitive data inclusion in backup with admin confirmation."""
        configure_privacy_enforcement(enabled=True)

        test_data = {
            "key": "user_profile",
            "value": "sensitive_user_data",
            "password": "secret123"
        }

        # Test with admin confirmation
        included = redact_sensitive_for_backup(test_data, include_sensitive=True, admin_confirmed=True)

        assert included["key"] == "user_profile"
        assert included["value"] == "sensitive_user_data"  # Should be included
        assert included["password"] == "secret123"  # Should be included

        # Should have multiple audit events: redaction + sensitive field access
        assert mock_audit_event.call_count >= 2

    @patch('src.util.logging.audit_event')
    @patch('src.core.privacy.list_keys')
    def test_privacy_audit_report_generation(self, mock_list_keys, mock_audit_event):
        """Test comprehensive privacy audit report generation."""
        # Mock some KV records
        mock_kv_records = [
            MagicMock(sensitive=True, value="secret"),
            MagicMock(sensitive=False, value="normal"),
            MagicMock(sensitive=False, value="")  # Tombstone
        ]
        mock_list_keys.return_value = mock_kv_records

        configure_privacy_enforcement(enabled=True, audit_level="standard")

        report = privacy_audit_summary()

        # Verify report structure
        assert "timestamp" in report
        assert "version" in report
        assert report["privacy_enforcement"] == "enabled"
        assert report["audit_level"] == "standard"
        assert "findings" in report
        assert "metrics" in report
        assert "recommendations" in report

        # Verify metrics
        assert report["metrics"]["total_kv_count"] == 3
        assert report["metrics"]["sensitive_kv_count"] == 1
        assert report["metrics"]["non_sensitive_kv_count"] == 2
        assert report["metrics"]["tombstoned_kv_count"] == 1

        # Should be compliant with our test data
        assert report["status"] == "compliant"

        # Audit completion should be logged
        mock_audit_event.assert_called_once()
        call_args = mock_audit_event.call_args
        assert call_args[1]["event_type"] == "privacy_audit_completed"

    @patch('src.core.privacy.list_keys')
    def test_privacy_audit_high_sensitive_data_ratio_warning(self, mock_list_keys):
        """Test detection of high proportion of sensitive data."""
        # Create mostly sensitive data
        mock_kv_records = [
            MagicMock(sensitive=True, value="secret1"),
            MagicMock(sensitive=True, value="secret2"),
            MagicMock(sensitive=True, value="secret3"),
            MagicMock(sensitive=False, value="normal")  # Only one non-sensitive
        ]
        mock_list_keys.return_value = mock_kv_records

        configure_privacy_enforcement(enabled=True)
        report = privacy_audit_summary()

        # Should detect high sensitive data ratio
        findings = report["findings"]
        high_ratio_findings = [f for f in findings if f["type"] == "high_sensitive_data_ratio"]

        assert len(high_ratio_findings) == 1
        assert "75.0%" in high_ratio_findings[0]["description"]
        assert high_ratio_findings[0]["severity"] == "medium"

    @patch('src.core.config.debug_enabled')
    def test_privacy_audit_debug_mode_warning(self, mock_debug_enabled):
        """Test detection of debug mode privacy risk."""
        mock_debug_enabled.return_value = True

        configure_privacy_enforcement(enabled=True)
        report = privacy_audit_summary()

        # Should flag debug mode as high severity risk
        findings = report["findings"]
        debug_findings = [f for f in findings if f["type"] == "debug_mode_privacy_risk"]

        assert len(debug_findings) == 1
        assert debug_findings[0]["severity"] == "high"
        assert "debug mode" in debug_findings[0]["description"].lower()

    @patch('src.core.privacy.audit_event')
    def test_privacy_enforcement_activation_audit(self, mock_audit_event):
        """Test that privacy enforcement activation is logged."""
        configure_privacy_enforcement(enabled=True, audit_level="verbose")

        # Should log activation
        mock_audit_event.assert_called_once()
        call_args = mock_audit_event.call_args
        assert call_args[1]["event_type"] == "privacy_enforcement_activated"
        assert call_args[1]["identifiers"]["audit_level"] == "verbose"

    def test_privacy_audit_disabled_behavior(self):
        """Test audit behavior when privacy enforcement is disabled."""
        configure_privacy_enforcement(enabled=False)

        report = privacy_audit_summary()

        assert report["privacy_enforcement"] == "disabled"
        assert report["status"] == "privacy_controls_inactive"
        assert not report["findings"]  # No findings when disabled


class TestPrivacyEnforcerIntegration:
    """Test privacy enforcer integration with existing system components."""

    def setup_method(self):
        """Reset privacy configuration before each test."""
        configure_privacy_enforcement(enabled=False)

    def teardown_method(self):
        """Clean up after each test."""
        configure_privacy_enforcement(enabled=False)

    @patch('src.core.privacy.audit_event')
    @patch('src.core.privacy.list_keys')
    def test_privacy_audit_with_empty_database(self, mock_list_keys, mock_audit_event):
        """Test privacy audit with empty database."""
        mock_list_keys.return_value = []

        configure_privacy_enforcement(enabled=True)
        report = privacy_audit_summary()

        assert report["metrics"]["total_kv_count"] == 0
        assert report["status"] == "compliant"  # Empty DB is compliant
        assert "regular privacy audits" in str(report["recommendations"][0])

    @patch('src.core.privacy.list_keys')
    def test_privacy_audit_database_error_handling(self, mock_list_keys):
        """Test privacy audit error handling for database issues."""
        # Simulate database error
        mock_list_keys.side_effect = Exception("Database connection failed")

        configure_privacy_enforcement(enabled=True)
        report = privacy_audit_summary()

        # Should report the error and mark as non-compliant
        assert report["status"] == "non_compliant"
        assert len(report["findings"]) >= 1

        error_findings = [f for f in report["findings"] if f["type"] == "kv_audit_error"]
        assert len(error_findings) == 1
        assert "Database connection failed" in error_findings[0]["description"]
        assert error_findings[0]["severity"] == "high"

    @patch('src.core.privacy.audit_event')
    def test_privacy_backup_redaction_no_sensitive_data(self, mock_audit_event):
        """Test backup redaction when no sensitive data is present."""
        configure_privacy_enforcement(enabled=True)

        # Data with no sensitive fields
        safe_data = {
            "key": "user_profile",
            "name": "John Doe",
            "email": "john@example.com",
            "normal_field": "normal_value"
        }

        result = redact_sensitive_for_backup(safe_data)

        # Should be identical since no sensitive fields
        assert result == safe_data

        # Should not trigger audit event for backup redaction
        # (Activation event might still occur but redaction event should not)
        audit_calls = mock_audit_event.call_args_list
        redaction_calls = [call for call in audit_calls if call[1]["event_type"] == "backup_redaction_operation"]
        assert len(redaction_calls) == 0
