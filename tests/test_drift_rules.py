"""
Stage 3 scope only. Do not implement beyond this file's responsibilities.
Heartbeat and drift correction - maintains vector overlay consistency with canonical SQLite.
"""

import pytest
from unittest.mock import patch, MagicMock
from datetime import datetime, timedelta

from src.core.drift_rules import (
    detect_drift, DriftFinding, CorrectionAction, CorrectionPlan,
    create_correction_plan, _calculate_severity
)


class TestDriftDetection:
    """Test drift detection between SQLite and vector overlay."""

    @patch('src.core.drift_rules.are_vector_features_enabled', return_value=True)
    @patch('src.core.drift_rules.get_vector_store')
    @patch('src.core.drift_rules.list_keys')
    @patch('src.core.drift_rules._get_audit_vector_entries')
    def test_detect_missing_vector(self, mock_get_vector_entries, mock_list_keys, mock_get_store):
        """Test detection of KV entries missing from vector store."""
        # Setup vector store
        mock_vector_store = MagicMock()
        mock_get_store.return_value = mock_vector_store

        # Setup SQLite KV entries (non-sensitive)
        mock_kv_entry = MagicMock()
        mock_kv_entry.key = "missing_key"
        mock_kv_entry.sensitive = False
        mock_kv_entry.updated_at = datetime.now()
        mock_kv_entry.source = "user"
        mock_list_keys.return_value = [mock_kv_entry]

        # Setup vector entries (key missing from vector)
        mock_get_vector_entries.return_value = {}  # Empty = no vectors

        findings = detect_drift()

        assert len(findings) == 1
        finding = findings[0]
        assert finding.type == "missing_vector"
        assert finding.kv_key == "missing_key"
        assert "sqlite_updated" in finding.details
        assert "KV entry exists in SQLite but missing from vector overlay" in finding.details["reason"]

    @patch('src.core.drift_rules.are_vector_features_enabled', return_value=True)
    @patch('src.core.drift_rules.get_vector_store')
    @patch('src.core.drift_rules.list_keys')
    @patch('src.core.drift_rules._get_audit_vector_entries')
    def test_detect_stale_vector(self, mock_get_vector_entries, mock_list_keys, mock_get_store):
        """Test detection of stale vector embeddings."""
        # Setup sqlite entry
        mock_sqlite_entry = MagicMock()
        mock_sqlite_entry.key = "stale_key"
        mock_sqlite_entry.sensitive = False
        current_time = datetime.now()
        mock_sqlite_entry.updated_at = current_time  # Recent update
        mock_list_keys.return_value = [mock_sqlite_entry]

        # Setup vector entry with older timestamp
        old_time = (current_time - timedelta(hours=1)).isoformat()
        mock_get_vector_entries.return_value = {
            "stale_key": {"updated_at": old_time}
        }

        findings = detect_drift()

        assert len(findings) == 1
        finding = findings[0]
        assert finding.type == "stale_vector"
        assert finding.kv_key == "stale_key"
        assert "Vector embedding is stale" in finding.details["reason"]

    @patch('src.core.drift_rules.are_vector_features_enabled', return_value=True)
    @patch('src.core.drift_rules.get_vector_store')
    @patch('src.core.drift_rules.list_keys')
    @patch('src.core.drift_rules._get_audit_vector_entries')
    def test_detect_orphaned_vector(self, mock_get_vector_entries, mock_list_keys, mock_get_store):
        """Test detection of orphaned vector entries."""
        # Setup empty SQLite (orphaned vector exists)
        mock_list_keys.return_value = []

        # Setup vector entry with no matching SQLite key
        mock_get_vector_entries.return_value = {
            "orphaned_key": {"updated_at": "2025-01-26T10:00:00"}
        }

        findings = detect_drift()

        assert len(findings) == 1
        finding = findings[0]
        assert finding.type == "orphaned_vector"
        assert finding.kv_key == "orphaned_key"
        assert "Vector entry exists but corresponding SQLite KV is missing" in finding.details["reason"]

    @patch('src.core.drift_rules.are_vector_features_enabled', return_value=True)
    @patch('src.core.drift_rules.get_vector_store')
    @patch('src.core.drift_rules.list_keys')
    @patch('src.core.drift_rules._get_audit_vector_entries')
    def test_skip_sensitive_drift_detection(self, mock_get_vector_entries, mock_list_keys, mock_get_store):
        """Test that sensitive KV entries are not checked for drift."""
        # Setup sensitive KV entry
        mock_sensitive_kv = MagicMock()
        mock_sensitive_kv.key = "sensitive_key"
        mock_sensitive_kv.sensitive = True  # Marked as sensitive
        mock_list_keys.return_value = [mock_sensitive_kv]

        # Empty vector entries
        mock_get_vector_entries.return_value = {}

        findings = detect_drift()

        # Should report no findings (sensitive KV ignored)
        assert len(findings) == 0

    def test_detect_drift_disabled_vectors(self):
        """Test drift detection when vector features are disabled."""
        with patch('src.core.drift_rules.are_vector_features_enabled', return_value=False):
            findings = detect_drift()
            assert findings == []

    def test_detect_drift_no_vector_store(self):
        """Test drift detection when vector store unavailable."""
        with patch('src.core.drift_rules.are_vector_features_enabled', return_value=True), \
             patch('src.core.drift_rules.get_vector_store', return_value=None):
            findings = detect_drift()
            assert findings == []


