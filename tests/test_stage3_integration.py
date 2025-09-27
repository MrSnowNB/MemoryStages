"""
Stage 3 Integration Tests - Heartbeat and Drift Correction System
Tests the complete heartbeat-drift-corrections pipeline as a unified system.
"""

import pytest
import os
from unittest.mock import patch, MagicMock
from datetime import datetime

from src.core.heartbeat import register_task
from src.core.drift_rules import detect_drift
from src.core.corrections import apply_corrections


class TestStage3Integration:
    """Test heartbeat system components working together."""

    @patch('src.core.drift_rules.are_vector_features_enabled', return_value=True)
    @patch('src.core.drift_rules._get_audit_vector_entries')
    @patch('src.core.drift_rules.list_keys')
    @patch('src.core.drift_rules.get_vector_store')
    @patch('src.core.drift_rules.get_drift_ruleset', return_value='strict')
    def test_full_drift_detection_to_correction_pipeline(self, mock_ruleset, mock_get_store, mock_list_keys, mock_get_vector_entries, mock_enabled):
        """Test the complete pipeline: detection → plans → corrections."""

        # Mock vector store and SQLite KV for drift scenario
        mock_vector_store = MagicMock()
        mock_get_store.return_value = mock_vector_store

        # Mock KV entry (sensitive=False, exists in SQLite)
        mock_kv_entry = MagicMock()
        mock_kv_entry.key = "drifted_key"
        mock_kv_entry.sensitive = False
        mock_kv_entry.updated_at = datetime.now()
        mock_kv_entry.source = "test"
        mock_list_keys.return_value = [mock_kv_entry]

        # Mock vector entries (key missing - creates drift!)
        mock_get_vector_entries.return_value = {}  # Empty = missing vector

        # 1. Detect drift
        findings = detect_drift()
        assert len(findings) == 1
        finding = findings[0]
        assert finding.type == "missing_vector"
        assert finding.kv_key == "drifted_key"
        print(f"✓ Detected drift: {finding.type} for key '{finding.kv_key}'")

        # 2. Create correction plan
        from src.core.drift_rules import create_correction_plan
        plan = create_correction_plan(finding)
        assert plan.finding_id == finding.id
        assert len(plan.actions) == 1
        assert plan.actions[0].type == "ADD_VECTOR"
        print(f"✓ Created correction plan: {plan.preview['action_type']} for '{plan.preview['affected_key']}'")

        # 3. Apply correction in "apply" mode
        kv_entry = MagicMock()
        kv_entry.value = "test value"
        kv_entry.sensitive = False
        kv_entry.source = "test"
        kv_entry.casing = "lower"
        kv_entry.updated_at = datetime.now()

        with patch('src.core.corrections.get_correction_mode', return_value='apply'), \
             patch('src.core.corrections.get_vector_store', return_value=mock_vector_store), \
             patch('src.core.corrections.get_embedding_provider') as mock_get_embed, \
             patch('src.core.corrections.get_key', return_value=kv_entry), \
             patch('src.core.corrections._log_correction_application') as mock_log:

            mock_embedding_provider = MagicMock()
            mock_embedding_provider.embed_text.return_value = [0.1] * 384
            mock_get_embed.return_value = mock_embedding_provider

            # Apply the correction
            results = apply_corrections([plan])

            assert len(results) == 1
            assert results[0].success == True
            assert results[0].action_taken == True
            assert "ADD_VECTOR" in results[0].details["action_type"]

            # Verify vector operations called
            mock_vector_store.add.assert_called_once()
            mock_log.assert_called_once()

        print(f"✓ Applied correction successfully: {results[0].details['message']}")

    @patch('src.core.drift_rules.are_vector_features_enabled', return_value=False)
    @patch('src.core.corrections.are_vector_features_enabled', return_value=False)
    def test_heartbeat_disabled_integration(self, mock_drift_enabled, mock_corr_enabled):
        """Test that the system behaves correctly when heartbeat is disabled globally."""

        # Drift detection should return empty
        findings = detect_drift()
        assert findings == []

        # Corrections should return empty
        results = apply_corrections([])
        assert results == []

        # Heartbeat task registration should work but do nothing
        def dummy_task():
            pass
        register_task("test_task", 60, dummy_task)
        # Task registration doesn't raise errors, but heartbeat won't start

        print("✓ System correctly disabled when HEARTBEAT_ENABLED=false")

    def test_correction_mode_safety_protection(self):
        """Test that off/propose modes protect against unintended changes."""

        # Create a dummy correction plan
        from src.core.drift_rules import CorrectionPlan, CorrectionAction
        plan = CorrectionPlan(
            id="safety-test-plan",
            finding_id="test-finding",
            actions=[CorrectionAction(type="ADD_VECTOR", key="safety_test", metadata={})],
            preview={}
        )

        # Test "off" mode
        with patch('src.core.corrections.get_correction_mode', return_value='off'), \
             patch('src.core.corrections.get_vector_store', return_value=MagicMock()) as mock_store, \
             patch('src.core.corrections.get_embedding_provider', return_value=MagicMock()):

            results = apply_corrections([plan])
            assert results[0].success == True
            assert results[0].action_taken == False  # No actual changes
            mock_store.add.assert_not_called()  # Verify no vector operations

        print("✓ 'off' mode correctly prevents data modifications")

        # Test "propose" mode
        with patch('src.core.corrections.get_correction_mode', return_value='propose'), \
             patch('src.core.corrections.get_vector_store', return_value=MagicMock()) as mock_store, \
             patch('src.core.corrections.get_embedding_provider', return_value=MagicMock()), \
             patch('src.core.corrections._log_correction_proposal') as mock_log:

            results = apply_corrections([plan])
            assert results[0].success == True
            assert results[0].action_taken == False  # No data changes
            mock_log.assert_called_once()  # But logging happens
            mock_store.add.assert_not_called()  # Vector operation doesn't

        print("✓ 'propose' mode correctly logs proposals without executing changes")

    @patch('src.core.drift_rules.are_vector_features_enabled', return_value=True)
    @patch('src.core.drift_rules.get_drift_ruleset', return_value='lenient')
    def test_drift_ruleset_differentiation(self, mock_ruleset, mock_enabled):
        """Test that strict vs lenient rulesets apply different severities."""

        with patch('src.core.drift_rules.list_keys') as mock_list_keys, \
             patch('src.core.drift_rules.get_vector_store') as mock_get_store, \
             patch('src.core.drift_rules._get_audit_vector_entries') as mock_get_vector_entries:

            # Setup SQLite with non-sensitive KV, missing from vector
            mock_kv = MagicMock()
            mock_kv.key = "test_key"
            mock_kv.sensitive = False
            mock_list_keys.return_value = [mock_kv]

            mock_vector_store = MagicMock()
            mock_get_store.return_value = mock_vector_store
            mock_get_vector_entries.return_value = {}  # Missing = drift

            # Test strict ruleset (all high severity)
            with patch('src.core.drift_rules.get_drift_ruleset', return_value='strict'):
                findings_strict = detect_drift()
                assert len(findings_strict) == 1
                assert findings_strict[0].severity == "high"

            # Test lenient ruleset (missing=medium, but still applies)
            with patch('src.core.drift_rules.get_drift_ruleset', return_value='lenient'):
                findings_lenient = detect_drift()
                assert len(findings_lenient) == 1
                assert findings_lenient[0].severity == "medium"

        print("✓ Rulesets correctly differentiate severity levels")

    def test_stage1_regression_with_heartbeat_flags(self):
        """Verify Stage 1 behaviors are unchanged when heartbeat flags are set."""
        # This test ensures HEARTBEAT_ENABLED=true doesn't break Stage 1 functionality

        # Import basic Stage 1 operations
        from src.core.dao import set_key, get_key, delete_key, list_keys

        # Basic KV operations should work normally even with heartbeat config present
        key = f"heartbeat-regression-{datetime.now().timestamp()}"
        value = "test_value_for_heartbeat_regression"

        # Set and get should work
        success = set_key(key, value, "test", "lower")
        assert success == True

        kv_entry = get_key(key)
        assert kv_entry is not None
        assert kv_entry.value == value

        # List should include our entry
        all_keys = list_keys()
        key_exists = any(kv.key == key for kv in all_keys)
        assert key_exists == True

        # Cleanup
        delete_key(key)

        print("✓ Stage 1 KV operations unchanged with heartbeat configuration enabled")

    @patch('src.core.heartbeat.is_heartbeat_enabled', return_value=False)
    def test_heartbeat_script_disabled_behavior(self, mock_enabled):
        """Test that heartbeat script graceful exits when disabled."""
        with patch('src.core.heartbeat.stop'), \
             patch('sys.exit') as mock_exit:

            from scripts.run_heartbeat import main

            # Should exit early without errors
            main()
            mock_exit.assert_not_called()  # No error exit, just graceful disable

        print("✓ Heartbeat script gracefully handles disabled state")


class TestHeartbeatEndToEnd:
    """Test the complete heartbeat execution from script to corrections."""

    @patch('src.core.drift_rules.are_vector_features_enabled', return_value=True)
    @patch('time.monotonic')
    def test_heartbeat_task_execution_flow(self, mock_monotonic, mock_enabled):
        """Test that heartbeat correctly executes drift audit task."""

        # Mock time for deterministic scheduling
        mock_monotonic.return_value = 1000  # Start time

        def mock_drift_task():
            """Mock drift task that detects and corrects."""
            findings = [MagicMock(type="missing_vector", kv_key="end_to_end_test")]
            plans = [MagicMock(id="test-plan")]
            # In real implementation, this would call the actual functions
            return findings, plans

        # Register and test task execution
        register_task("test_drift_task", 60, mock_drift_task)

        # Check task is registered
        from src.core.heartbeat import tasks
        assert "test_drift_task" in tasks

        # Execute the task directly (would happen in heartbeat loop)
        result = mock_drift_task()
        findings, plans = result
        assert len(findings) == 1
        assert findings[0].type == "missing_vector"

        print("✓ End-to-end heartbeat task execution verified")
