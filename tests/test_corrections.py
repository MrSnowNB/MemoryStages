"""
Stage 3 scope only. Do not implement beyond this file's responsibilities.
Heartbeat and drift correction - maintains vector overlay consistency with canonical SQLite.
"""

import pytest
from unittest.mock import patch, MagicMock
from datetime import datetime

from src.core.corrections import apply_corrections, revert_correction, CorrectionResult
from src.core.drift_rules import CorrectionPlan, CorrectionAction


class TestCorrectionEngine:
    """Test the corrections engine core functionality."""

    def test_apply_corrections_disabled_vectors(self):
        """Test corrections are skipped when vector features disabled."""
        with patch('src.core.corrections.are_vector_features_enabled', return_value=False), \
             patch('src.core.corrections.get_correction_mode', return_value="apply"):
            results = apply_corrections([])
            assert results == []

    @patch('src.core.corrections.are_vector_features_enabled', return_value=True)
    @patch('src.core.corrections.get_correction_mode', return_value="apply")
    def test_apply_corrections_no_vector_store(self, mock_enabled, mock_mode):
        """Test corrections are skipped when vector store unavailable."""
        with patch('src.core.corrections.get_vector_store', return_value=None):
            results = apply_corrections([])
            assert results == []

    @patch('src.core.corrections.are_vector_features_enabled', return_value=True)
    @patch('src.core.corrections.get_correction_mode', return_value="off")
    def test_apply_corrections_mode_off(self, mock_enabled, mock_mode, capsys):
        """Test off mode performs no actions."""
        vector_store = MagicMock()
        embedding_provider = MagicMock()

        with patch('src.core.corrections.get_vector_store', return_value=vector_store), \
             patch('src.core.corrections.get_embedding_provider', return_value=embedding_provider):

            plan = CorrectionPlan(
                id="test-plan",
                finding_id="test-finding",
                actions=[CorrectionAction(type="ADD_VECTOR", key="test", metadata={})],
                preview={}
            )

            results = apply_corrections([plan])

            assert len(results) == 1
            assert results[0].success == True
            assert results[0].action_taken == False
            assert "no action taken" in results[0].details["message"]

            # Verify no vector operations called
            vector_store.add.assert_not_called()

    @patch('src.core.corrections.are_vector_features_enabled', return_value=True)
    @patch('src.core.corrections.get_correction_mode', return_value="propose")
    def test_apply_corrections_mode_propose(self, mock_enabled, mock_mode):
        """Test propose mode logs but doesn't execute."""
        vector_store = MagicMock()
        embedding_provider = MagicMock()

        with patch('src.core.corrections.get_vector_store', return_value=vector_store), \
             patch('src.core.corrections.get_embedding_provider', return_value=embedding_provider), \
             patch('src.core.corrections._log_correction_proposal') as mock_log:

            plan = CorrectionPlan(
                id="test-plan",
                finding_id="test-finding",
                actions=[CorrectionAction(type="ADD_VECTOR", key="test", metadata={})],
                preview={}
            )

            results = apply_corrections([plan])

            assert len(results) == 1
            assert results[0].success == True
            assert results[0].action_taken == False
            assert "proposed" in results[0].details["message"]

            # Verify logging called but no vector operations
            mock_log.assert_called_once()
            vector_store.add.assert_not_called()

    @patch('src.core.corrections.are_vector_features_enabled', return_value=True)
    @patch('src.core.corrections.get_correction_mode', return_value="apply")
    def test_apply_corrections_mode_apply_success(self, mock_enabled, mock_mode):
        """Test apply mode successfully executes corrections."""
        vector_store = MagicMock()
        embedding_provider = MagicMock()

        # Mock KV entry
        kv_entry = MagicMock()
        kv_entry.value = "test value"
        kv_entry.sensitive = False
        kv_entry.source = "test"
        kv_entry.casing = "lower"
        kv_entry.updated_at = datetime.now()

        with patch('src.core.corrections.get_vector_store', return_value=vector_store), \
             patch('src.core.corrections.get_embedding_provider', return_value=embedding_provider), \
             patch('src.core.corrections.get_key', return_value=kv_entry), \
             patch('src.core.corrections._log_correction_application') as mock_log:

            embedding_provider.embed_text.return_value = [0.1] * 384

            plan = CorrectionPlan(
                id="test-plan",
                finding_id="test-finding",
                actions=[CorrectionAction(type="ADD_VECTOR", key="test", metadata={})],
                preview={}
            )

            results = apply_corrections([plan])

            assert len(results) == 1
            assert results[0].success == True
            assert results[0].action_taken == True
            assert "Applied ADD_VECTOR" in results[0].details["message"]

            # Verify vector operations called
            vector_store.add.assert_called_once()
            mock_log.assert_called_once()