class TestSeverityCalculation:
    """Test severity calculation for different drift types and rulesets."""

    @patch('src.core.drift_rules.get_drift_ruleset', return_value="strict")
    def test_severity_strict_ruleset(self, mock_ruleset):
        """Test strict ruleset assigns high severity to all findings."""
        assert _calculate_severity("missing_vector") == "high"
        assert _calculate_severity("stale_vector") == "high"
        assert _calculate_severity("orphaned_vector") == "high"

    @patch('src.core.drift_rules.get_drift_ruleset', return_value="lenient")
    def test_severity_lenient_ruleset(self, mock_ruleset):
        """Test lenient ruleset assigns differentiated severities."""
        assert _calculate_severity("missing_vector") == "medium"
        assert _calculate_severity("stale_vector") == "medium"
        assert _calculate_severity("orphaned_vector") == "low"

    @patch('src.core.drift_rules.get_drift_ruleset', return_value="invalid")
    def test_severity_invalid_ruleset(self, mock_ruleset):
        """Test invalid ruleset falls back to medium severity."""
        assert _calculate_severity("missing_vector") == "medium"

    @patch('src.core.drift_rules.get_drift_ruleset', return_value="lenient")
    def test_severity_unknown_drift_type(self, mock_ruleset):
        """Test unknown drift type defaults to medium."""
        assert _calculate_severity("unknown_type") == "medium"


class TestCorrectionPlans:
    """Test generation of correction plans from drift findings."""

    def test_create_correction_plan_missing_vector(self):
        """Test correction plan for missing vector issue."""
        finding = DriftFinding(
            id="test-finding-id",
            type="missing_vector",
            severity="medium",
            kv_key="missing_key",
            details={"test": "data"}
        )

        plan = create_correction_plan(finding)

        assert plan.finding_id == finding.id
        assert len(plan.actions) == 1
        assert plan.actions[0].type == "ADD_VECTOR"
        assert plan.actions[0].key == "missing_key"
        assert plan.preview["drift_type"] == "missing_vector"
        assert plan.preview["action_type"] == "ADD_VECTOR"

    def test_create_correction_plan_stale_vector(self):
        """Test correction plan for stale vector issue."""
        finding = DriftFinding(
            id="test-finding-id",
            type="stale_vector",
            severity="medium",
            kv_key="stale_key",
            details={"test": "data"}
        )

        plan = create_correction_plan(finding)

        assert plan.actions[0].type == "UPDATE_VECTOR"
        assert plan.actions[0].key == "stale_key"
        assert plan.preview["drift_type"] == "stale_vector"
        assert plan.preview["action_type"] == "UPDATE_VECTOR"

    def test_create_correction_plan_orphaned_vector(self):
        """Test correction plan for orphaned vector issue."""
        finding = DriftFinding(
            id="test-finding-id",
            type="orphaned_vector",
            severity="low",
            kv_key="orphaned_key",
            details={"test": "data"}
        )

        plan = create_correction_plan(finding)

        assert plan.actions[0].type == "REMOVE_VECTOR"
        assert plan.actions[0].key == "orphaned_key"
        assert plan.preview["drift_type"] == "orphaned_vector"
        assert plan.preview["action_type"] == "REMOVE_VECTOR"

    def test_create_correction_plan_unknown_type(self):
        """Test error for unknown drift finding type."""
        finding = DriftFinding(
            id="test-finding-id",
            type="unknown_type",
            severity="medium",
            kv_key="unknown_key",
            details={}
        )

        with pytest.raises(ValueError, match="Unknown drift type"):
            create_correction_plan(finding)


class TestDataStructures:
    """Test the dataclasses work as expected."""

    def test_drift_finding_creation(self):
        """Test DriftFinding dataclass creation."""
        finding = DriftFinding(
            id="test-id",
            type="missing_vector",
            severity="high",
            kv_key="test_key",
            details={"reason": "test"}
        )

        assert finding.id == "test-id"
        assert finding.type == "missing_vector"
        assert finding.severity == "high"
        assert finding.kv_key == "test_key"
        assert finding.details["reason"] == "test"

    def test_correction_action_creation(self):
        """Test CorrectionAction dataclass creation."""
        action = CorrectionAction(
            type="ADD_VECTOR",
            key="test_key",
            metadata={"reason": "test"}
        )

        assert action.type == "ADD_VECTOR"
        assert action.key == "test_key"
        assert action.metadata["reason"] == "test"

    def test_correction_plan_creation(self):
        """Test CorrectionPlan dataclass creation."""
        plan = CorrectionPlan(
            id="plan-id",
            finding_id="finding-id",
            actions=[],
            preview={"impact": "safe"}
        )

        assert plan.id == "plan-id"
        assert plan.finding_id == "finding-id"
        assert len(plan.actions) == 0
        assert plan.preview["impact"] == "safe"


class TestAuditVectorEntries:
    """Test the vector audit functionality."""

    @patch('src.core.drift_rules._get_audit_vector_entries')
    @patch('src.core.drift_rules.are_vector_features_enabled', return_value=True)
    @patch('src.core.drift_rules.get_vector_store')
    @patch('src.core.drift_rules.list_keys')
    def test_audit_vector_entries_failure(self, mock_list_keys, mock_get_store, mock_get_vector_entries):
        """Test graceful handling when vector audit fails."""
        mock_list_keys.return_value = []
        mock_get_store.return_value = MagicMock()
        mock_get_vector_entries.side_effect = Exception("Audit failed")

        findings = detect_drift()

        # Should return empty (no crash)
        assert findings == []