class TestCorrectionActions:
    """Test individual correction action execution."""

    @patch('src.core.corrections.get_key')
    def test_add_vector_success(self, mock_get_key):
        """Test successful ADD_VECTOR action."""
        # Mock KV entry
        kv_entry = MagicMock()
        kv_entry.value = "test value"
        kv_entry.sensitive = False
        kv_entry.source = "test"
        kv_entry.casing = "lower"
        kv_entry.updated_at = datetime.now()
        mock_get_key.return_value = kv_entry

        vector_store = MagicMock()
        embedding_provider = MagicMock()
        embedding_provider.embed_text.return_value = [0.1] * 384

        action = CorrectionAction(type="ADD_VECTOR", key="test_key", metadata={})

        # This should be called by the apply_corrections flow, but we'll test directly
        from src.core.corrections import _apply_add_vector
        _apply_add_vector("test_key", vector_store, embedding_provider)

        vector_store.add.assert_called_once()

    @patch('src.core.corrections.get_key')
    def test_add_vector_missing_kv(self, mock_get_key):
        """Test ADD_VECTOR fails when KV entry doesn't exist."""
        mock_get_key.return_value = None

        vector_store = MagicMock()
        embedding_provider = MagicMock()

        from src.core.corrections import _apply_add_vector
        with pytest.raises(ValueError, match="Cannot add vector"):
            _apply_add_vector("missing_key", vector_store, embedding_provider)

    @patch('src.core.corrections.get_key')
    def test_add_vector_sensitive_kv(self, mock_get_key):
        """Test ADD_VECTOR refuses to vectorize sensitive keys."""
        kv_entry = MagicMock()
        kv_entry.sensitive = True  # Sensitive!
        mock_get_key.return_value = kv_entry

        vector_store = MagicMock()
        embedding_provider = MagicMock()

        from src.core.corrections import _apply_add_vector
        with pytest.raises(ValueError, match="Refusing to vectorize sensitive"):
            _apply_add_vector("sensitive_key", vector_store, embedding_provider)

    @patch('src.core.corrections.get_key')
    def test_update_vector_success(self, mock_get_key):
        """Test successful UPDATE_VECTOR action."""
        kv_entry = MagicMock()
        kv_entry.value = "updated value"
        kv_entry.sensitive = False
        kv_entry.source = "test"
        kv_entry.casing = "lower"
        kv_entry.updated_at = datetime.now()
        mock_get_key.return_value = kv_entry

        vector_store = MagicMock()
        vector_store.update = MagicMock()  # Mock has update method
        embedding_provider = MagicMock()
        embedding_provider.embed_text.return_value = [0.1] * 384

        from src.core.corrections import _apply_update_vector
        _apply_update_vector("test_key", vector_store, embedding_provider)

        vector_store.update.assert_called_once()

    def test_remove_vector_success(self):
        """Test successful REMOVE_VECTOR action."""
        vector_store = MagicMock()

        from src.core.corrections import _apply_remove_vector
        _apply_remove_vector("orphaned_key", vector_store)

        vector_store.delete.assert_called_once()


class TestCorrectionModes:
    """Test different correction modes."""

    @patch('src.core.corrections.are_vector_features_enabled', return_value=True)
    @patch('src.core.corrections.get_correction_mode')
    def test_unknown_correction_mode(self, mock_get_mode):
        """Test handling of unknown correction mode."""
        mock_get_mode.return_value = "invalid_mode"

        with patch('src.core.corrections.get_vector_store', return_value=MagicMock()), \
             patch('src.core.corrections.get_embedding_provider', return_value=MagicMock()):

            plan = CorrectionPlan(
                id="test-plan",
                finding_id="test-finding",
                actions=[CorrectionAction(type="ADD_VECTOR", key="test", metadata={})],
                preview={}
            )

            results = apply_corrections([plan])

            assert len(results) == 1
            assert results[0].success == False
            assert "Unknown correction mode" in results[0].error_message


class TestRevertCorrections:
    """Test correction reversion functionality."""

    @patch('src.core.corrections.add_event')
    def test_revert_correction(self, mock_add_event):
        """Test correction revert functionality."""
        result = revert_correction("test-plan-id")

        assert result["plan_id"] == "test-plan-id"
        assert result["reverted"] == False
        assert "limited_support" in result["reason"]

        # Verify episodic event was logged
        mock_add_event.assert_called_once()
        call_args = mock_add_event.call_args
        assert call_args[0] == ("correction_system", "revert_correction")
        payload = call_args[1][0]
        assert "limited_support" in payload


class TestCorrectionLogging:
    """Test correction event logging."""

    @patch('src.core.corrections.add_event')
    def test_log_correction_plan(self, mock_add_event):
        """Test correction plan logging."""
        plan = CorrectionPlan(
            id="plan-123",
            finding_id="finding-456",
            actions=[],
            preview={"drift_type": "missing_vector", "severity": "high"}
        )

        from src.core.corrections import _log_correction_plan
        _log_correction_plan(plan, "apply")

        mock_add_event.assert_called_once()
        call_args = mock_add_event.call_args
        assert call_args[0] == ("correction_system", "correction_plan_started")
        payload = call_args[1][0]
        assert payload["plan_id"] == "plan-123"
        assert payload["correction_mode"] == "apply"

    @patch('src.core.corrections.add_event')
    def test_log_correction_proposal(self, mock_add_event):
        """Test correction proposal logging."""
        action = CorrectionAction(type="ADD_VECTOR", key="proposal_key", metadata={"reason": "test"})

        from src.core.corrections import _log_correction_proposal
        _log_correction_proposal("plan-123", action)

        mock_add_event.assert_called_once()
        call_args = mock_add_event.call_args
        assert call_args[0] == ("correction_system", "correction_proposed")
        payload = call_args[1][0]
        assert payload["plan_id"] == "plan-123"
        assert payload["action_type"] == "ADD_VECTOR"
        assert payload["key"] == "proposal_key"

    @patch('src.core.corrections.add_event')
    def test_log_correction_application(self, mock_add_event):
        """Test correction application logging."""
        action = CorrectionAction(type="REMOVE_VECTOR", key="applied_key", metadata={})

        from src.core.corrections import _log_correction_application
        _log_correction_application("plan-456", action)

        mock_add_event.assert_called_once()
        call_args = mock_add_event.call_args
        assert call_args[0] == ("correction_system", "correction_applied")
        payload = call_args[1][0]
        assert payload["action_type"] == "REMOVE_VECTOR"

    @patch('src.core.corrections.add_event')
    def test_log_correction_failure(self, mock_add_event):
        """Test correction failure logging."""
        action = CorrectionAction(type="UPDATE_VECTOR", key="failed_key", metadata={})
        error = ValueError("Test error")

        from src.core.corrections import _log_correction_failure
        _log_correction_failure("plan-789", action, error)

        mock_add_event.assert_called_once()
        call_args = mock_add_event.call_args
        assert call_args[0] == ("correction_system", "correction_failed")
        payload = call_args[1][0]
        assert "Test error" in payload["error"]


class TestCorrectionDataStructures:
    """Test correction-related dataclasses."""

    def test_correction_result_creation(self):
        """Test CorrectionResult dataclass."""
        result = CorrectionResult(
            plan_id="plan-123",
            action_index=0,
            success=True,
            action_taken=False,
            error_message="",
            details={"key": "test", "message": "ok"}
        )

        assert result.plan_id == "plan-123"
        assert result.success == True
        assert result.action_taken == False
        assert result.details["message"] == "ok"

    def test_correction_result_default_values(self):
        """Test CorrectionResult default values."""
        result = CorrectionResult("plan-123", 0, False, False, "error", {})

        assert result.success == False
        assert result.error_message == "error"
        assert len(result.details) == 0
